"""ETL agent — cleans and transforms raw data.

This agent receives the raw DataFrame from the workflow state and applies
a configurable sequence of transformations:
1. Null handling (drop, fill, or flag missing values)
2. Type casting (coerce columns to target dtypes)
3. Categorical encoding (label-encode string columns)

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Composable: transformations are applied in order; each step is
  independently testable via ``data.transformers.cleaning``.
- Returns: dict with keys ``processed_data``, ``transform_log``
  that LangGraph merges into the workflow state.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from aetherml.agents.base import AgentResult, Tool
from aetherml.data.transformers.cleaning import (
    cast_dtypes,
    encode_categoricals,
    handle_nulls,
)
from aetherml.exceptions import DataTransformError

logger = logging.getLogger(__name__)


class ETLConfig:
    """Configuration for the ETL agent's transformation pipeline.

    Attributes:
        null_strategy: How to handle nulls (``"drop"``, ``"fill"``, ``"flag"``).
        fill_value: Value to use when ``null_strategy="fill"``.
        type_map: Column → dtype mapping for type casting.
            If ``None``, no casting is performed.
        encode_columns: Columns to label-encode.  If ``None``, all
            object-dtype columns are encoded.

    """

    def __init__(
        self,
        null_strategy: str = "drop",
        fill_value: Any = None,
        type_map: dict[str, str] | None = None,
        encode_columns: list[str] | None = None,
    ) -> None:
        self.null_strategy = null_strategy
        self.fill_value = fill_value
        self.type_map = type_map
        self.encode_columns = encode_columns


class ETLAgent:
    """Agent responsible for data cleaning and transformation.

    Args:
        config: ETL configuration.  Uses defaults (drop nulls, no casting,
            auto-encode categoricals) if ``None``.

    """

    name = "etl"
    description = "Clean and transform raw data into a processed DataFrame."

    def __init__(self, config: ETLConfig | None = None) -> None:
        self._config = config or ETLConfig()

    async def run(self, state: Any) -> AgentResult:
        """Apply ETL transformations to ``state.raw_data``.

        Reads from: ``state.raw_data``
        Returns: dict with ``processed_data`` and ``transform_log``
        """
        raw_data = state.raw_data
        if raw_data is None:
            return AgentResult(
                success=False,
                error="No raw_data in workflow state. Run the upload agent first.",
            )

        if not isinstance(raw_data, pd.DataFrame):
            return AgentResult(
                success=False,
                error=f"Expected pandas DataFrame, got {type(raw_data).__name__}.",
            )

        config = self._config
        transform_log: list[dict[str, Any]] = []
        df = raw_data.copy()

        try:
            # Step 1: Handle nulls
            df, null_log = handle_nulls(
                df,
                strategy=config.null_strategy,
                fill_value=config.fill_value,
            )
            transform_log.append(null_log)

            # Step 2: Cast dtypes (if configured)
            if config.type_map:
                df, cast_log = cast_dtypes(df, config.type_map)
                transform_log.append(cast_log)

            # Step 3: Encode categoricals
            df, encode_log = encode_categoricals(df, columns=config.encode_columns)
            transform_log.append(encode_log)

            logger.info(
                "ETL complete: %d rows, %d columns, %d transformations applied.",
                len(df),
                len(df.columns),
                len(transform_log),
            )
            return AgentResult(
                success=True,
                data={
                    "processed_data": df,
                    "transform_log": transform_log,
                },
                metadata={"columns": list(df.columns)},
            )
        except DataTransformError as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        except Exception as exc:
            msg = f"Unexpected error during ETL: {exc}"
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
                name="clean_data",
                description="Apply null handling, type casting, and encoding to raw data.",
                parameters={
                    "null_strategy": {
                        "type": "string",
                        "enum": ["drop", "fill", "flag"],
                    },
                    "type_map": {
                        "type": "object",
                        "description": "Column → dtype mapping",
                    },
                },
            ),
        ]
