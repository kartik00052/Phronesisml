"""Explainability agent — generates model explanations using SHAP.

This agent consumes the trained model from Model Selection and produces
feature importance explanations that help users understand *why* the
model makes its predictions.

Responsibilities:
- Consume the trained model — never retrain or re-select a model.
- Select the appropriate SHAP explainer based on model class (tree
  explainer for tree-based models, linear explainer for linear models,
  KernelExplainer as fallback).
- Compute global feature importance via mean absolute SHAP values.
- Resource-bound SHAP computation via ``max_samples`` (default 100).
  If the dataset exceeds the cap, a sample is drawn and the output
  flags that explanations are based on a sample.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Consumes, never retrains: only explains the model provided by
  Model Selection.
- Thin orchestrator: delegates to ``ml.explainability.shap_explainer``
  for real SHAP computation.
- Returns: dict with ``explanation_report`` that LangGraph merges
  into the workflow state.

Resource bounds:
- ``max_samples`` (default 100): caps rows used for SHAP computation.
  Enforced as a hard ceiling — if dataset exceeds this, a random
  sample is drawn and ``sampled=True`` is set in the output.
  This prevents resource exhaustion for non-tree explainers.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.agents.base import AgentResult, Tool
from phronesisml.engines.base_engine import BaseEngine
from phronesisml.ml.explainability.shap_explainer import (
    DEFAULT_MAX_SAMPLES,
    compute_shap_explanations,
)

logger = logging.getLogger(__name__)


class ExplainabilityAgent:
    """Agent responsible for generating model explanations via SHAP.

    Args:
        engine: The active computation engine (for data operations).
        max_samples: Maximum rows for SHAP computation.  Enforced as
            a hard ceiling — prevents resource exhaustion for non-tree
            explainers.  Default 100.

    """

    name = "explainability"
    description = "Generate SHAP-based model explanations and feature importance."

    def __init__(
        self,
        engine: BaseEngine,
        max_samples: int = DEFAULT_MAX_SAMPLES,
    ) -> None:
        self._engine = engine
        self._max_samples = max_samples

    async def run(self, state: Any) -> AgentResult:
        """Generate explanations for the trained model.

        Reads from: ``state.trained_model``, ``state.features``
        (or ``state.validated_data``/``state.processed_data``),
        ``state.feature_names``, ``state.target_column``

        Returns: dict with ``explanation_report``
        """
        # ── Resolve inputs ───────────────────────────────────────────
        trained_model = getattr(state, "trained_model", None)
        if trained_model is None:
            return AgentResult(
                success=False,
                error="No trained_model in workflow state. Run model selection first.",
            )

        data = (
            state.features
            if state.features is not None
            else (
                state.validated_data if state.validated_data is not None else state.processed_data
            )
        )
        if data is None:
            return AgentResult(
                success=False,
                error="No features, validated_data, or processed_data in workflow state.",
            )

        target_column = getattr(state, "target_column", None)
        feature_names = getattr(state, "feature_names", None)

        # ── Collect data to pandas ───────────────────────────────────
        collected = self._engine.cached_collect(data)

        # ── Resolve feature names ────────────────────────────────────
        if feature_names is None:
            feature_names = [c for c in collected.columns if c != target_column]

        # ── Build feature matrix ─────────────────────────────────────
        X = collected[feature_names].values

        # ── Compute SHAP explanations ────────────────────────────────
        try:
            report = compute_shap_explanations(
                model=trained_model,
                X=X,
                feature_names=feature_names,
                max_samples=self._max_samples,
            )
        except Exception as exc:
            msg = f"SHAP computation failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        # ── Log results ──────────────────────────────────────────────
        logger.info(
            "Explainability complete: explainer=%s, features=%d, sampled=%s.",
            report["explainer_type"],
            len(report["feature_importance"]),
            report["sampled"],
        )

        return AgentResult(
            success=True,
            data={
                "explanation_report": report,
            },
            metadata={
                "explainer_type": report["explainer_type"],
                "n_features": len(report["feature_importance"]),
                "sampled": report["sampled"],
                "n_samples_used": report["n_samples_used"],
            },
        )

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="explain_model",
                description="Generate SHAP-based feature importance explanations.",
                parameters={
                    "max_samples": {
                        "type": "integer",
                        "description": (
                            f"Max rows for SHAP computation (default: {DEFAULT_MAX_SAMPLES})."
                        ),
                    },
                },
            ),
        ]
