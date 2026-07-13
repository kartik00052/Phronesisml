"""Validation agent — inspects data schema, types, and quality.

This agent receives the processed DataFrame from the workflow state and
runs validation checks using the active computation engine:

1. Schema inspection: infer column dtypes, detect nulls.
2. Quality checks: duplicate rows, fully-empty columns.
3. Hard failures: empty DataFrame or zero columns raises immediately.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Engine-mediated: all data operations go through ``BaseEngine`` —
  no direct pandas/polars imports.
- Returns: dict with ``validated_data`` and ``validation_report``
  that LangGraph merges into the workflow state.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.agents.base import AgentResult, Tool
from phronesisml.data.validators.checks import validate_dataframe
from phronesisml.engines.base_engine import BaseEngine
from phronesisml.exceptions import DataValidationError

logger = logging.getLogger(__name__)


class ValidationAgent:
    """Agent responsible for validating data schema and quality.

    Args:
        engine: The active computation engine used for data introspection.

    """

    name = "validation"
    description = "Validate data schema, types, and quality constraints."

    def __init__(self, engine: BaseEngine) -> None:
        self._engine = engine

    async def run(self, state: Any) -> AgentResult:
        """Validate ``state.processed_data`` and return a validation report.

        Reads from: ``state.processed_data``
        Returns: dict with ``validated_data`` and ``validation_report``
        """
        processed_data = state.processed_data
        if processed_data is None:
            return AgentResult(
                success=False,
                error="No processed_data in workflow state. Run the ETL agent first.",
            )

        try:
            validated_data, report = validate_dataframe(
                processed_data,
                self._engine,
            )

            logger.info(
                "Validation complete: %d rows, %d columns, passed=%s.",
                report["shape"]["rows"],
                report["shape"]["columns"],
                report["passed"],
            )
            return AgentResult(
                success=True,
                data={
                    "validated_data": validated_data,
                    "validation_report": report,
                },
                metadata={
                    "rows": report["shape"]["rows"],
                    "columns": report["shape"]["columns"],
                },
            )
        except DataValidationError as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        except Exception as exc:
            msg = f"Unexpected error during validation: {exc}"
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
                name="validate_data",
                description="Run schema, type, and quality validation checks on a DataFrame.",
                parameters={
                    "checks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Validation checks to run (default: all).",
                    },
                },
            ),
        ]
