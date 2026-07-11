"""Upload agent — loads data from a file path into the workflow state.

This is the first agent in the pipeline.  It receives a ``data_path``
from the user, detects the file format, loads the data via the active
engine, and returns the resulting DataFrame.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Engine-agnostic: delegates I/O to ``data.loaders.file_loader`` which
  uses whatever engine is active.
- Size guard: rejects files exceeding ``max_file_size_bytes`` before
  loading into memory.
- Returns: dict with keys ``raw_data``, ``file_format``, ``row_count``
  that LangGraph merges into the workflow state.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from aetherml.agents.base import AgentResult, Tool
from aetherml.data.loaders.file_loader import detect_format, load_file
from aetherml.engines.base_engine import BaseEngine
from aetherml.exceptions import DataLoadError

logger = logging.getLogger(__name__)


class UploadAgent:
    """Agent responsible for loading raw data into the workflow.

    Args:
        engine: The active computation engine used for data loading.
    """

    name = "upload"
    description = "Load raw data from a file path into the workflow state."

    def __init__(self, engine: BaseEngine) -> None:
        self._engine = engine

    async def run(self, state: Any) -> AgentResult:
        """Load data from ``state.data_path`` and return the loaded data."""
        data_path = state.data_path
        if not data_path:
            return AgentResult(
                success=False,
                error="No data_path provided in workflow state.",
            )

        try:
            # Size guard: reject files exceeding the configured limit.
            max_bytes = getattr(state, "max_file_size_bytes", None)
            if max_bytes is None:
                from aetherml.configs.settings import AetherMLConfig
                max_bytes = AetherMLConfig().data.max_file_size_bytes
            if os.path.exists(data_path):
                file_size = os.path.getsize(data_path)
                if file_size > max_bytes:
                    size_mb = file_size / (1024 * 1024)
                    limit_mb = max_bytes / (1024 * 1024)
                    return AgentResult(
                        success=False,
                        error=(
                            f"File too large: {size_mb:.1f} MB exceeds "
                            f"limit of {limit_mb:.1f} MB. "
                            "Increase data.max_file_size_bytes in config "
                            "or reduce the dataset size."
                        ),
                    )

            file_format = detect_format(data_path)
            df = load_file(data_path, self._engine)
            row_count = len(df)

            logger.info(
                "Upload complete: %s format, %d rows, %d columns",
                file_format,
                row_count,
                len(df.columns),
            )
            return AgentResult(
                success=True,
                data={
                    "raw_data": df,
                    "file_format": file_format,
                    "row_count": row_count,
                },
                metadata={"columns": list(df.columns)},
            )
        except DataLoadError as exc:
            return AgentResult(success=False, error=str(exc))
        except Exception as exc:
            msg = f"Unexpected error during upload: {exc}"
            logger.exception(msg)
            return AgentResult(success=False, error=msg)

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="load_data",
                description="Load a dataset from a file path.",
                parameters={
                    "data_path": {
                        "type": "string",
                        "description": "Path to the data file",
                    }
                },
            )
        ]
