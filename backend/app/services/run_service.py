"""Run service — run lifecycle orchestration (list / create / cancel / restore / detail).

DTO shapes follow ``frontend/src/types/run.ts``.
"""

from __future__ import annotations

import uuid
from typing import Any

from backend.app.db import repositories
from backend.app.db.models import Run
from backend.app.db.repositories import iso
from backend.app.schemas.run_schemas import RunRequest
from backend.app.services.events import emit_event
from backend.app.workers.runner import WORKER, canonical_stages

_TERMINAL = {Run.STATUS_COMPLETED, Run.STATUS_FAILED, Run.STATUS_CANCELLED}


class RunError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def create_run(request: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    dataset_id = request.get("datasetId")
    dataset = repositories.get_dataset(dataset_id) if dataset_id else None
    if dataset is None:
        raise RunError("DatasetNotFound", "The selected dataset no longer exists.")

    stages = canonical_stages(list(request.get("stages") or []))
    if not stages:
        raise RunError("InvalidRequest", "At least one pipeline stage must be requested.")

    run_id = f"run_{uuid.uuid4().hex[:16]}"
    repositories.create_run(
        {
            "id": run_id,
            "user_id": user_id,
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "dataset_path": dataset.path,
            "file_format": dataset.format,
            "rows": dataset.rows,
            "columns": dataset.columns,
            "file_size_bytes": dataset.size_bytes,
            "status": Run.STATUS_QUEUED,
            "request": _jsonable_request(request),
            "mode": request.get("mode") or "balanced",
            "stages_requested": stages,
            "stages_executed": [],
            "sampling_metadata": request.get("sampling"),
            "transform_log": [],
            "warnings": [],
            "logs": [],
        }
    )
    repositories.touch_dataset_last_used(dataset_id, run_id)

    emit_event(run_id, event_type="run.created", status="queued", summary={"datasetId": dataset_id})
    WORKER.launch(run_id)
    return run_to_dict(run_id)


def get_run_detail(run_id: str) -> dict[str, Any] | None:
    run = repositories.get_run(run_id)
    if run is None:
        return None
    return run_to_dict(run_id)


def cancel_run(run_id: str) -> dict[str, Any]:
    run = repositories.get_run(run_id)
    if run is None:
        raise RunError("RunNotFound", "No such run.")
    if run.status in _TERMINAL:
        raise RunError("RunNotActive", f"Cannot cancel a run that has finished ({run.status}).")
    repositories.update_run(run_id, status=Run.STATUS_CANCELLED, completed_at=_utcnow())
    WORKER.cancel(run_id)
    # The worker emits run.cancelled when it observes the cancellation, but if
    # the thread already exited (or was never launched) nothing would reach
    # subscribers — emit here so the UI can never be left stale.
    if not WORKER.is_active(run_id):
        emit_event(
            run_id, event_type="run.cancelled", status="cancelled", summary={"requested": True}
        )
    return run_to_dict(run_id)


def restore_run(run_id: str) -> dict[str, Any]:
    """Re-queue a finished run with its original dataset + request."""
    run = repositories.get_run(run_id)
    if run is None:
        raise RunError("RunNotFound", "No such run.")
    if run.status not in _TERMINAL:
        raise RunError("RunNotActive", "Only finished runs can be restored.")
    stages = canonical_stages(run.stages_requested or [])
    # The previous attempt's artifacts/leaderboard must never be presented as
    # the re-queued run's current output — invalidate them until the new run
    # writes and re-indexes its own.
    repositories.invalidate_artifacts(
        run_id, "Superseded by restore — awaiting the re-run's artifacts."
    )
    repositories.replace_model_results(run_id, [])
    repositories.update_run(
        run_id,
        status=Run.STATUS_QUEUED,
        error=None,
        warnings=[],
        logs=[],
        stages_executed=[],
        completed_at=None,
        total_duration_ms=None,
    )
    from backend.app.services.pipeline_service import reset_stages

    reset_stages(run_id, stages)
    emit_event(run_id, event_type="run.created", status="queued", summary={"restored": True})
    # A previously cancelled run left the cancellation flag set in the worker;
    # clear it so the re-queued run actually executes.
    WORKER.clear_cancel(run_id)
    WORKER.launch(run_id)
    return run_to_dict(run_id)


def delete_run(run_id: str) -> dict[str, Any]:
    run = repositories.get_run(run_id)
    if run is None:
        raise RunError("RunNotFound", "No such run.")
    if run.status in {Run.STATUS_QUEUED, Run.STATUS_RUNNING}:
        WORKER.cancel(run_id)
        repositories.update_run(run_id, status=Run.STATUS_CANCELLED)
    repositories.delete_run(run_id)
    _remove_run_dir(run_id)
    return {"deleted": True, "id": run_id}


def reconcile_interrupted_runs() -> list[str]:
    """Fail runs left queued/running by a previous process.

    Worker threads live only in memory: after a restart nothing is executing,
    so a non-terminal status is stale. Mark those runs failed with an honest
    reason and a persisted event. Startup never auto-runs anything — recovery
    is always explicit via ``restore``.
    """
    interrupted = [
        run.id for run in repositories.list_runs_by_status([Run.STATUS_QUEUED, Run.STATUS_RUNNING])
    ]
    for run_id in interrupted:
        repositories.update_run(
            run_id,
            status=Run.STATUS_FAILED,
            completed_at=_utcnow(),
            error={
                "type": "Interrupted",
                "message": (
                    "The backend restarted while this run was queued or running, so it "
                    "cannot continue. Restore the run to execute it again."
                ),
                "context": {"reconciled": True},
            },
        )
        emit_event(
            run_id,
            event_type="run.failed",
            status="failed",
            payload={"type": "Interrupted", "reason": "backend restart"},
        )
    return interrupted


def _remove_run_dir(run_id: str) -> None:
    """Best-effort removal of a run's artifact directory (storage-scoped)."""
    import shutil

    from backend.app.config import get_settings

    storage_root = get_settings().run_storage_dir.resolve()
    run_dir = (storage_root / run_id).resolve()
    if run_dir.is_relative_to(storage_root) and run_dir.is_dir():
        shutil.rmtree(run_dir, ignore_errors=True)


def _utcnow() -> Any:
    from datetime import UTC, datetime

    return datetime.now(UTC)


# ─────────────────── DTO assembly ───────────────────────────────


def run_summary(run: Run) -> dict[str, Any]:
    return {
        "id": run.id,
        "datasetName": run.dataset_name,
        "datasetPath": run.dataset_path or "",
        "fileFormat": run.file_format or "",
        "rows": run.rows or 0,
        "columns": run.columns or 0,
        "fileSizeBytes": run.file_size_bytes or 0,
        "taskType": run.task_type or "unknown",
        "targetColumn": run.target_column,
        "engine": run.engine or "pandas",
        "engineReason": run.engine_reason or "",
        "bestModelType": run.best_model_type,
        "bestScore": run.best_score,
        "primaryMetric": run.primary_metric or "",
        "status": run.status,
        "mode": run.mode or "balanced",
        "createdAt": iso(run.created_at) or "",
        "updatedAt": iso(run.updated_at) or "",
        "durationMs": run.total_duration_ms,
        "trialCount": run.trial_count,
        "hpoTruncated": run.hpo_truncated,
        "stagesRequested": run.stages_requested or [],
        "error": _scrub_text((run.error or {}).get("message")) if run.error else None,
    }


def run_to_dict(run_id: str) -> dict[str, Any]:
    _assert_run(run_id)
    run = repositories.get_run(run_id)
    if run is None:
        raise RunError("RunNotFound", "No such run.")
    request = RunRequest(**run.request).model_dump() if run.request else {}
    return {
        "id": run.id,
        "status": run.status,
        "request": request,
        "summary": run_summary(run),
        "sampling": run.sampling_metadata,
        "resourceReport": run.resource_report,
        "warnings": [_scrub_text(w) for w in (run.warnings or [])],
        "error": _sanitized_error(run.error),
        "logs": [_scrub_text(line) for line in (run.logs or [])],
        "stagesRequested": run.stages_requested or [],
        "stagesExecuted": run.stages_executed or [],
        "totalDurationMs": run.total_duration_ms,
        "createdAt": iso(run.created_at) or "",
        "updatedAt": iso(run.updated_at) or "",
    }


def run_logs(run_id: str) -> list[str]:
    run = repositories.get_run(run_id)
    if run is None:
        raise RunError("RunNotFound", "No such run.")
    if run.logs:
        return list(run.logs)
    from backend.app.config import get_settings

    settings = get_settings()
    log_file = settings.run_storage_dir / run_id / "logs.txt"
    if log_file.is_file():
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        return [line for line in lines if line.strip()]
    return []


def list_runs(
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    dataset_id: str | None = None,
    search: str | None = None,
    task_type: str | None = None,
    sort: str | None = None,
    order: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    runs, total = repositories.list_runs(
        page=page,
        page_size=page_size,
        status=status,
        dataset_id=dataset_id,
        search=search,
        task_type=task_type,
        sort=sort,
        order=order,
        user_id=user_id,
    )
    return {
        "items": [run_summary(r) for r in runs],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "hasMore": page * page_size < total,
    }


def recent_activity(limit: int = 8, user_id: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "id": run.id,
            "datasetName": run.dataset_name or run.id,
            "status": run.status,
            "taskType": run.task_type or "unknown",
            "bestModelType": run.best_model_type,
            "bestScore": run.best_score,
            "createdAt": iso(run.created_at) or "",
            "durationMs": run.total_duration_ms,
        }
        for run in repositories.list_recent_runs(limit, user_id=user_id)
    ]


def run_dataset(run_id: str) -> dict[str, Any] | None:
    run = _assert_run(run_id)
    from backend.app.services.dataset_service import for_run

    return for_run(run)


def _assert_run(run_id: str) -> Run:
    run = repositories.get_run(run_id)
    if run is None:
        raise RunError("RunNotFound", "No such run.")
    return run


def _jsonable_request(request: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in request.items() if k != "datasetId"}
    stages = canonical_stages(list(request.get("stages") or []))
    if stages != request.get("stages"):
        out["stages"] = stages
    if request.get("datasetId"):
        out["datasetId"] = request["datasetId"]
    return out


def _scrub_text(text: str) -> str:
    """Replace absolute filesystem paths with placeholders before shipping a
    run DTO over the API — never expose host layout or user directories."""
    from pathlib import Path

    from backend.app.config import ROOT_DIR, get_settings

    settings = get_settings()
    roots = [
        ROOT_DIR,
        settings.data_storage_dir,
        settings.run_storage_dir,
        settings.artifact_storage_dir,
        settings.report_storage_dir,
    ]
    out = text
    for root in roots:
        out = out.replace(str(root), "<storage-root>")
    return out.replace(str(Path.home()), "~")


def _sanitized_error(error: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop tracebacks and scrub paths from a run's persisted error object.

    The worker stores the raw traceback for debugging; the API must never
    ship it (it leaks absolute paths and internals). Type + scrubbed message
    alone keep the UI informed without exposing host layout.
    """
    if not error:
        return None
    safe: dict[str, Any] = {
        "type": _scrub_text(str(error.get("type") or "Error")),
        "message": _scrub_text(str(error.get("message") or "")),
    }
    context = error.get("context")
    if isinstance(context, dict):
        safe_context = {
            str(key): _scrub_text(str(value))
            for key, value in context.items()
            if key != "traceback"
        }
        if safe_context:
            safe["context"] = safe_context
    return safe
