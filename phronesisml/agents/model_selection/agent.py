"""Model selection agent — recommends and trains candidate models.

This agent consumes engineered features and target information from
the workflow state, recommends candidate models via rule-based
heuristics, trains them with resource-bounded hyperparameter search,
and writes the best model to the state.

Responsibilities:
- **Model recommendation**: rule-based on dataset metadata (task type,
  dataset size, feature count, feature types).
- **Train/test split**: stratified for classification, random for
  regression.  Respects the target/feature split from Target Detection
  and Feature Engineering.
- **Hyperparameter optimization**: resource-bounded via ``max_trials``
  and ``max_time_seconds`` with enforced defaults.  The search CANNOT
  run unbounded under any code path.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Engine-mediated: data operations go through ``BaseEngine``.
- Thin orchestrator: delegates to ``ml.automl.auto_selector`` for
  model recommendation and ``ml.automl.trainer`` for training.
- Returns: dict with ``candidate_models``, ``best_pipeline``,
  ``trained_model`` that LangGraph merges into the workflow state.

Resource bounds:
- ``max_trials`` (default 50): total parameter combinations across
  ALL candidates.  Hard ceiling — enforced by ``trainer.train_models()``.
- ``max_time_seconds`` (default 120): total wall-clock seconds.
  Checked via monotonic clock before each trial.
- These are enforced at the trainer level, not just documented.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.agents.base import AgentResult, Tool, resolve_features_target
from phronesisml.engines.base_engine import NUMERIC_DTYPES, BaseEngine
from phronesisml.ml.automl.auto_selector import (
    candidate_to_dict,
    estimate_training_cost,
    recommend_models,
)
from phronesisml.ml.automl.trainer import (
    DEFAULT_MAX_TIME_SECONDS,
    DEFAULT_MAX_TRIALS,
    train_models,
)

logger = logging.getLogger(__name__)


class ModelSelectionAgent:
    """Agent responsible for model recommendation and training.

    Args:
        engine: The active computation engine used for data operations.
        max_trials: Maximum total HPO trials across all candidates.
            Enforced as a hard ceiling — search stops when exceeded.
        max_time_seconds: Maximum total wall-clock seconds for HPO.
            Checked via monotonic clock before each trial.

    """

    name = "model_selection"
    description = "Recommend candidate models, run resource-bounded HPO, and train the best model."

    def __init__(
        self,
        engine: BaseEngine,
        max_trials: int = DEFAULT_MAX_TRIALS,
        max_time_seconds: int = DEFAULT_MAX_TIME_SECONDS,
        cv: int | None = None,
        model_type: str | None = None,
    ) -> None:
        self._engine = engine
        self._max_trials = max_trials
        self._max_time_seconds = max_time_seconds
        self._cv = cv
        self._model_type = model_type

    async def run(self, state: Any) -> AgentResult:
        """Recommend models and train the best one.

        Reads from: ``state.features`` (preferred) or
        ``state.validated_data``/``state.processed_data`` (fallback),
        ``state.feature_names``, ``state.target_column``,
        ``state.task_type``, ``state.data_profile``

        Returns: dict with ``candidate_models``, ``best_pipeline``,
        ``trained_model``
        """
        # ── Resolve input data ───────────────────────────────────────
        task_type = getattr(state, "task_type", None)
        if task_type is None:
            return AgentResult(
                success=False,
                error="No task_type in workflow state. Run target detection first.",
            )

        try:
            resolved = resolve_features_target(state, self._engine)
        except ValueError as exc:
            return AgentResult(success=False, error=str(exc))

        collected = resolved.collected
        feature_names = resolved.feature_names
        target_column = resolved.target_column

        # ── Recommend models ─────────────────────────────────────────
        n_rows = len(collected)
        n_features = len(feature_names)

        # ── Unsupervised tasks ────────────────────────────────────────
        if task_type in ("clustering", "anomaly_detection"):
            return await self._run_unsupervised(
                state, collected, feature_names, task_type, n_rows, n_features
            )

        # ── Supervised tasks ─────────────────────────────────────────
        dtypes = self._engine.dtypes(state.features if state.features is not None else collected)
        n_numeric = sum(1 for f in feature_names if dtypes.get(f, "") in NUMERIC_DTYPES)
        n_categorical = n_features - n_numeric

        candidates = recommend_models(
            task_type=task_type,
            n_rows=n_rows,
            n_features=n_features,
            n_numeric_features=n_numeric,
            n_categorical_features=n_categorical,
        )

        # Filter to a specific model type if requested
        if self._model_type is not None:
            candidates = [c for c in candidates if c.name == self._model_type]
            if not candidates:
                avail = recommend_models(task_type, n_rows, n_features, n_numeric, n_categorical)
                return AgentResult(
                    success=False,
                    error=(
                        f"Model type '{self._model_type}' not found. "
                        f"Available: {[c.name for c in avail]}"
                    ),
                )

        if not candidates:
            return AgentResult(
                success=False,
                error="No candidate models recommended for this dataset/task.",
            )

        # ── Train models with resource-bounded HPO ───────────────────
        try:
            train_result = train_models(
                df=collected,
                engine=self._engine,
                candidates=candidates,
                target_column=target_column,
                task_type=task_type,
                max_trials=self._max_trials,
                max_time_seconds=self._max_time_seconds,
                cv=self._cv,
            )
        except Exception as exc:
            msg = f"Model training failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        # ── Build output ─────────────────────────────────────────────
        candidate_dicts = [candidate_to_dict(c) for c in candidates]
        cost = estimate_training_cost(n_rows, n_features, candidates)

        best_pipeline = {
            "model_type": train_result["best_model"].__class__.__name__,
            "params": train_result["best_params"],
            "score": train_result["best_score"],
            "trials_used": train_result["trials_used"],
            "time_elapsed": train_result["time_elapsed"],
            "truncated": train_result["truncated"],
            "estimated_training_cost": cost,
        }

        logger.info(
            "Model selection complete: best=%s, score=%.4f, truncated=%s",
            best_pipeline["model_type"],
            best_pipeline["score"],
            best_pipeline["truncated"],
        )

        return AgentResult(
            success=True,
            data={
                "candidate_models": candidate_dicts,
                "best_pipeline": best_pipeline,
                "trained_model": train_result["best_model"],
            },
            metadata={
                "n_candidates": len(candidates),
                "trials_used": train_result["trials_used"],
                "truncated": train_result["truncated"],
                "feature_names": feature_names,
            },
        )

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="select_and_train",
                description=(
                    "Recommend candidate models and train the best via resource-bounded HPO."
                ),
                parameters={
                    "max_trials": {
                        "type": "integer",
                        "description": (f"Max HPO trials (default: {DEFAULT_MAX_TRIALS})."),
                    },
                    "max_time_seconds": {
                        "type": "integer",
                        "description": (
                            f"Max HPO time in seconds (default: {DEFAULT_MAX_TIME_SECONDS})."
                        ),
                    },
                },
            ),
        ]

    async def _run_unsupervised(
        self,
        state: Any,
        collected: Any,
        feature_names: list[str],
        task_type: str,
        n_rows: int,
        n_features: int,
    ) -> AgentResult:
        """Handle unsupervised tasks (clustering, anomaly detection).

        Reads unsupervised parameters from state and delegates to the
        appropriate ML module.
        """
        if task_type == "clustering":
            return self._run_clustering(state, collected, feature_names, n_rows, n_features)
        if task_type == "anomaly_detection":
            return self._run_anomaly(state, collected, feature_names, n_rows, n_features)
        return AgentResult(
            success=False,
            error=f"Unknown unsupervised task type: {task_type}",
        )

    def _run_clustering(
        self,
        state: Any,
        collected: Any,
        feature_names: list[str],
        n_rows: int,
        n_features: int,
    ) -> AgentResult:
        """Run clustering analysis with parameters from state."""
        from phronesisml.ml.clustering.algorithms import run_clustering

        n_clusters = getattr(state, "clustering_n_clusters", None)
        algorithms = getattr(state, "clustering_algorithms", None)

        kwargs: dict[str, Any] = {}
        if n_clusters is not None:
            kwargs["max_k"] = n_clusters + 1
        if algorithms is not None:
            kwargs["algorithms"] = algorithms

        try:
            result = run_clustering(
                df=collected,
                feature_names=feature_names,
                **kwargs,
            )
        except Exception as exc:
            msg = f"Clustering failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        metrics = {
            "algorithm": result.algorithm,
            "n_clusters": result.n_clusters,
            "silhouette_score": result.silhouette_score,
            "davies_bouldin_score": result.davies_bouldin_score,
            "calinski_harabasz_score": result.calinski_harabasz_score,
            "params": result.params,
        }

        logger.info(
            "Clustering complete: algorithm=%s, n_clusters=%d, silhouette=%.4f",
            result.algorithm,
            result.n_clusters,
            result.silhouette_score or 0.0,
        )

        return AgentResult(
            success=True,
            data={
                "cluster_labels": result.labels,
                "cluster_metrics": metrics,
            },
            metadata={
                "algorithm": result.algorithm,
                "n_clusters": result.n_clusters,
                "n_algorithms_tried": len(result.all_results),
            },
        )

    def _run_anomaly(
        self,
        state: Any,
        collected: Any,
        feature_names: list[str],
        n_rows: int,
        n_features: int,
    ) -> AgentResult:
        """Run anomaly detection with parameters from state."""
        from phronesisml.ml.anomaly.detector import detect_anomalies

        contamination = getattr(state, "anomaly_contamination", None) or 0.1
        algorithms = getattr(state, "anomaly_algorithms", None)

        try:
            result = detect_anomalies(
                df=collected,
                feature_names=feature_names,
                contamination=contamination,
                algorithms=algorithms,
            )
        except Exception as exc:
            msg = f"Anomaly detection failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        metrics = {
            "algorithm": result.algorithm,
            "n_anomalies": result.n_anomalies,
            "contamination": result.contamination,
            "params": result.params,
        }

        logger.info(
            "Anomaly detection complete: algorithm=%s, n_anomalies=%d",
            result.algorithm,
            result.n_anomalies,
        )

        return AgentResult(
            success=True,
            data={
                "anomaly_labels": result.labels,
                "anomaly_scores": result.anomaly_scores,
                "anomaly_metrics": metrics,
            },
            metadata={
                "algorithm": result.algorithm,
                "n_anomalies": result.n_anomalies,
                "n_algorithms_tried": len(result.all_results),
            },
        )
