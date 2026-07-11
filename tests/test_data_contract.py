"""Tests for the Feature Engineering → Model Selection data contract fix.

CRITICAL BUG: Feature Engineering drops the target column from
state.features.  Model Selection and Evaluation must reconstruct
the full DataFrame by joining engineered features with the target
from upstream validated/processed data.
"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from aetherml.agents.evaluation.agent import EvaluationAgent
from aetherml.agents.model_selection.agent import ModelSelectionAgent
from aetherml.engines.pandas_engine import PandasEngine


@pytest.fixture
def engine() -> PandasEngine:
    return PandasEngine()


@pytest.fixture
def features_without_target() -> pd.DataFrame:
    """Simulates state.features after Feature Engineering drops the target."""
    return pd.DataFrame(
        {
            "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "f2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
        }
    )


@pytest.fixture
def upstream_data_with_target() -> pd.DataFrame:
    """Simulates state.validated_data with the target column still present."""
    return pd.DataFrame(
        {
            "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "f2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
            "label": ["A", "B", "A", "B", "A", "B", "A", "B"],
        }
    )


class TestModelSelectionDataContract:
    """Model Selection must reconstruct the full DataFrame with target."""

    @pytest.mark.asyncio
    async def test_reconstructs_target_from_upstream(
        self,
        engine: PandasEngine,
        features_without_target: pd.DataFrame,
        upstream_data_with_target: pd.DataFrame,
    ) -> None:
        """When features has no target, agent joins target from validated_data."""
        agent = ModelSelectionAgent(engine=engine, max_trials=3, max_time_seconds=30)
        state = SimpleNamespace(
            features=features_without_target,
            feature_names=["f1", "f2"],
            validated_data=upstream_data_with_target,
            processed_data=None,
            target_column="label",
            task_type="classification",
        )
        result = await agent.run(state)

        assert result.success is True
        assert result.data["trained_model"] is not None

    @pytest.mark.asyncio
    async def test_reconstructs_target_from_processed_data(
        self,
        engine: PandasEngine,
        features_without_target: pd.DataFrame,
        upstream_data_with_target: pd.DataFrame,
    ) -> None:
        """When validated_data is None, agent falls back to processed_data."""
        agent = ModelSelectionAgent(engine=engine, max_trials=3, max_time_seconds=30)
        state = SimpleNamespace(
            features=features_without_target,
            feature_names=["f1", "f2"],
            validated_data=None,
            processed_data=upstream_data_with_target,
            target_column="label",
            task_type="classification",
        )
        result = await agent.run(state)

        assert result.success is True
        assert result.data["trained_model"] is not None

    @pytest.mark.asyncio
    async def test_no_upstream_data_fails(
        self,
        engine: PandasEngine,
        features_without_target: pd.DataFrame,
    ) -> None:
        """Fails gracefully when neither validated_data nor processed_data exists."""
        agent = ModelSelectionAgent(engine=engine, max_trials=3, max_time_seconds=30)
        state = SimpleNamespace(
            features=features_without_target,
            feature_names=["f1", "f2"],
            validated_data=None,
            processed_data=None,
            target_column="label",
            task_type="classification",
        )
        result = await agent.run(state)

        assert result.success is False
        assert "validated_data" in result.error.lower()


class TestEvaluationDataContract:
    """Evaluation must reconstruct the full DataFrame with target."""

    @pytest.mark.asyncio
    async def test_reconstructs_target_from_upstream(
        self,
        engine: PandasEngine,
        features_without_target: pd.DataFrame,
        upstream_data_with_target: pd.DataFrame,
    ) -> None:
        """When features has no target, agent joins target from validated_data."""
        from sklearn.ensemble import RandomForestClassifier

        model = RandomForestClassifier(n_estimators=2, random_state=42)
        X = features_without_target.values
        y = upstream_data_with_target["label"].values
        model.fit(X, y)

        agent = EvaluationAgent(engine=engine)
        state = SimpleNamespace(
            trained_model=model,
            features=features_without_target,
            feature_names=["f1", "f2"],
            validated_data=upstream_data_with_target,
            processed_data=None,
            target_column="label",
            task_type="classification",
            best_pipeline={"params": {}},
            target_detection_confidence=0.9,
            ambiguity_reason=None,
        )
        result = await agent.run(state)

        assert result.success is True
        assert "evaluation_report" in result.data
        metrics = result.data["evaluation_report"]["metrics"]
        assert "accuracy" in metrics
        assert 0.0 <= metrics["accuracy"] <= 1.0

    @pytest.mark.asyncio
    async def test_no_trained_model_fails(self, engine: PandasEngine) -> None:
        """Fails gracefully when no trained_model in state."""
        agent = EvaluationAgent(engine=engine)
        state = SimpleNamespace(trained_model=None)
        result = await agent.run(state)

        assert result.success is False
        assert "trained_model" in result.error.lower()


class TestFeatureSelectionMinFeatures:
    """Feature selection must respect min_features floor."""

    def test_min_features_prevents_dropping_all(self) -> None:
        """When all features would be dropped, min_features keeps at least one."""
        from aetherml.ml.feature_engineering.engineer import _select_features

        df = pd.DataFrame(
            {
                "f1": [1.0] * 10,
                "f2": [1.0] * 10,
                "f3": [1.0] * 10,
                "target": list(range(10)),
            }
        )
        result, log = _select_features(
            df,
            feature_cols=["f1", "f2", "f3"],
            target_column="target",
            min_features=1,
        )
        # At least 1 feature should remain
        assert len(result.columns) >= 2  # target + at least 1 feature

    def test_min_features_higher_floor(self) -> None:
        """min_features=2 should keep at least 2 features."""
        from aetherml.ml.feature_engineering.engineer import _select_features

        df = pd.DataFrame(
            {
                "f1": [1.0] * 10,
                "f2": [1.0] * 10,
                "f3": [1.0] * 10,
                "target": list(range(10)),
            }
        )
        result, log = _select_features(
            df,
            feature_cols=["f1", "f2", "f3"],
            target_column="target",
            min_features=2,
        )
        # target + at least 2 features
        assert len(result.columns) >= 3

    def test_predictive_feature_survives_selection(self) -> None:
        """A feature genuinely correlated with the target must survive selection."""
        import numpy as np

        from aetherml.ml.feature_engineering.engineer import _select_features

        rng = np.random.RandomState(42)
        n = 100
        predictive = np.linspace(0, 10, n)  # strong signal
        noise = rng.randn(n)  # no signal
        target = predictive * 2 + 1  # target is a function of predictive

        df = pd.DataFrame(
            {
                "predictive": predictive,
                "noise": noise,
                "target": target,
            }
        )
        result, log = _select_features(
            df,
            feature_cols=["predictive", "noise"],
            target_column="target",
            min_features=1,
        )
        # predictive feature MUST survive — it's perfectly correlated
        assert "predictive" in result.columns

    def test_configurable_thresholds_applied(self) -> None:
        """Custom thresholds from AetherMLConfig must be respected."""
        from aetherml.engines.pandas_engine import PandasEngine
        from aetherml.ml.feature_engineering.engineer import engineer_features

        engine = PandasEngine()
        rng = __import__("numpy").random.RandomState(42)
        n = 50
        df = pd.DataFrame(
            {
                "f1": rng.randn(n),
                "f2": rng.randn(n),
                "f3": rng.randn(n),
                "target": rng.randn(n),
            }
        )

        # With very lenient thresholds (keep everything), all features should survive
        result, _ = engineer_features(
            df,
            engine,
            target_column="target",
            variance_threshold=0.0,
            correlation_threshold=0.0,
        )
        # All 3 features should be present (no features dropped)
        assert "f1" in result.columns
        assert "f2" in result.columns
        assert "f3" in result.columns

    def test_strict_thresholds_drop_features(self) -> None:
        """Very strict thresholds should drop features with no signal."""
        from aetherml.ml.feature_engineering.engineer import _select_features

        df = pd.DataFrame(
            {
                "f1": [1.0] * 10,  # zero variance
                "f2": [1.0] * 10,  # zero variance
                "target": list(range(10)),
            }
        )
        # With default thresholds, both features should be flagged for dropping
        # (zero variance < 0.01)
        result, log = _select_features(
            df,
            feature_cols=["f1", "f2"],
            target_column="target",
            min_features=1,
        )
        # min_features=1 ensures at least 1 feature survives
        assert "target" in result.columns
        assert len([c for c in result.columns if c != "target"]) >= 1
