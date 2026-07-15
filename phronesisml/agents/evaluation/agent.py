"""Evaluation agent — evaluates trained model performance.

This agent consumes the trained model from Model Selection, computes
problem-type-appropriate metrics, and surfaces ambiguity signals from
Target Detection alongside the metrics.

Responsibilities:
- Consume the trained model — never retrain or re-select a model.
- Compute problem-type-appropriate metrics based on the task type
  recorded by Target Detection — never infer problem type independently.
- Surface ambiguity/confidence signals from Target Detection.
- Log to MLflow with graceful degradation if unavailable.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Consumes, never retrains: only evaluates the model provided by
  Model Selection.
- Problem-type dispatch: selects metric set based on ``task_type``
  from Target Detection.
- Graceful MLflow degradation: if MLflow isn't reachable/configured,
  logs a warning and continues.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.agents.base import AgentResult, Tool, resolve_features_target
from phronesisml.engines.base_engine import BaseEngine
from phronesisml.ml.evaluation.metrics import evaluate_model

logger = logging.getLogger(__name__)


class EvaluationAgent:
    """Agent responsible for evaluating trained model performance.

    Args:
        engine: The active computation engine (for data operations).

    """

    name = "evaluation"
    description = "Evaluate trained model performance using problem-type-appropriate metrics."

    def __init__(self, engine: BaseEngine) -> None:
        self._engine = engine

    async def run(self, state: Any) -> AgentResult:
        """Evaluate the trained model from workflow state.

        Reads from: ``state.trained_model``, ``state.features``
        (or ``state.validated_data``/``state.processed_data``),
        ``state.feature_names``, ``state.target_column``,
        ``state.task_type``, ``state.target_detection_confidence``,
        ``state.ambiguity_reason``, ``state.best_pipeline``

        Returns: dict with ``evaluation_report``
        """
        # ── Resolve inputs ───────────────────────────────────────────
        trained_model = getattr(state, "trained_model", None)
        if trained_model is None:
            return AgentResult(
                success=False,
                error="No trained_model in workflow state. Run model selection first.",
            )

        task_type = getattr(state, "task_type", None)

        best_pipeline = getattr(state, "best_pipeline", None)
        best_params = best_pipeline.get("params", {}) if best_pipeline else {}

        target_detection_confidence = getattr(state, "target_detection_confidence", None)
        ambiguity_reason = getattr(state, "ambiguity_reason", None)

        try:
            resolved = resolve_features_target(state, self._engine)
        except ValueError as exc:
            return AgentResult(success=False, error=str(exc))

        collected = resolved.collected
        feature_names = resolved.feature_names
        target_column = resolved.target_column

        # ── Evaluate ─────────────────────────────────────────────────
        try:
            report = evaluate_model(
                model=trained_model,
                df=collected,
                target_column=target_column,
                feature_names=feature_names,
                task_type=task_type,
                best_params=best_params,
                target_detection_confidence=target_detection_confidence,
                ambiguity_reason=ambiguity_reason,
            )
        except Exception as exc:
            msg = f"Model evaluation failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        # ── Log results ──────────────────────────────────────────────
        metrics = report.get("metrics", {})
        caveat = report.get("ambiguity_caveat")
        mlflow_logged = report.get("mlflow_logged", False)

        logger.info(
            "Evaluation complete: task=%s, metrics=%s, ambiguity=%s, mlflow=%s",
            task_type,
            list(metrics.keys()),
            caveat is not None,
            mlflow_logged,
        )

        return AgentResult(
            success=True,
            data={
                "evaluation_report": report,
            },
            metadata={
                "task_type": task_type,
                "n_metrics": len(metrics),
                "has_ambiguity_caveat": caveat is not None,
                "mlflow_logged": mlflow_logged,
            },
        )

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="evaluate_model",
                description="Evaluate a trained model using problem-type-appropriate metrics.",
                parameters={
                    "mlflow_experiment": {
                        "type": "string",
                        "description": "Optional MLflow experiment name.",
                    },
                },
            ),
        ]
