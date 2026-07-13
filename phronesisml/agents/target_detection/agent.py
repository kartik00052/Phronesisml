"""Target detection agent — identifies the target column and task type.

This agent receives the processed DataFrame and EDA profile from the
workflow state and uses heuristic rules to detect:

1. The likely target column (by name signals, cardinality, dtype).
2. The ML task type (classification, regression, or ambiguous).

Ambiguity handling:
- A numeric column with 2–5 unique values is genuinely ambiguous.
- When confidence falls below ``AMBIGUITY_THRESHOLD`` (0.6), the agent
  surfaces ``ambiguity_reason`` rather than guessing silently.
- The threshold and its rationale are documented in both this docstring
  and ``ml.target_detection.detector`` — they must agree.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Engine-mediated: all data operations go through ``BaseEngine`` —
  no direct pandas/polars imports.
- Thin orchestrator: delegates to ``ml.target_detection.detector``
  for real detection logic.
- Returns: dict with ``target_column``, ``task_type``,
  ``target_detection_confidence``, ``ambiguity_reason``
  that LangGraph merges into the workflow state.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.agents.base import AgentResult, Tool
from phronesisml.engines.base_engine import BaseEngine
from phronesisml.ml.target_detection.detector import AMBIGUITY_THRESHOLD, detect_target

logger = logging.getLogger(__name__)


class TargetDetectionAgent:
    """Agent responsible for detecting the target variable and task type.

    Args:
        engine: The active computation engine used for data introspection.

    Ambiguity threshold:
        ``AMBIGUITY_THRESHOLD = 0.6`` — when the best candidate's
        confidence falls below this, the result is flagged as ambiguous
        and ``ambiguity_reason`` is populated.  This threshold is
        defined in ``ml.target_detection.detector`` and must match
        the value stated here.

    """

    name = "target_detection"
    description = "Identify the target variable and determine the ML task type."

    def __init__(self, engine: BaseEngine) -> None:
        self._engine = engine

    async def run(self, state: Any) -> AgentResult:
        """Detect the target column from ``state.processed_data`` and ``state.data_profile``.

        Reads from: ``state.processed_data`` (or ``state.validated_data``),
        ``state.data_profile``
        Returns: dict with ``target_column``, ``task_type``,
        ``target_detection_confidence``, ``ambiguity_reason``
        """
        data = state.processed_data if state.processed_data is not None else state.validated_data
        if data is None:
            return AgentResult(
                success=False,
                error="No processed_data or validated_data in workflow state.",
            )

        data_profile = state.data_profile
        if data_profile is None:
            return AgentResult(
                success=False,
                error="No data_profile in workflow state. Run the EDA agent first.",
            )

        try:
            result = detect_target(data, self._engine, data_profile)

            logger.info(
                "Target detection complete: column=%s, task=%s, confidence=%.2f, ambiguity=%s",
                result["target_column"],
                result["task_type"],
                result["confidence"],
                result["ambiguity_reason"] is not None,
            )
            return AgentResult(
                success=True,
                data={
                    "target_column": result["target_column"],
                    "task_type": result["task_type"],
                    "target_detection_confidence": result["confidence"],
                    "ambiguity_reason": result["ambiguity_reason"],
                },
                metadata={
                    "candidates": result["candidates"],
                    "ambiguity_threshold": AMBIGUITY_THRESHOLD,
                },
            )
        except Exception as exc:
            msg = f"Unexpected error during target detection: {exc}"
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
                name="detect_target",
                description="Identify the target column and ML task type using heuristic rules.",
                parameters={
                    "target_hint": {
                        "type": "string",
                        "description": "Optional user-provided hint for the target column name.",
                    },
                },
            ),
        ]
