"""Pipeline service — stage list, overview, and real progress for a run.

Progress is derived only from authoritative state: the persisted stage rows
and the run's completed stage list — nothing is fabricated.  DTO shapes
follow ``frontend/src/types/pipeline.ts``.
"""

from __future__ import annotations

from typing import Any

from backend.app.db import repositories
from backend.app.db.repositories import iso
from backend.app.workers.runner import (
    _FULL_PIPELINE_STAGES,
    _STAGE_LABELS,
    canonical_stages,
    ordered_items,
    stage_id_for_node,
)

_STAGE_ORDER = {stage: i for i, stage in enumerate(_FULL_PIPELINE_STAGES)}
_DEFAULT_REQUESTED = _FULL_PIPELINE_STAGES


def stage_position(stage: str) -> int:
    return _STAGE_ORDER.get(stage, _STAGE_ORDER.get("reporting", 9))


def reset_stages(run_id: str, stages: list[str]) -> None:
    """Clear persisted stage rows and re-seed the canonical queue (for restore)."""
    from sqlalchemy import delete as sa_delete

    from backend.app.db.models import PipelineStage

    with repositories.session_scope() as session:
        session.execute(sa_delete(PipelineStage).where(PipelineStage.run_id == run_id))
        session.commit()
    for position, (_, stage_id) in enumerate(ordered_items(stages)):
        repositories.create_stage(run_id, stage_id, position)


def list_stages(run_id: str) -> list[dict[str, Any]] | None:
    run = repositories.get_run(run_id)
    if run is None:
        return None
    requested = canonical_stages(run.stages_requested or list(_DEFAULT_REQUESTED))
    rows = {stage_id_for_node(r.stage): r for r in repositories.get_stages(run_id)}

    items: list[dict[str, Any]] = []
    for _, stage_id in ordered_items(requested):
        is_sampling = stage_id == "node_sampling"
        row = rows.get(stage_id)
        default_status = "skipped" if is_sampling else "idle"
        items.append(
            {
                "id": stage_id,
                "name": (
                    "Sampling" if is_sampling else _STAGE_LABELS.get(stage_id, stage_id.title())
                ),
                "status": row.status if row else default_status,
                "queuedAt": iso(row.queued_at) if row else None,
                "startedAt": iso(row.started_at) if row else None,
                "completedAt": iso(row.completed_at) if row else None,
                "durationMs": row.duration_ms if row else None,
                "summary": row.summary or {} if row else {},
                "logs": list(row.logs or []) if row else [],
                "error": row.error if row else None,
            }
        )
    return items


def overview(run_id: str) -> dict[str, Any] | None:
    run = repositories.get_run(run_id)
    if run is None:
        return None
    stages = canonical_stages(run.stages_requested or list(_DEFAULT_REQUESTED))
    sampling = run.sampling_metadata or {}
    sampling_view = None
    if isinstance(sampling, dict) and sampling:
        sampling_view = {
            "was_sampled": bool(sampling.get("was_sampled")),
            "sampling_method": sampling.get("sampling_method"),
            "sampling_ratio": sampling.get("sampling_ratio"),
            "original_rows": sampling.get("original_rows"),
            "sample_rows": sampling.get("sample_rows"),
            "reason": sampling.get("reason") or sampling.get("sampling_reason"),
        }
    return {
        "runId": run.id,
        "mode": run.mode or "balanced",
        "stagesRequested": stages,
        "stagesExecuted": run.stages_executed or [],
        "sampling": sampling_view,
        "totalDurationMs": run.total_duration_ms or 0,
    }


def progress(run_id: str) -> dict[str, Any] | None:
    run = repositories.get_run(run_id)
    if run is None:
        return None
    stages = canonical_stages(run.stages_requested or list(_DEFAULT_REQUESTED))
    items = list_stages(run_id) or []
    completed = [s for s in (run.stages_executed or []) if s in stages]
    current = None
    for item in items:
        if item["status"] in {"idle", "queued", "running"}:
            current = item["id"]
        if item["status"] in {"idle", "queued"}:
            current = item["id"]
            break
    return {
        "runId": run.id,
        "status": run.status,
        "completedStages": completed,
        "currentStage": current,
        "currentStagesCompleted": len(completed),
        "totalStages": len(items) if items else len(stages),
        "messages": _messages(run),
    }


# ─────────────────── helpers ────────────────────────────────────


def _messages(run: Any) -> list[str]:
    out: list[str] = []
    if run.engine:
        out.append(f"Engine: {run.engine} ({run.engine_reason or 'selected'})")
    for stage in canonical_stages(run.stages_executed or []):
        label = _STAGE_LABELS.get(stage, stage.title())
        out.append(f"{label} completed")
    return out or ["Queued — waiting for the runner to pick up this run."]
