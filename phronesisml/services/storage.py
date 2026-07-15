"""Storage service — persist pipeline artifacts to disk.

Extracted from ``StorageAgent`` to separate file I/O logic from
agent orchestration.  All functions are pure (no agent dependency)
and can be called directly or through the agent.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def save_artifacts(
    state: Any,
    base_dir: str | Path = "./Phronesis_artifacts",
) -> dict[str, Any]:
    """Persist pipeline artifacts to disk.

    Reads from: ``state.run_id``, ``state.trained_model``,
    ``state.final_report``, ``state.processed_data``,
    ``state.evaluation_report``.

    Args:
        state: The current ``WorkflowState``.
        base_dir: Base directory for artifact storage.

    Returns:
        A dict with ``artifact_uri`` and ``saved_files``.

    Raises:
        OSError: If disk write fails.
    """
    run_id = getattr(state, "run_id", None) or "default_run"
    artifact_dir = Path(base_dir) / run_id

    logger.info("Storage service: persisting artifacts to %s.", artifact_dir)

    artifact_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []

    # Save evaluation report as JSON
    eval_report = getattr(state, "evaluation_report", None)
    if eval_report is not None:
        eval_path = artifact_dir / "evaluation_report.json"
        eval_path.write_text(
            json.dumps(eval_report, indent=2, default=str),
            encoding="utf-8",
        )
        saved_files.append(str(eval_path))

    # Save final report if present
    final_report = getattr(state, "final_report", None)
    if final_report is not None:
        report_path = artifact_dir / "final_report.md"
        report_path.write_text(str(final_report), encoding="utf-8")
        saved_files.append(str(report_path))

    # Save metadata summary
    metadata = {
        "run_id": run_id,
        "target_column": getattr(state, "target_column", None),
        "task_type": getattr(state, "task_type", None),
        "best_pipeline": getattr(state, "best_pipeline", None),
        "saved_files": saved_files,
    }
    meta_path = artifact_dir / "run_metadata.json"
    meta_path.write_text(
        json.dumps(metadata, indent=2, default=str),
        encoding="utf-8",
    )
    saved_files.append(str(meta_path))

    artifact_uri = str(artifact_dir)
    logger.info(
        "Storage service: saved %d artifacts to %s.",
        len(saved_files),
        artifact_uri,
    )

    return {"artifact_uri": artifact_uri, "saved_files": saved_files}
