"""Storage agent — persist models, data, and artifacts.

Saves pipeline artifacts (trained model, reports, processed data) to
a local directory structure.  Writes to ``state.artifact_uri``.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Uses a local filesystem layout: ``<run_id>/`` directory with
  subdirectories for model, data, and reports.
- Graceful degradation: if disk write fails, returns failure result
  instead of crashing the pipeline.
- Future: will integrate with MLflow for experiment tracking and
  model registry when ``database.mlflow`` is implemented.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from phronesisml.agents.base import AgentResult, Tool

logger = logging.getLogger(__name__)


class StorageAgent:
    """Agent responsible for persisting pipeline artifacts.

    Args:
        base_dir: Base directory for artifact storage.
            Defaults to ``./Phronesis_artifacts``.

    """

    name = "storage"
    description = "Persist models, data, and artifacts to durable storage."

    def __init__(self, base_dir: str | Path = "./Phronesis_artifacts") -> None:
        self._base_dir = Path(base_dir)

    async def run(self, state: Any) -> AgentResult:
        """Persist pipeline artifacts to disk.

        Reads from: ``state.run_id``, ``state.trained_model``,
        ``state.final_report``, ``state.processed_data``,
        ``state.evaluation_report``.

        Writes to: ``state.artifact_uri``.

        """
        run_id = getattr(state, "run_id", None) or "default_run"
        artifact_dir = self._base_dir / run_id

        logger.info("Storage agent: persisting artifacts to %s.", artifact_dir)

        try:
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
                "Storage agent: saved %d artifacts to %s.",
                len(saved_files),
                artifact_uri,
            )

            return AgentResult(
                success=True,
                data={"artifact_uri": artifact_uri},
                metadata={"saved_files": saved_files},
            )

        except Exception as exc:
            msg = f"Storage failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="save_artifacts",
                description="Persist pipeline artifacts to durable storage.",
                parameters={
                    "base_dir": {
                        "type": "string",
                        "description": "Override base directory for artifact storage.",
                    },
                },
            ),
        ]
