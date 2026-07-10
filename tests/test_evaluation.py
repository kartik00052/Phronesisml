"""Unit tests for the Evaluation agent and its underlying metrics.

Key tests mandated by the directive:
- Evaluation correctly selects classification vs. regression metrics
  based on Target Detection's recorded problem type.
- Ambiguous/low-confidence problem type from Pass 4 propagates into
  Evaluation's output rather than being silently dropped.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression, LogisticRegression

from aetherml.agents.base import BaseAgent
from aetherml.agents.evaluation.agent import EvaluationAgent
from aetherml.engines.pandas_engine import PandasEngine
from aetherml.ml.evaluation.metrics import evaluate_model

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def classification_dataset() -> tuple[pd.DataFrame, Any]:
    """Return a trained classification model and its test data."""
    rng = np.random.RandomState(42)
    n = 100
    df = pd.DataFrame(
        {
            "f1": rng.randn(n),
            "f2": rng.randn(n),
            "label": rng.choice(["A", "B"], size=n),
        }
    )
    features = df[["f1", "f2"]].values
    target = df["label"].values
    model = LogisticRegression(random_state=42, max_iter=200)
    model.fit(features, target)
    return df, model


@pytest.fixture
def regression_dataset() -> tuple[pd.DataFrame, Any]:
    """Return a trained regression model and its test data."""
    rng = np.random.RandomState(42)
    n = 100
    df = pd.DataFrame(
        {
            "f1": rng.randn(n),
            "f2": rng.randn(n),
            "target": rng.randn(n) * 10 + 50,
        }
    )
    features = df[["f1", "f2"]].values
    target = df["target"].values
    model = LinearRegression()
    model.fit(features, target)
    return df, model


# ── Protocol tests ────────────────────────────────────────────────────


class TestEvaluationAgentProtocol:
    """Verify the EvaluationAgent satisfies the BaseAgent protocol."""

    def test_isinstance_base_agent(self, pandas_engine: PandasEngine) -> None:
        agent = EvaluationAgent(engine=pandas_engine)
        assert isinstance(agent, BaseAgent)

    def test_has_required_attributes(self, pandas_engine: PandasEngine) -> None:
        agent = EvaluationAgent(engine=pandas_engine)
        assert agent.name == "evaluation"
        assert isinstance(agent.description, str)

    def test_has_run_method(self, pandas_engine: PandasEngine) -> None:
        agent = EvaluationAgent(engine=pandas_engine)
        assert callable(getattr(agent, "run", None))

    def test_has_get_tools_method(self, pandas_engine: PandasEngine) -> None:
        agent = EvaluationAgent(engine=pandas_engine)
        tools = agent.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "evaluate_model"


# ── Agent run tests ───────────────────────────────────────────────────


class TestEvaluationAgentRun:
    """Test EvaluationAgent.run() with various state inputs."""

    @pytest.mark.asyncio
    async def test_classification_metrics(
        self,
        pandas_engine: PandasEngine,
        classification_dataset: tuple[pd.DataFrame, Any],
    ) -> None:
        """Should compute classification metrics for classification task."""
        df, model = classification_dataset
        agent = EvaluationAgent(engine=pandas_engine)
        state = _make_state(
            trained_model=model,
            features=df,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="classification",
        )
        result = await agent.run(state)

        assert result.success is True
        report = result.data["evaluation_report"]
        assert report["task_type"] == "classification"
        metrics = report["metrics"]
        assert "accuracy" in metrics
        assert "precision_macro" in metrics
        assert "recall_macro" in metrics
        assert "f1_macro" in metrics
        assert "confusion_matrix" in metrics
        assert 0 <= metrics["accuracy"] <= 1

    @pytest.mark.asyncio
    async def test_regression_metrics(
        self,
        pandas_engine: PandasEngine,
        regression_dataset: tuple[pd.DataFrame, Any],
    ) -> None:
        """Should compute regression metrics for regression task."""
        df, model = regression_dataset
        agent = EvaluationAgent(engine=pandas_engine)
        state = _make_state(
            trained_model=model,
            features=df,
            feature_names=["f1", "f2"],
            target_column="target",
            task_type="regression",
        )
        result = await agent.run(state)

        assert result.success is True
        report = result.data["evaluation_report"]
        assert report["task_type"] == "regression"
        metrics = report["metrics"]
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics
        assert metrics["rmse"] >= 0

    @pytest.mark.asyncio
    async def test_ambiguous_task_computes_both(
        self,
        pandas_engine: PandasEngine,
        classification_dataset: tuple[pd.DataFrame, Any],
    ) -> None:
        """Ambiguous task type should compute classification metrics,
        and also regression metrics when the target is numeric."""
        df, model = classification_dataset
        agent = EvaluationAgent(engine=pandas_engine)
        state = _make_state(
            trained_model=model,
            features=df,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="ambiguous",
        )
        result = await agent.run(state)

        assert result.success is True
        report = result.data["evaluation_report"]
        assert report["task_type"] == "ambiguous"
        metrics = report["metrics"]
        # Should always have classification metrics
        assert "accuracy" in metrics
        # Regression metrics are skipped for non-numeric targets
        # (which is correct behavior)

    @pytest.mark.asyncio
    async def test_ambiguity_caveat_propagated(
        self,
        pandas_engine: PandasEngine,
        classification_dataset: tuple[pd.DataFrame, Any],
    ) -> None:
        """When target detection is ambiguous, the caveat must appear in evaluation output."""
        df, model = classification_dataset
        agent = EvaluationAgent(engine=pandas_engine)
        state = _make_state(
            trained_model=model,
            features=df,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="ambiguous",
            target_detection_confidence=0.3,
            ambiguity_reason="Column 'label' is numeric with 3 unique values.",
        )
        result = await agent.run(state)

        assert result.success is True
        report = result.data["evaluation_report"]
        # The ambiguity caveat MUST be present
        assert report["ambiguity_caveat"] is not None
        assert "ambiguous" in report["ambiguity_caveat"].lower()
        assert "0.30" in report["ambiguity_caveat"]

    @pytest.mark.asyncio
    async def test_low_confidence_caveat_propagated(
        self,
        pandas_engine: PandasEngine,
        classification_dataset: tuple[pd.DataFrame, Any],
    ) -> None:
        """When confidence is low but no explicit ambiguity_reason, caveat should still appear."""
        df, model = classification_dataset
        agent = EvaluationAgent(engine=pandas_engine)
        state = _make_state(
            trained_model=model,
            features=df,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="classification",
            target_detection_confidence=0.4,
            ambiguity_reason=None,
        )
        result = await agent.run(state)

        assert result.success is True
        report = result.data["evaluation_report"]
        assert report["ambiguity_caveat"] is not None
        assert "0.40" in report["ambiguity_caveat"]

    @pytest.mark.asyncio
    async def test_no_caveat_when_confident(
        self,
        pandas_engine: PandasEngine,
        classification_dataset: tuple[pd.DataFrame, Any],
    ) -> None:
        """When confidence is high, no ambiguity caveat should appear."""
        df, model = classification_dataset
        agent = EvaluationAgent(engine=pandas_engine)
        state = _make_state(
            trained_model=model,
            features=df,
            feature_names=["f1", "f2"],
            target_column="label",
            task_type="classification",
            target_detection_confidence=0.9,
            ambiguity_reason=None,
        )
        result = await agent.run(state)

        assert result.success is True
        report = result.data["evaluation_report"]
        assert report["ambiguity_caveat"] is None

    @pytest.mark.asyncio
    async def test_no_trained_model(self, pandas_engine: PandasEngine) -> None:
        """Should fail gracefully when no trained_model is in state."""
        agent = EvaluationAgent(engine=pandas_engine)
        state = _make_state(trained_model=None)
        result = await agent.run(state)

        assert result.success is False
        assert "trained_model" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_data(self, pandas_engine: PandasEngine) -> None:
        """Should fail gracefully when no data is in state."""
        agent = EvaluationAgent(engine=pandas_engine)
        state = _make_state(
            trained_model=LogisticRegression(),
            features=None,
            validated_data=None,
            processed_data=None,
        )
        result = await agent.run(state)

        assert result.success is False
        assert "no features" in result.error.lower()


# ── Metrics unit tests ────────────────────────────────────────────────


class TestEvaluateModel:
    """Test the underlying evaluate_model function."""

    def test_classification_metrics(
        self,
        classification_dataset: tuple[pd.DataFrame, Any],
    ) -> None:
        """Should compute all classification metrics."""
        df, model = classification_dataset
        report = evaluate_model(
            model=model,
            df=df,
            target_column="label",
            feature_names=["f1", "f2"],
            task_type="classification",
        )
        assert report["task_type"] == "classification"
        assert "accuracy" in report["metrics"]
        assert "f1_macro" in report["metrics"]
        assert 0 <= report["metrics"]["accuracy"] <= 1

    def test_regression_metrics(
        self,
        regression_dataset: tuple[pd.DataFrame, Any],
    ) -> None:
        """Should compute all regression metrics."""
        df, model = regression_dataset
        report = evaluate_model(
            model=model,
            df=df,
            target_column="target",
            feature_names=["f1", "f2"],
            task_type="regression",
        )
        assert report["task_type"] == "regression"
        assert "rmse" in report["metrics"]
        assert "r2" in report["metrics"]

    def test_ambiguity_caveat_with_reason(self) -> None:
        """Should include ambiguity caveat when ambiguity_reason is provided."""
        rng = np.random.RandomState(42)
        df = pd.DataFrame({"f1": rng.randn(50), "label": rng.choice(["A", "B"], 50)})
        model = LogisticRegression(random_state=42)
        model.fit(df[["f1"]].values, df["label"].values)

        report = evaluate_model(
            model=model,
            df=df,
            target_column="label",
            feature_names=["f1"],
            task_type="classification",
            target_detection_confidence=0.3,
            ambiguity_reason="Column is ambiguous.",
        )
        assert report["ambiguity_caveat"] is not None
        assert "ambiguous" in report["ambiguity_caveat"].lower()

    def test_ambiguity_caveat_with_low_confidence_only(self) -> None:
        """Should include caveat when confidence is low but no explicit reason."""
        rng = np.random.RandomState(42)
        df = pd.DataFrame({"f1": rng.randn(50), "label": rng.choice(["A", "B"], 50)})
        model = LogisticRegression(random_state=42)
        model.fit(df[["f1"]].values, df["label"].values)

        report = evaluate_model(
            model=model,
            df=df,
            target_column="label",
            feature_names=["f1"],
            task_type="classification",
            target_detection_confidence=0.4,
            ambiguity_reason=None,
        )
        assert report["ambiguity_caveat"] is not None
        assert "0.40" in report["ambiguity_caveat"]

    def test_no_caveat_when_confident(self) -> None:
        """Should not include caveat when confidence is high."""
        rng = np.random.RandomState(42)
        df = pd.DataFrame({"f1": rng.randn(50), "label": rng.choice(["A", "B"], 50)})
        model = LogisticRegression(random_state=42)
        model.fit(df[["f1"]].values, df["label"].values)

        report = evaluate_model(
            model=model,
            df=df,
            target_column="label",
            feature_names=["f1"],
            task_type="classification",
            target_detection_confidence=0.9,
            ambiguity_reason=None,
        )
        assert report["ambiguity_caveat"] is None

    def test_model_info_populated(self) -> None:
        """Should populate model_info with model metadata."""
        rng = np.random.RandomState(42)
        df = pd.DataFrame({"f1": rng.randn(50), "target": rng.randn(50)})
        model = LinearRegression()
        model.fit(df[["f1"]].values, df["target"].values)

        report = evaluate_model(
            model=model,
            df=df,
            target_column="target",
            feature_names=["f1"],
            task_type="regression",
            best_params={"fit_intercept": True},
        )
        info = report["model_info"]
        assert info["model_type"] == "LinearRegression"
        assert info["best_params"] == {"fit_intercept": True}
        assert info["n_features"] == 1
        assert info["n_samples"] == 50


# ── Ambiguity propagation integration test ────────────────────────────


class TestAmbiguityPropagation:
    """Test that ambiguity signals from Target Detection propagate through
    Model Selection → Evaluation rather than being silently dropped."""

    @pytest.mark.asyncio
    async def test_ambiguity_surfaces_in_evaluation_output(
        self,
        pandas_engine: PandasEngine,
    ) -> None:
        """Full chain: ambiguous target → model selection → evaluation with caveat."""
        from aetherml.agents.model_selection.agent import ModelSelectionAgent

        # Create a small dataset with ambiguous target
        df = pd.DataFrame(
            {
                "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
                "f2": [10, 20, 30, 40, 50, 60, 70, 80],
                "grade": [1, 2, 3, 1, 2, 3, 1, 2],
            }
        )

        # Step 1: Model Selection with ambiguous task type
        ms_agent = ModelSelectionAgent(
            engine=pandas_engine, max_trials=3, max_time_seconds=30,
        )
        ms_state = _make_state(
            features=df,
            feature_names=["f1", "f2"],
            target_column="grade",
            task_type="ambiguous",
        )
        ms_result = await ms_agent.run(ms_state)
        assert ms_result.success is True

        # Step 2: Evaluation with ambiguity signals from target detection
        ev_agent = EvaluationAgent(engine=pandas_engine)
        ev_state = _make_state(
            trained_model=ms_result.data["trained_model"],
            features=df,
            feature_names=["f1", "f2"],
            target_column="grade",
            task_type="ambiguous",
            target_detection_confidence=0.3,
            ambiguity_reason="Column 'grade' is numeric with 3 unique values.",
            best_pipeline=ms_result.data["best_pipeline"],
        )
        ev_result = await ev_agent.run(ev_state)
        assert ev_result.success is True

        report = ev_result.data["evaluation_report"]
        # The ambiguity caveat MUST be present — this is the critical assertion
        assert report["ambiguity_caveat"] is not None
        assert "0.30" in report["ambiguity_caveat"]
        # Should have both metric sets for ambiguous task
        assert "accuracy" in report["metrics"]
        assert "rmse" in report["metrics"]


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
