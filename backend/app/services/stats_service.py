"""Stats service — dashboard aggregates computed from the database.

Mirrors ``frontend/src/types/run.ts`` DashboardStats: engine/task
breakdowns are keyed records (engine/task name → count).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from backend.app.db import repositories
from backend.app.db.repositories import iso


def dashboard() -> dict[str, Any]:
    stats = repositories.run_stats()
    engine_breakdown = {str(k): int(v) for k, v in (stats["engine_breakdown"] or {}).items()}
    task_breakdown = {str(k): int(v) for k, v in (stats["task_breakdown"] or {}).items()}
    return {
        "totalRuns": int(stats["total_runs"]),
        "activeRuns": int(stats["active_runs"]),
        "queuedRuns": int(stats["queued_runs"]),
        "completedRuns": int(stats["completed_runs"]),
        "failedRuns": int(stats["failed_runs"]),
        "cancelledRuns": int(stats["cancelled_runs"]),
        "totalDatasets": int(stats["total_datasets"]),
        "totalModels": repositories.count_model_results(),
        "avgBestScore": _round4(stats["avg_best_score"]),
        "avgDurationMs": stats["avg_duration_ms"],
        "totalArtifacts": repositories.count_artifacts(),
        "engineBreakdown": engine_breakdown,
        "taskBreakdown": task_breakdown,
        "generatedAt": iso(datetime.now(UTC)),
    }


def recent_runs(limit: int = 6) -> list[dict[str, Any]]:
    return [
        {
            "id": run.id,
            "datasetName": run.dataset_name,
            "status": run.status,
            "taskType": run.task_type or "unknown",
            "bestModelType": run.best_model_type,
            "bestScore": _round4(run.best_score),
            "createdAt": iso(run.created_at),
            "durationMs": run.total_duration_ms,
        }
        for run in repositories.list_recent_runs(limit)
    ]


def _round4(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value):
        return None
    return round(float(value), 4)
