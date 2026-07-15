"""Storage agent — persist models, data, and artifacts.

Delegates file I/O to ``phronesisml.services.storage``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from phronesisml.agents.base import AgentResult, Tool
from phronesisml.services.storage import save_artifacts

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
        logger.info("Storage agent: persisting artifacts.")

        try:
            result = save_artifacts(state, base_dir=self._base_dir)
            return AgentResult(
                success=True,
                data={"artifact_uri": result["artifact_uri"]},
                metadata={"saved_files": result["saved_files"]},
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
