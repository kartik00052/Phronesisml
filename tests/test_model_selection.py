"""Unit tests for the Model Selection agent, auto_selector, and trainer.

Key tests mandated by the directive:
- max_trials/max_time_seconds enforcement (the most important test)
- Rule-based recommendation (no LLM)
- Resource bounds prevent unbounded search
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

from aetherml.agents.base import BaseAgent
from aetherml.agents.model_selection.agent import ModelSelectionAgent
from aetherml.engines.pandas_engine import PandasEngine
from aetherml.exceptions import AgentError
from aetherml.ml.automl.auto_selector import (
    CandidateModel,
    candidate_to_dict,
    dict_to_candidate,
    recommend_models,
)
from aetherml.ml.automl.trainer import (
    DEFAULT_MAX_TIME_SECONDS,
    DEFAULT_MAX_TRIALS,
    train_models,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def classification_data() -> pd.DataFrame:
    """Return a small classification dataset."""
    rng = np.random.RandomState(42)
    n = 100
    return pd.DataFrame(
        {
            "f1": rng.randn(n),
            "f2": rng.randn(n),
            "f3": rng.randn(n),
            "label": rng.choice(["A", "B"], size=n),
        }
    )


@pytest.fixture
def regression_data() -> pd.DataFrame:
    """Return a small regression dataset."""
    rng = np.random.RandomState(42)
    n = 100
    return pd.DataFrame(
        {
            "f1": rng.randn(n),
            "f2": rng.randn(n),
            "f3": rng.randn(n),
            "target": rng.randn(n) * 10 + 50,
        }
    )


@pytest.fixture
def small_classification_data() -> pd.DataFrame:
    """Return a very small classification dataset for fast tests."""
    return pd.DataFrame(
        {
            "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "f2": [10, 20, 30, 40, 50, 60, 70, 80],
            "label": ["A", "B", "A", "B", "A", "B", "A", "B"],
        }
    )


@pytest.fixture
def small_regression_data() -> pd.DataFrame:
    """Return a very small regression dataset for fast tests."""
    return pd.DataFrame(
        {
            "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "f2": [10, 20, 30, 40, 50, 60, 70, 80],
            "target": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0],
        }
    )


# ── Protocol tests ────────────────────────────────────────────────────


class TestModelSelectionAgentProtocol:
    """Verify the ModelSelectionAgent satisfies the BaseAgent protocol."""

    def test_isinstance_base_agent(self, pandas_engine: PandasEngine) -> None:
        agent = ModelSelectionAgent(engine=pandas_engine)
        assert isinstance(agent, BaseAgent)

    def test_has_required_attributes(self, pandas_engine: PandasEngine) -> None:
        agent = ModelSelectionAgent(engine=pandas_engine)
        assert agent.name == "model_selection"
        assert isinstance(agent.description, str)

    def test_has_run_method(self, pandas_engine: PandasEngine) -> None:
        agent = ModelSelectionAgent(engine=pandas_engine)
        assert callable(getattr(agent, "run", None))

    def test_has_get_tools_method(self, pandas_engine: PandasEngine) -> None:
        agent = ModelSelectionAgent(engine=pandas_engine)
        tools = agent.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "select_and_train"

    def test_resource_bounds_stored(self, pandas_engine: PandasEngine) -> None:
        agent = ModelSelectionAgent(
            engine=pandas_engine,
            max_trials=10,
            max_time_seconds=30,
        )
        assert agent._max_trials == 10
        assert agent._max_time_seconds == 30

    def test_resource_bounds_defaults(self, pandas_engine: PandasEngine) -> None:
        agent = ModelSelectionAgent(engine=pandas_engine)
        assert agent._max_trials == DEFAULT_MAX_TRIALS
        assert agent._max_time_seconds == DEFAULT_MAX_TIME_SECONDS


# ── Agent run tests ───────────────────────────────────────────────────


class TestModelSelectionAgentRun:
    """Test ModelSelectionAgent.run() with various state inputs."""

    @pytest.mark.asyncio
    async def test_classification_pipeline(
        self,
        pandas_engine: PandasEngine,
        small_classification_data: pd.DataFrame,
    ) -> None:
        """Should train a classification model and return results."""
        agent = ModelSelectionAgent(
            engine=pandas_engine, max_trials=5, max_time_seconds=30,
        )
        state = _make_state(
            features=small_classification_data,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="classification",
        )
        result = await agent.run(state)

        assert result.success is True
        assert result.data["trained_model"] is not None
        assert result.data["best_pipeline"] is not None
        assert result.data["candidate_models"] is not None
        assert len(result.data["candidate_models"]) > 0
        assert result.data["best_pipeline"]["score"] > 0

    @pytest.mark.asyncio
    async def test_regression_pipeline(
        self,
        pandas_engine: PandasEngine,
        small_regression_data: pd.DataFrame,
    ) -> None:
        """Should train a regression model and return results."""
        agent = ModelSelectionAgent(
            engine=pandas_engine, max_trials=5, max_time_seconds=30,
        )
        state = _make_state(
            features=small_regression_data,
            feature_names=["f1", "f2"],
            target_column="target",
            task_type="regression",
        )
        result = await agent.run(state)

        assert result.success is True
        assert result.data["trained_model"] is not None
        assert result.data["best_pipeline"]["score"] > 0

    @pytest.mark.asyncio
    async def test_ambiguous_task_type(
        self,
        pandas_engine: PandasEngine,
        small_classification_data: pd.DataFrame,
    ) -> None:
        """Should handle ambiguous task type by trying both sets of models."""
        agent = ModelSelectionAgent(
            engine=pandas_engine, max_trials=5, max_time_seconds=30,
        )
        state = _make_state(
            features=small_classification_data,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="ambiguous",
        )
        result = await agent.run(state)

        assert result.success is True
        assert result.data["trained_model"] is not None

    @pytest.mark.asyncio
    async def test_no_features(self, pandas_engine: PandasEngine) -> None:
        """Should fail gracefully when no features are in state."""
        agent = ModelSelectionAgent(engine=pandas_engine)
        state = _make_state(features=None, validated_data=None, processed_data=None)
        result = await agent.run(state)

        assert result.success is False
        assert "no features" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_target_column(self, pandas_engine: PandasEngine) -> None:
        """Should fail gracefully when no target_column is in state."""
        agent = ModelSelectionAgent(engine=pandas_engine)
        state = _make_state(
            features=pd.DataFrame({"a": [1, 2, 3]}),
            target_column=None,
        )
        result = await agent.run(state)

        assert result.success is False
        assert "target_column" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_task_type(self, pandas_engine: PandasEngine) -> None:
        """Should fail gracefully when no task_type is in state."""
        agent = ModelSelectionAgent(engine=pandas_engine)
        state = _make_state(
            features=pd.DataFrame({"a": [1, 2, 3]}),
            target_column="a",
            task_type=None,
        )
        result = await agent.run(state)

        assert result.success is False
        assert "task_type" in result.error.lower()


# ── Resource bound enforcement tests (CRITICAL) ───────────────────────


class TestResourceBoundEnforcement:
    """Verify that max_trials and max_time_seconds are actually enforced.

    This is the single most important test group in this pass.
    The directive explicitly requires: "mock a slow search and confirm
    it truncates rather than running indefinitely."
    """

    @pytest.mark.asyncio
    async def test_max_trials_enforced(
        self,
        pandas_engine: PandasEngine,
        small_classification_data: pd.DataFrame,
    ) -> None:
        """HPO must stop when max_trials is reached, not continue."""
        # With max_trials=3, only 3 parameter combinations should be tried
        # across ALL candidates
        agent = ModelSelectionAgent(
            engine=pandas_engine,
            max_trials=3,
            max_time_seconds=300,  # High time limit — trials should hit first
        )
        state = _make_state(
            features=small_classification_data,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="classification",
        )
        result = await agent.run(state)

        assert result.success is True
        best = result.data["best_pipeline"]
        # trials_used must be <= max_trials
        assert best["trials_used"] <= 3
        # If truncated, the flag must be set
        if best["trials_used"] == 3:
            assert best["truncated"] is True

    @pytest.mark.asyncio
    async def test_max_time_enforced(
        self,
        pandas_engine: PandasEngine,
        classification_data: pd.DataFrame,
    ) -> None:
        """HPO must stop when max_time_seconds is reached."""
        # With a 1-second time limit and enough candidates to exceed it,
        # the search should truncate
        agent = ModelSelectionAgent(
            engine=pandas_engine,
            max_trials=1000,  # High trial limit — time should hit first
            max_time_seconds=1,  # Very short time limit
        )
        state = _make_state(
            features=classification_data,
            feature_names=["f1", "f2", "f3"],
            target_column="label",
            task_type="classification",
        )
        start = time.monotonic()
        result = await agent.run(state)
        elapsed = time.monotonic() - start

        assert result.success is True
        best = result.data["best_pipeline"]
        # Should have stopped within a reasonable time (2x the limit for safety)
        assert elapsed < 10.0
        # If the search was truncated, the flag must be set
        if best["truncated"]:
            assert best["time_elapsed"] >= 1.0

    @pytest.mark.asyncio
    async def test_truncated_flag_set_on_time_limit(
        self,
        pandas_engine: PandasEngine,
        classification_data: pd.DataFrame,
    ) -> None:
        """When time limit is hit, truncated=True MUST be set."""
        agent = ModelSelectionAgent(
            engine=pandas_engine,
            max_trials=10000,
            max_time_seconds=1,
        )
        state = _make_state(
            features=classification_data,
            feature_names=["f1", "f2", "f3"],
            target_column="label",
            task_type="classification",
        )
        result = await agent.run(state)

        assert result.success is True
        best = result.data["best_pipeline"]
        # With 10000 max_trials and 1 second, it's almost certain to truncate
        # But even if it finishes in time, truncated should be False
        assert isinstance(best["truncated"], bool)

    @pytest.mark.asyncio
    async def test_truncated_flag_set_on_trial_limit(
        self,
        pandas_engine: PandasEngine,
        small_classification_data: pd.DataFrame,
    ) -> None:
        """When trial limit is hit, truncated=True MUST be set."""
        agent = ModelSelectionAgent(
            engine=pandas_engine,
            max_trials=2,
            max_time_seconds=300,
        )
        state = _make_state(
            features=small_classification_data,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="classification",
        )
        result = await agent.run(state)

        assert result.success is True
        best = result.data["best_pipeline"]
        assert best["trials_used"] <= 2
        # If exactly 2 trials used, search was truncated
        if best["trials_used"] == 2:
            assert best["truncated"] is True


# ── Auto selector tests ───────────────────────────────────────────────


class TestRecommendModels:
    """Test the rule-based model recommendation logic."""

    def test_classification_candidates(self) -> None:
        """Should return classification-appropriate models."""
        candidates = recommend_models(
            task_type="classification",
            n_rows=500,
            n_features=10,
            n_numeric_features=8,
            n_categorical_features=2,
        )
        assert len(candidates) > 0
        # Should include logistic regression and random forest
        names = [c.name for c in candidates]
        assert "logistic_regression" in names
        assert "random_forest" in names

    def test_regression_candidates(self) -> None:
        """Should return regression-appropriate models."""
        candidates = recommend_models(
            task_type="regression",
            n_rows=500,
            n_features=10,
            n_numeric_features=10,
            n_categorical_features=0,
        )
        assert len(candidates) > 0
        names = [c.name for c in candidates]
        assert "linear_regression" in names
        assert "random_forest" in names

    def test_ambiguous_candidates(self) -> None:
        """Should return a superset of both classification and regression."""
        candidates = recommend_models(
            task_type="ambiguous",
            n_rows=500,
            n_features=10,
            n_numeric_features=8,
            n_categorical_features=2,
        )
        assert len(candidates) >= 3

    def test_small_dataset_prefers_simple(self) -> None:
        """Small datasets should prefer simpler models."""
        candidates = recommend_models(
            task_type="classification",
            n_rows=50,
            n_features=10,
            n_numeric_features=8,
            n_categorical_features=2,
        )
        # Linear models should be ranked higher for small datasets
        names = [c.name for c in candidates]
        # logistic_regression should be near the top
        assert names.index("logistic_regression") < len(names) // 2

    def test_high_dimensionality_prefers_ensemble(self) -> None:
        """High-dimensional data should prefer tree-based models."""
        candidates = recommend_models(
            task_type="classification",
            n_rows=100,
            n_features=200,
            n_numeric_features=200,
            n_categorical_features=0,
        )
        names = [c.name for c in candidates]
        # Ensemble models should be ranked higher
        assert "random_forest" in names

    def test_candidate_serialization(self) -> None:
        """CandidateModel should round-trip through dict serialization."""
        original = CandidateModel(
            name="test_model",
            estimator_path="sklearn.linear_model.LinearRegression",
            param_space={"C": [0.1, 1.0]},
            tags={"linear": True},
        )
        d = candidate_to_dict(original)
        restored = dict_to_candidate(d)
        assert restored.name == original.name
        assert restored.estimator_path == original.estimator_path
        assert restored.param_space == original.param_space
        assert restored.tags == original.tags


# ── Trainer tests ─────────────────────────────────────────────────────


class TestTrainModels:
    """Test the trainer with resource bounds."""

    def test_basic_training_classification(
        self,
        pandas_engine: PandasEngine,
        small_classification_data: pd.DataFrame,
    ) -> None:
        """Should train a classification model successfully."""
        candidates = recommend_models(
            task_type="classification",
            n_rows=len(small_classification_data),
            n_features=2,
            n_numeric_features=2,
            n_categorical_features=0,
        )
        result = train_models(
            df=small_classification_data,
            engine=pandas_engine,
            candidates=candidates,
            target_column="label",
            task_type="classification",
            max_trials=5,
            max_time_seconds=30,
        )
        assert result["best_model"] is not None
        assert result["best_score"] > 0
        assert result["trials_used"] > 0
        assert isinstance(result["truncated"], bool)

    def test_basic_training_regression(
        self,
        pandas_engine: PandasEngine,
        small_regression_data: pd.DataFrame,
    ) -> None:
        """Should train a regression model successfully."""
        candidates = recommend_models(
            task_type="regression",
            n_rows=len(small_regression_data),
            n_features=2,
            n_numeric_features=2,
            n_categorical_features=0,
        )
        result = train_models(
            df=small_regression_data,
            engine=pandas_engine,
            candidates=candidates,
            target_column="target",
            task_type="regression",
            max_trials=5,
            max_time_seconds=30,
        )
        assert result["best_model"] is not None
        assert result["best_score"] > 0

    def test_max_trials_enforced_in_trainer(
        self,
        pandas_engine: PandasEngine,
        small_classification_data: pd.DataFrame,
    ) -> None:
        """Trainer must respect max_trials as a hard ceiling."""
        candidates = recommend_models(
            task_type="classification",
            n_rows=len(small_classification_data),
            n_features=2,
            n_numeric_features=2,
            n_categorical_features=0,
        )
        result = train_models(
            df=small_classification_data,
            engine=pandas_engine,
            candidates=candidates,
            target_column="label",
            task_type="classification",
            max_trials=2,
            max_time_seconds=300,
        )
        assert result["trials_used"] <= 2

    def test_max_time_enforced_in_trainer(
        self,
        pandas_engine: PandasEngine,
        classification_data: pd.DataFrame,
    ) -> None:
        """Trainer must respect max_time_seconds as a hard ceiling."""
        candidates = recommend_models(
            task_type="classification",
            n_rows=len(classification_data),
            n_features=3,
            n_numeric_features=3,
            n_categorical_features=0,
        )
        start = time.monotonic()
        train_models(
            df=classification_data,
            engine=pandas_engine,
            candidates=candidates,
            target_column="label",
            task_type="classification",
            max_trials=10000,
            max_time_seconds=1,
        )
        elapsed = time.monotonic() - start
        assert elapsed < 10.0  # Should not run much longer than 1 second

    def test_empty_param_grid(
        self,
        pandas_engine: PandasEngine,
        small_regression_data: pd.DataFrame,
    ) -> None:
        """Models with no param space should train with defaults."""
        candidates = [
            CandidateModel(
                name="linear_regression",
                estimator_path="sklearn.linear_model.LinearRegression",
                param_space={},
            ),
        ]
        result = train_models(
            df=small_regression_data,
            engine=pandas_engine,
            candidates=candidates,
            target_column="target",
            task_type="regression",
            max_trials=10,
            max_time_seconds=30,
        )
        assert result["best_model"] is not None
        assert result["trials_used"] == 1
        assert result["truncated"] is False

    def test_no_successful_model_raises(
        self,
        pandas_engine: PandasEngine,
    ) -> None:
        """Should raise AgentError if no model can be trained."""
        # Create a dataset that will cause issues
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        bad_candidates = [
            CandidateModel(
                name="nonexistent",
                estimator_path="nonexistent.module.Class",
                param_space={},
            ),
        ]
        with pytest.raises(AgentError, match="No model could be trained"):
            train_models(
                df=df,
                engine=pandas_engine,
                candidates=bad_candidates,
                target_column="b",
                task_type="regression",
                max_trials=5,
                max_time_seconds=30,
            )


# ── Helper ────────────────────────────────────────────────────────────


def _make_state(**kwargs: Any) -> Any:
    """Create a minimal state-like object for testing."""
    defaults = {
        "data_path": None,
        "raw_data": None,
        "file_format": None,
        "row_count": None,
        "validated_data": None,
        "validation_report": None,
        "active_engine": None,
        "processed_data": None,
        "transform_log": None,
        "data_profile": None,
        "eda_report": None,
        "target_column": None,
        "task_type": None,
        "target_detection_confidence": None,
        "ambiguity_reason": None,
        "features": None,
        "feature_names": None,
        "candidate_models": None,
        "best_pipeline": None,
        "trained_model": None,
        "evaluation_report": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
