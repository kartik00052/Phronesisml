"""Model service — leaderboard and per-model detail from indexed run artifacts.

DTO shapes follow ``frontend/src/types/model.ts`` (snake_case row fields,
camelCase detail extras).
"""

from __future__ import annotations

from typing import Any

from backend.app.db import repositories
from backend.app.db.models import ModelResult
from backend.app.services.artifact_service import read_artifact_text


def list_models(run_id: str) -> list[dict[str, Any]] | None:
    if repositories.get_run(run_id) is None:
        return None
    rows = repositories.list_model_results(run_id)
    if not rows:
        return []
    return [_row_to_rank(row) for row in rows]


def get_model_detail(run_id: str, model_type: str) -> dict[str, Any] | None:
    rows = [r for r in repositories.list_model_results(run_id) if r.model_type == model_type]
    if not rows:
        return None
    row = rows[0]
    evaluation = read_artifact_text(run_id, "evaluation.json") or {}
    target = read_artifact_text(run_id, "target_detection.json") or {}
    feature_meta = read_artifact_text(run_id, "feature_metadata.json") or {}
    training = read_artifact_text(run_id, "training.json") or {}
    model_json = read_artifact_text(run_id, "model.json") or {}

    n_samples = (evaluation.get("model_info") or {}).get("n_samples")
    if n_samples is None:
        n_samples = (model_json.get("best_estimator") or {}).get("n_samples")
    return {
        "model_type": row.model_type,
        "model_class": (model_json.get("best_estimator") or {}).get("class")
        or model_json.get("model_class")
        or "",
        "best_params": (
            training.get("best_params")
            or (model_json.get("best_estimator") or {}).get("best_params")
            or {}
        ),
        "score": row.primary_score,
        "trials_used": row.trials_used,
        "time_elapsed": row.time_elapsed,
        "truncated": row.truncated,
        "estimated_training_cost": row.estimated_training_cost or "unknown",
        "taskType": evaluation.get("task_type") or target.get("task_type") or "unknown",
        "targetColumn": target.get("target_column"),
        "nFeatures": feature_meta.get("n_features"),
        "nSamples": n_samples,
        "evaluation": evaluation or None,
        "rank": row.rank,
        "best": row.best,
    }


def _row_to_rank(row: ModelResult) -> dict[str, Any]:
    return {
        "rank": row.rank,
        "model_type": row.model_type,
        "primary_score": row.primary_score,
        "secondary_metrics": row.secondary_metrics or {},
        "trials_used": row.trials_used,
        "time_elapsed": row.time_elapsed,
        "truncated": row.truncated,
        "estimated_training_cost": row.estimated_training_cost or "unknown",
        "best": row.best,
        "status": "ready" if row.best else "failed" if row.primary_score is None else "candidate",
    }
