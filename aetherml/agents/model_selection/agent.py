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

from aetherml.agents.base import AgentResult, Tool
from aetherml.engines.base_engine import BaseEngine
from aetherml.ml.automl.auto_selector import (
    candidate_to_dict,
    estimate_training_cost,
    recommend_models,
)
from aetherml.ml.automl.trainer import (
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
        target_column = getattr(state, "target_column", None)
        if target_column is None:
            return AgentResult(
                success=False,
                error="No target_column in workflow state. Run target detection first.",
            )

        task_type = getattr(state, "task_type", None)
        if task_type is None:
            return AgentResult(
                success=False,
                error="No task_type in workflow state. Run target detection first.",
            )

        feature_names = getattr(state, "feature_names", None)

        # Feature Engineering drops the target column from state.features.
        # To train, we need both features AND target in one DataFrame.
        # Reconstruct by joining engineered features with the target
        # from upstream validated/processed data.
        upstream = (
            state.validated_data if state.validated_data is not None else state.processed_data
        )
        if upstream is None:
            return AgentResult(
                success=False,
                error="No validated_data or processed_data in workflow state.",
            )

        if state.features is not None:
            features_df = self._engine.collect(state.features)
            upstream_df = self._engine.collect(upstream)
            if target_column in upstream_df.columns:
                collected = features_df.copy()
                collected[target_column] = upstream_df[target_column].values
            else:
                collected = features_df
        else:
            collected = self._engine.collect(upstream)

        if feature_names is None:
            # Fallback: all columns except target
            feature_names = [c for c in collected.columns if c != target_column]

        # ── Recommend models ─────────────────────────────────────────
        n_rows = len(collected)
        n_features = len(feature_names)
        dtypes = self._engine.dtypes(state.features if state.features is not None else upstream)
        n_numeric = sum(1 for f in feature_names if dtypes.get(f, "") in _NUMERIC_DTYPES)
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


_NUMERIC_DTYPES = frozenset(
    {
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint24",
        "uint32",
        "uint64",
        "float16",
        "float32",
        "float64",
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "Float32",
        "Float64",
    }
)
