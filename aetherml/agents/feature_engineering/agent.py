"""Feature engineering agent — transforms validated data into model-ready features.

This agent receives the validated DataFrame, EDA profile, and target
detection results from the workflow state and produces model-ready
features:

1. Handles remaining nulls (fill or flag — distinct from ETL's drop).
2. Encodes categoricals excluding the target column.
3. Scales numeric features (min-max, excluding the target).
4. Detects and flags outliers (IQR-based, flag by default).
5. Selects features via variance threshold and correlation-with-target.

Distinction from ETL (``agents/etl``):
- ETL runs *before* target detection and operates on ALL columns.
  Its job is to produce a clean DataFrame by dropping nulls and
  encoding every categorical.
- Feature Engineering runs *after* target detection.  It knows which
  column is the target and excludes it from all transforms.  It adds
  signal (scaling, outlier detection, feature selection) on top of
  ETL's clean base.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Engine-mediated: all data operations go through ``BaseEngine`` —
  no direct pandas/polars imports.
- Thin orchestrator: delegates to ``ml.feature_engineering.engineer``
  for real engineering logic.
- Returns: dict with ``features`` and ``feature_names``
  that LangGraph merges into the workflow state.
"""

from __future__ import annotations

import logging
from typing import Any

from aetherml.agents.base import AgentResult, Tool
from aetherml.engines.base_engine import BaseEngine
from aetherml.ml.feature_engineering.engineer import engineer_features

logger = logging.getLogger(__name__)


class FeatureEngineeringAgent:
    """Agent responsible for feature engineering and selection.

    Args:
        engine: The active computation engine used for data operations.
    """

    name = "feature_engineering"
    description = "Create model-ready features from validated data."

    def __init__(self, engine: BaseEngine) -> None:
        self._engine = engine

    async def run(self, state: Any) -> AgentResult:
        """Engineer features from ``state.validated_data`` (or ``state.processed_data``).

        Reads from: ``state.validated_data`` (preferred) or
        ``state.processed_data`` (fallback), ``state.data_profile``,
        ``state.target_column``, ``state.task_type``
        Returns: dict with ``features`` and ``feature_names``
        """
        data = state.validated_data if state.validated_data is not None else state.processed_data
        if data is None:
            return AgentResult(
                success=False,
                error="No validated_data or processed_data in workflow state.",
            )

        target_column = getattr(state, "target_column", None)

        try:
            features, log_entry = engineer_features(
                data,
                self._engine,
                target_column=target_column,
            )

            feature_names = [
                c for c in self._engine.columns(features)
                if c != target_column
            ]

            logger.info(
                "Feature engineering complete: %d rows, %d features.",
                self._engine.shape(features)[0],
                len(feature_names),
            )
            return AgentResult(
                success=True,
                data={
                    "features": features,
                    "feature_names": feature_names,
                },
                metadata={
                    "rows": self._engine.shape(features)[0],
                    "n_features": len(feature_names),
                    "target_excluded": target_column,
                },
            )
        except Exception as exc:
            msg = f"Unexpected error during feature engineering: {exc}"
            logger.exception(msg)
            return AgentResult(success=False, error=msg)

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="engineer_features",
                description="Transform validated data into model-ready features.",
                parameters={
                    "null_strategy": {
                        "type": "string",
                        "enum": ["fill", "flag"],
                        "description": "Strategy for remaining nulls (default: fill).",
                    },
                    "scale_numeric": {
                        "type": "boolean",
                        "description": "Whether to min-max scale numeric features (default: true).",
                    },
                    "detect_outliers": {
                        "type": "boolean",
                        "description": "Whether to flag outliers (default: true).",
                    },
                },
            )
        ]
