"""EDA agent — exploratory data analysis and statistical profiling.

This agent receives the validated DataFrame from the workflow state and
produces descriptive statistics and distribution analysis using the
active computation engine:

1. Descriptive statistics per column (min/max/mean/std for numeric;
   cardinality/top values for categorical).
2. Dataset-level summary (shape, dtypes, memory usage).

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Engine-mediated: all data operations go through ``BaseEngine`` —
  no direct pandas/polars imports.
- Thin orchestrator: delegates to ``data.profilers.stats`` for real
  computation logic.
- Returns: dict with ``data_profile`` and ``eda_report``
  that LangGraph merges into the workflow state.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.agents.base import AgentResult, Tool
from phronesisml.data.profilers.stats import profile_dataset
from phronesisml.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)


class EDAAgent:
    """Agent responsible for exploratory data analysis and profiling.

    Args:
        engine: The active computation engine used for data operations.

    """

    name = "eda"
    description = "Perform exploratory data analysis and statistical profiling."

    def __init__(self, engine: BaseEngine) -> None:
        self._engine = engine

    async def run(self, state: Any) -> AgentResult:
        """Profile ``state.validated_data`` (or ``state.processed_data``).

        Reads from: ``state.validated_data`` (preferred) or
        ``state.processed_data`` (fallback).
        Returns: dict with ``data_profile`` and ``eda_report``
        """
        data = state.validated_data if state.validated_data is not None else state.processed_data
        if data is None:
            return AgentResult(
                success=False,
                error="No validated_data or processed_data in workflow state.",
            )

        try:
            profile = profile_dataset(data, self._engine)

            eda_report = {
                "summary": f"Dataset has {profile['shape']['rows']} rows and "
                f"{profile['shape']['columns']} columns.",
                "numeric_columns": profile["numeric_columns"],
                "categorical_columns": profile["categorical_columns"],
                "memory_bytes": profile["memory_bytes"],
            }

            logger.info(
                "EDA complete: %d rows, %d columns, %d numeric, %d categorical.",
                profile["shape"]["rows"],
                profile["shape"]["columns"],
                len(profile["numeric_columns"]),
                len(profile["categorical_columns"]),
            )
            return AgentResult(
                success=True,
                data={
                    "data_profile": profile,
                    "eda_report": eda_report,
                },
                metadata={
                    "rows": profile["shape"]["rows"],
                    "columns": profile["shape"]["columns"],
                },
            )
        except Exception as exc:
            msg = f"Unexpected error during EDA: {exc}"
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
                name="profile_data",
                description="Compute descriptive statistics and distribution info for a DataFrame.",
                parameters={
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific columns to profile (default: all).",
                    },
                },
            ),
        ]
