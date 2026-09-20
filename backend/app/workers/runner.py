"""Run worker — executes a PhronesisML pipeline in a dedicated thread.

Design:
- One daemon thread per run, each with its own asyncio event loop.
- The run is driven directly against the SDK graph via
  ``graph.astream(stream_mode="updates")`` so every node completion is
  observable and becomes a real, persisted ``pipeline.stage`` event
  (no fabricated percentages — progress derives from completed nodes).
- Final state is reconstructed node-by-node, the report is re-rendered
  with the terminal ``completed`` status (mirroring the SDK's own
  re-render), artifacts are indexed into the ``artifacts`` table, and
  model leaderboard rows are persisted.
- Cancellation is cooperative (checked between nodes).
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.config import Settings, get_settings
from backend.app.db import repositories
from backend.app.db.models import Run as RunModel
from backend.app.services.events import emit_event
from phronesisml import _FULL_PIPELINE_STAGES  # noqa: PLC2701  (canonical stage order)

# Stages that get a pre-flight sampling node inserted before them.
_SAMPLING_PRECEDENCE: frozenset[str] = frozenset(
    {"eda", "feature_engineering", "model_selection", "explainability", "reporting"}
)

_STAGE_LABELS: dict[str, str] = {
    "upload": "Data Upload",
    "etl": "ETL & Cleaning",
    "validation": "Validation",
    "eda": "EDA & Profiling",
    "target_detection": "Target & Task Detection",
    "feature_engineering": "Feature Engineering",
    "model_selection": "Model Selection & Training",
    "evaluation": "Evaluation",
    "explainability": "Explainability (SHAP)",
    "reporting": "Report Generation",
    "storage": "Artifact Storage",
}

_KIND_BY_EXT: dict[str, tuple[str, str]] = {
    "model.json": ("model", "json"),
    "model.joblib": ("model_binary", "joblib"),
    "training.json": ("training", "json"),
    "evaluation.json": ("evaluation", "json"),
    "metrics.json": ("metrics", "json"),
    "shap.json": ("shap", "json"),
    "config.json": ("config", "json"),
    "feature_metadata.json": ("feature_metadata", "json"),
    "target_detection.json": ("target_detection", "json"),
    "eda.json": ("eda", "json"),
    "validation.json": ("validation", "json"),
    "resource_estimation.json": ("resource_estimation", "json"),
    "engine_selection.json": ("engine_selection", "json"),
    "pipeline.json": ("pipeline", "json"),
    "run_metadata.json": ("run_metadata", "json"),
    "logs.txt": ("logs", "txt"),
    "report.md": ("report", "md"),
    "report.html": ("report", "html"),
}

_ARTIFACT_DESCRIPTIONS: dict[str, str] = {
    "model.json": "Trained best model metadata (estimator, params, score, cost).",
    "model.joblib": "Serialized best scikit-learn model (binary).",
    "training.json": "Full best-pipeline object including HPO trials and cv_results.",
    "evaluation.json": "Evaluation report with task metrics (curves for binary tasks).",
    "metrics.json": "Primary metric maps extracted from the evaluation report.",
    "shap.json": "SHAP global feature importance + explainer metadata.",
    "config.json": "PhronesisConfig snapshot used for the run.",
    "feature_metadata.json": "Selected feature names + reproducible transform recipe.",
    "target_detection.json": "Detected target column, task type and confidence.",
    "eda.json": "Full statistical profile (shape, dtypes, numeric/categorical summaries).",
    "validation.json": "Data validation report (nulls, duplicates, empty columns).",
    "resource_estimation.json": "Pre-flight memory/runtime estimate and sampling decision.",
    "engine_selection.json": "Selected computation engine and routing basis.",
    "pipeline.json": "Structured JSON pipeline report.",
    "run_metadata.json": "Canonical run index (status, target, engine, artifact list).",
    "logs.txt": "Deterministic run log lines (transform + warning entries).",
    "report.md": "Human-readable Markdown report.",
    "report.html": "Self-contained HTML rendering of the report.",
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def ordered_items(stages: list[str]) -> list[tuple[str, str]]:
    """Return ``(node_kind, stage_id)`` items: ``node_kind`` in {"stage","sampling"}."""
    items: list[tuple[str, str]] = []
    for stage in _FULL_PIPELINE_STAGES:
        if stage not in stages:
            continue
        if stage in _SAMPLING_PRECEDENCE:
            items.append(("sampling", "node_sampling"))
        items.append(("stage", stage))
    return items


def canonical_stages(stages: list[str]) -> list[str]:
    """Condense the requested stages into the canonical pipeline order."""
    return [s for s in _FULL_PIPELINE_STAGES if s in stages]


def stage_id_for_node(node_name: str) -> str:
    """Map a LangGraph node name to its display stage id."""
    if node_name.startswith("sampling_before_"):
        return "node_sampling"
    return node_name


def stage_summary(node_kind: str, stage_id: str, state: dict[str, Any]) -> dict[str, Any]:
    """Build a small, honest per-stage summary from the current state."""
    if stage_id == "node_sampling":
        meta = state.get("sampling_metadata") or {}
        resource = state.get("resource_report") or {}
        if meta.get("was_sampled"):
            return {
                "was_sampled": True,
                "sampling_method": meta.get("sampling_method"),
                "original_rows": meta.get("original_rows"),
                "sample_rows": meta.get("sample_rows"),
            }
        if resource.get("requires_sampling") is False:
            return {
                "was_sampled": False,
                "reason": resource.get("sampling_reason") or "no sampling required",
            }
        return {"was_sampled": False}

    if stage_id == "upload":
        profile = state.get("data_profile") or {}
        shape = profile.get("shape") or {}
        return {"rows": shape.get("rows"), "columns": shape.get("columns")}
    if stage_id == "etl":
        log = state.get("transform_log") or []
        return {"transformations": len(log)}
    if stage_id == "validation":
        report = state.get("validation_report") or {}
        return {
            "passed": report.get("passed"),
            "duplicate_rows": report.get("duplicate_rows"),
            "null_columns": len(report.get("null_columns") or []),
        }
    if stage_id == "eda":
        profile = state.get("data_profile") or {}
        return {
            "numeric_columns": len(profile.get("numeric_columns") or []),
            "categorical_columns": len(profile.get("categorical_columns") or []),
        }
    if stage_id == "target_detection":
        return {
            "target": state.get("target_column"),
            "task": state.get("task_type"),
            "confidence": state.get("target_detection_confidence"),
        }
    if stage_id == "feature_engineering":
        names = state.get("feature_names") or []
        return {"features": len(names)}
    if stage_id == "model_selection":
        best = state.get("best_pipeline") or {}
        return {
            "best_model": best.get("model_type") or best.get("candidate"),
            "score": best.get("score"),
            "trials_used": best.get("trials_used"),
        }
    if stage_id == "evaluation":
        report = state.get("evaluation_report") or {}
        metrics = report.get("metrics") or {}
        return {
            "task": report.get("task_type"),
            "n_metrics": len({k: v for k, v in metrics.items() if isinstance(v, (int, float))}),
        }
    if stage_id == "explainability":
        report = state.get("explanation_report") or {}
        return {
            "explainer": report.get("explainer_type"),
            "features_used": report.get("n_features_used"),
        }
    if stage_id == "reporting":
        report = state.get("final_report") or ""
        return {"report_length": len(report)}
    if stage_id == "storage":
        return {"artifact_uri": state.get("artifact_uri")}
    return {}


class RunWorker:
    """Schedules and supervises one pipeline job per run id."""

    def __init__(self) -> None:
        self._threads: dict[str, threading.Thread] = {}
        self._cancelled: set[str] = set()
        self._lock = threading.Lock()

    def launch(self, run_id: str) -> None:
        with self._lock:
            if run_id in self._threads:
                return
            thread = threading.Thread(
                target=self._thread_main, args=(run_id,), name=f"run-{run_id}", daemon=True
            )
            self._threads[run_id] = thread
            thread.start()

    def cancel(self, run_id: str) -> None:
        with self._lock:
            self._cancelled.add(run_id)

    def clear_cancel(self, run_id: str) -> None:
        with self._lock:
            self._cancelled.discard(run_id)

    def is_cancelled(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._cancelled

    def is_active(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._threads

    def _thread_main(self, run_id: str) -> None:
        try:
            asyncio.run(self._execute(run_id))
        except Exception:  # pragma: no cover - defensive
            traceback.print_exc()
        finally:
            with self._lock:
                self._threads.pop(run_id, None)

    async def _execute(self, run_id: str) -> None:
        settings = get_settings()
        run = repositories.get_run(run_id)
        if run is None:
            return
        if run.status == RunModel.STATUS_CANCELLED:
            emit_event(run_id, event_type="run.cancelled", status="cancelled")
            return

        dataset = repositories.get_dataset(run.dataset_id) if run.dataset_id else None
        if dataset is None or not Path(dataset.path).is_file():
            self._fail(run_id, "DatasetMissing", "Dataset file is not available on disk.")
            return

        request = run.request or {}
        try:
            config = _build_config(request)
            from phronesisml.engines.engine_selector import select_engine

            engine = select_engine(config=config, data_path=dataset.path)
            engine_name = type(engine).__name__.removesuffix("Engine").lower()
            from phronesisml.agents.compose import compose_agents
            from phronesisml.workflow.graph import build_graph

            agents = compose_agents(
                config=config,
                engine=engine,
                agent_overrides={
                    "storage": {"base_dir": str(settings.run_storage_dir)},
                    "model_selection": _model_selection_overrides(request),
                },
            )
            stages = canonical_stages(request.get("stages") or list(_FULL_PIPELINE_STAGES))
            # The graph needs the upload agent to load raw_data from data_path,
            # but "upload" is an implicit bootstrap stage, not a display stage
            # (the UI's RunRequest stages never include it).
            wired = stages if "upload" in stages else ["upload", *stages]
            graph = build_graph(
                agents,
                stages=wired,
                sampling_config=config.sampling,
                engine=engine,
            )
        except Exception as exc:  # noqa: BLE001
            self._fail(run_id, "ConfigError", f"Pipeline configuration failed: {exc}")
            return

        items = ordered_items(stages)
        from phronesisml.workflow.state import WorkflowState

        initial = WorkflowState(
            data_path=str(Path(dataset.path)),
            run_id=run_id,
            status="running",
            config_snapshot=config.model_dump(mode="json"),
            engine_name=engine_name,
            max_file_size_bytes=settings.max_upload_bytes,
        )

        repositories.update_run(
            run_id,
            status=RunModel.STATUS_RUNNING,
            started_at=_utcnow(),
            engine=engine_name,
            engine_reason=_engine_reason(config, dataset.size_bytes),
        )
        emit_event(run_id, event_type="run.started", status="running")
        _enqueue_stage_rows(run_id, items)
        for _, stage_id in items:
            emit_event(
                run_id,
                event_type="pipeline.stage",
                stage=stage_id,
                status="queued",
                summary={"name": _STAGE_LABELS.get(stage_id, stage_id)},
            )

        state: dict[str, Any] = dict(initial)
        completed: list[str] = []
        prev_completed_at = time.monotonic()
        try:
            async for chunk in graph.astream(initial, stream_mode="updates"):
                if self.is_cancelled(run_id):
                    break
                if not isinstance(chunk, dict):
                    continue
                for node_name, update in chunk.items():
                    update = update or {}
                    state.update(update)
                    stage_id = stage_id_for_node(node_name)
                    if stage_id not in {s for _, s in items}:
                        continue
                    now = time.monotonic()
                    duration_ms = int((now - prev_completed_at) * 1000)
                    prev_completed_at = now
                    summary = stage_summary(
                        "sampling" if stage_id == "node_sampling" else "stage",
                        stage_id,
                        state,
                    )
                    repositories.update_stage(
                        run_id, stage_id, status="running", started_at=_utcnow()
                    )
                    emit_event(
                        run_id, event_type="pipeline.stage", stage=stage_id, status="running"
                    )
                    repositories.update_stage(
                        run_id,
                        stage_id,
                        status="completed",
                        completed_at=_utcnow(),
                        duration_ms=duration_ms,
                        summary=summary,
                    )
                    emit_event(
                        run_id,
                        event_type="pipeline.stage",
                        stage=stage_id,
                        status="completed",
                        summary=summary,
                    )
                    _emit_warnings(run_id, update)
                    if stage_id != "node_sampling" and stage_id not in completed:
                        completed.append(stage_id)
                    if stage_id == "model_selection" and state.get("best_pipeline"):
                        best = state["best_pipeline"]
                        emit_event(
                            run_id,
                            event_type="model.completed",
                            status="completed",
                            summary={
                                "model_type": best.get("model_type"),
                                "score": best.get("score"),
                            },
                        )
                    if stage_id == "storage":
                        for artifact_name in _list_run_files(settings, run_id):
                            emit_event(
                                run_id,
                                event_type="artifact.created",
                                status="available",
                                payload={"name": artifact_name},
                            )
        except Exception as exc:  # noqa: BLE001
            self._fail(run_id, type(exc).__name__, str(exc), traceback=traceback.format_exc())
            return

        if self.is_cancelled(run_id):
            repositories.update_run(
                run_id, status=RunModel.STATUS_CANCELLED, completed_at=_utcnow()
            )
            emit_event(run_id, event_type="run.cancelled", status="cancelled")
            return

        await self._finalize(run_id, settings, state, items, completed)

    async def _finalize(
        self,
        run_id: str,
        settings: Settings,
        state: dict[str, Any],
        items: list[tuple[str, str]],
        completed: list[str],
    ) -> None:
        from phronesisml.ml.reports.builder import build_report
        from phronesisml.services.storage import save_artifacts
        from phronesisml.workflow.state import WorkflowState

        try:
            final_obj = WorkflowState(**state)
        except Exception:  # noqa: BLE001
            final_obj = WorkflowState(run_id=run_id, status="completed")
            final_obj.config_snapshot = state.get("config_snapshot")
            final_obj.engine_name = state.get("engine_name")

        final_obj.run_id = run_id
        final_obj.status = "completed"
        with contextlib.suppress(Exception):
            final_obj.final_report = build_report(final_obj)

        try:
            result = save_artifacts(final_obj, base_dir=str(settings.run_storage_dir))
            artifact_uri = result.get("artifact_uri")
        except Exception as exc:  # noqa: BLE001
            self._fail(run_id, "StorageError", f"Artifact storage failed: {exc}")
            return

        stage_ids = [s for _, s in items if s != "node_sampling"]
        executed = [s for s in stage_ids if s in completed]

        warnings: list[str] = list(state.get("preflight_warnings") or [])
        warnings += list(result.get("warnings") or [])
        warnings = list(dict.fromkeys(warnings))

        best = state.get("best_pipeline") or {}
        evaluation = state.get("evaluation_report") or {}
        profile = state.get("data_profile") or {}
        shape = profile.get("shape") or {}

        repositories.replace_model_results(run_id, _model_rows(state, best))
        start_key = getattr(repositories.get_run(run_id), "started_at", None)

        repositories.update_run(
            run_id,
            status=RunModel.STATUS_COMPLETED,
            completed_at=_utcnow(),
            task_type=state.get("task_type"),
            target_column=state.get("target_column"),
            best_model_type=best.get("model_type"),
            best_score=_scalar(best.get("score")),
            primary_metric=_primary_metric(evaluation.get("task_type")),
            trial_count=_int(best.get("trials_used")),
            hpo_truncated=best.get("truncated"),
            sampling_metadata=state.get("sampling_metadata"),
            resource_report=state.get("resource_report"),
            transform_log=state.get("transform_log") or [],
            warnings=warnings,
            rows=state.get("row_count") or shape.get("rows"),
            columns=shape.get("columns"),
            file_format=state.get("file_format"),
            stages_executed=executed,
            total_duration_ms=_duration_ms(start_key),
            artifact_dir=artifact_uri,
        )

        final_run = repositories.get_run(run_id)
        if final_run is not None and final_run.dataset_id:
            repositories.update_dataset(
                final_run.dataset_id,
                task_type=state.get("task_type"),
                target_column=state.get("target_column"),
                last_used_run_id=run_id,
            )

        indexed = _list_run_files(settings, run_id)
        _index_artifacts(run_id, settings)
        for name in indexed:
            emit_event(
                run_id,
                event_type="artifact.created",
                status="available",
                payload={"name": name},
            )
        emit_event(
            run_id,
            event_type="run.completed",
            status="completed",
            summary={
                "best_model": best.get("model_type"),
                "score": best.get("score"),
            },
        )

    def _fail(
        self,
        run_id: str,
        err_type: str,
        message: str,
        traceback: str | None = None,
    ) -> None:
        repositories.update_run(
            run_id,
            status=RunModel.STATUS_FAILED,
            completed_at=_utcnow(),
            error={
                "type": err_type,
                "message": message,
                "context": {"traceback": traceback} if traceback else None,
            },
        )
        emit_event(
            run_id,
            event_type="pipeline.error",
            status="failed",
            payload={"type": err_type, "message": message},
        )
        emit_event(run_id, event_type="run.failed", status="failed")


# ─────────────────────── helpers ───────────────────────────────


def _enqueue_stage_rows(run_id: str, items: list[tuple[str, str]]) -> None:
    for position, (_, stage_id) in enumerate(items):
        repositories.create_stage(run_id, stage_id, position)


def _build_config(request: dict[str, Any]) -> Any:
    from phronesisml.configs.settings import PhronesisConfig

    config = PhronesisConfig()
    engine = request.get("engine")
    if engine and engine != "auto":
        config.engine.preferred = engine
    null_strategy = request.get("nullStrategy")
    if null_strategy in {"drop", "fill", "flag"}:
        config.null_strategy = null_strategy
    if request.get("varianceThreshold") is not None:
        config.feature_selection.variance_threshold = float(request["varianceThreshold"])
    if request.get("correlationThreshold") is not None:
        config.feature_selection.correlation_threshold = float(request["correlationThreshold"])
    if request.get("minFeatures") is not None:
        config.feature_selection.min_features = int(request["minFeatures"])
    sampling = request.get("samplingStrategy")
    if sampling:
        config.sampling.sample_strategy = sampling
    return config


def _model_selection_overrides(request: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if request.get("cv") is not None:
        overrides["cv"] = int(request["cv"])
    if request.get("modelType"):
        overrides["model_type"] = request["modelType"]
    if request.get("maxTrials") is not None:
        overrides["max_trials"] = int(request["maxTrials"])
    if request.get("maxTimeSeconds") is not None:
        overrides["max_time_seconds"] = int(request["maxTimeSeconds"])
    return overrides


def _engine_reason(config: Any, size_bytes: int) -> str:
    preferred = config.engine.preferred
    if preferred:
        return f"engine forced by user: {preferred}"
    from phronesisml.configs.settings import PANDAS_MAX_BYTES

    if size_bytes < PANDAS_MAX_BYTES:
        return "file < 2 MB → pandas (fastest startup)"
    if size_bytes <= config.data.max_memory_bytes:
        return "file within 500 MB ceiling → polars (default single-machine engine)"
    return "file exceeds 500 MB ceiling → spark (distributed)"


def _emit_warnings(run_id: str, update: dict[str, Any]) -> None:
    warnings = update.get("preflight_warnings")
    if not warnings:
        return
    for warning in warnings if isinstance(warnings, list) else [warnings]:
        emit_event(
            run_id,
            event_type="pipeline.warning",
            status="warning",
            summary={"message": str(warning)},
        )


def _list_run_files(settings: Settings, run_id: str) -> list[str]:
    artifact_dir = settings.run_storage_dir / run_id
    if not artifact_dir.is_dir():
        return []
    return sorted(p.name for p in artifact_dir.iterdir() if p.is_file())


def _index_artifacts(run_id: str, settings: Settings) -> None:
    items = []
    artifact_dir = settings.run_storage_dir / run_id
    if not artifact_dir.is_dir():
        repositories.index_artifacts(run_id, [])
        return
    for path in sorted(artifact_dir.iterdir()):
        if not path.is_file():
            continue
        name = path.name
        kind, fmt = _KIND_BY_EXT.get(name, ("pipeline", path.suffix.lstrip(".") or "json"))
        items.append(
            {
                "name": name,
                "kind": kind,
                "format": fmt,
                "size_bytes": path.stat().st_size,
                "status": "available",
                "description": _ARTIFACT_DESCRIPTIONS.get(name, "Run artifact."),
                "url": f"/api/v1/runs/{run_id}/artifacts/{name}/content",
            }
        )
    repositories.index_artifacts(run_id, items)


def _model_rows(state: dict[str, Any], best: dict[str, Any]) -> list[dict[str, Any]]:
    cv_results = best.get("cv_results") if isinstance(best, dict) else None
    rows: list[dict[str, Any]] = []
    if isinstance(cv_results, list) and cv_results:
        best_score = _scalar(best.get("score"))
        entries = sorted(cv_results, key=lambda e: _scalar(e.get("score")) or 0.0, reverse=True)
        for rank, entry in enumerate(entries, start=1):
            score = _scalar(entry.get("score")) or 0.0
            rows.append(
                {
                    "rank": rank,
                    "model_type": str(entry.get("candidate") or "model"),
                    "primary_score": score,
                    "secondary_metrics": {},
                    "trials_used": 1,
                    "time_elapsed": _scalar(entry.get("time_sec")),
                    "truncated": bool(best.get("truncated")),
                    "estimated_training_cost": best.get("estimated_training_cost") or "unknown",
                    "best": score == best_score and rank == 1,
                }
            )
    else:
        name = str(
            best.get("model_type")
            or best.get("candidate")
            or type(state.get("trained_model") or object).__name__
        )
        rows.append(
            {
                "rank": 1,
                "model_type": name,
                "primary_score": _scalar(best.get("score")),
                "secondary_metrics": {},
                "trials_used": _int(best.get("trials_used")),
                "time_elapsed": _scalar(best.get("time_elapsed")),
                "truncated": bool(best.get("truncated")),
                "estimated_training_cost": best.get("estimated_training_cost") or "unknown",
                "best": True,
            }
        )
    return rows


def _primary_metric(task_type: str | None) -> str:
    return {"classification": "accuracy", "regression": "r2"}.get(task_type or "", "score")


def _duration_ms(started_at: Any) -> int | None:
    if started_at is None:
        return None
    start = started_at
    if start.tzinfo is not None:
        start = start.astimezone(UTC).replace(tzinfo=None)
    now = datetime.now(UTC).replace(tzinfo=None)
    return int((now - start).total_seconds() * 1000)


def _scalar(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


WORKER = RunWorker()
