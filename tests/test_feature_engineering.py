"""Unit tests for the Feature Engineering agent and its underlying engineer."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from aetherml.agents.base import BaseAgent
from aetherml.agents.feature_engineering.agent import FeatureEngineeringAgent
from aetherml.engines.pandas_engine import PandasEngine
from aetherml.ml.feature_engineering.engineer import engineer_features


class TestFeatureEngineeringAgentProtocol:
    """Verify the FeatureEngineeringAgent satisfies the BaseAgent protocol."""

    def test_isinstance_base_agent(self, pandas_engine: PandasEngine) -> None:
        agent = FeatureEngineeringAgent(engine=pandas_engine)
        assert isinstance(agent, BaseAgent)

    def test_has_required_attributes(self, pandas_engine: PandasEngine) -> None:
        agent = FeatureEngineeringAgent(engine=pandas_engine)
        assert agent.name == "feature_engineering"
        assert isinstance(agent.description, str)

    def test_has_run_method(self, pandas_engine: PandasEngine) -> None:
        agent = FeatureEngineeringAgent(engine=pandas_engine)
        assert callable(getattr(agent, "run", None))

    def test_has_get_tools_method(self, pandas_engine: PandasEngine) -> None:
        agent = FeatureEngineeringAgent(engine=pandas_engine)
        tools = agent.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "engineer_features"


class TestFeatureEngineeringAgentRun:
    """Test FeatureEngineeringAgent.run() with various state inputs."""

    @pytest.mark.asyncio
    async def test_normal_input_with_target(
        self, pandas_engine: PandasEngine, classification_df: pd.DataFrame
    ) -> None:
        """Feature engineering should exclude the target column from transforms."""
        agent = FeatureEngineeringAgent(engine=pandas_engine)
        state = _make_state(
            validated_data=classification_df,
            target_column="label",
        )
        result = await agent.run(state)

        assert result.success is True
        feature_names = result.data["feature_names"]

        # Target should be excluded from features
        assert "label" not in feature_names
        assert "feature_a" in feature_names
        assert "feature_b" in feature_names

    @pytest.mark.asyncio
    async def test_target_column_not_encoded(
        self, pandas_engine: PandasEngine, classification_df: pd.DataFrame
    ) -> None:
        """The target column should not be label-encoded by feature engineering."""
        agent = FeatureEngineeringAgent(engine=pandas_engine)
        state = _make_state(
            validated_data=classification_df,
            target_column="label",
        )
        result = await agent.run(state)

        features = result.data["features"]
        # The original 'label' column should not be in features
        assert "label" not in features.columns

    @pytest.mark.asyncio
    async def test_no_target_column(
        self, pandas_engine: PandasEngine, features_only_df: pd.DataFrame
    ) -> None:
        """When no target is detected, all columns should be treated as features."""
        agent = FeatureEngineeringAgent(engine=pandas_engine)
        state = _make_state(
            validated_data=features_only_df,
            target_column=None,
        )
        result = await agent.run(state)

        assert result.success is True
        feature_names = result.data["feature_names"]
        assert "feature_a" in feature_names
        assert "feature_b" in feature_names
        assert "feature_c" in feature_names

    @pytest.mark.asyncio
    async def test_no_data(self, pandas_engine: PandasEngine) -> None:
        """Should fail gracefully when no data is in state."""
        agent = FeatureEngineeringAgent(engine=pandas_engine)
        state = _make_state(validated_data=None, processed_data=None)
        result = await agent.run(state)

        assert result.success is False
        assert "no validated_data" in result.error.lower()


class TestEngineerFeatures:
    """Test the underlying engineer_features function."""

    def test_nulls_filled(
        self, pandas_engine: PandasEngine, all_null_column_df: pd.DataFrame
    ) -> None:
        """Remaining nulls should be filled with the fill_value."""
        # Add some nulls to a numeric column
        df = all_null_column_df.copy()
        df.loc[0, "age"] = None

        result_df, log = engineer_features(
            df, pandas_engine, null_strategy="fill", fill_value=0
        )
        assert result_df.loc[0, "age"] == 0

    def test_outlier_flagged(
        self, pandas_engine: PandasEngine,
    ) -> None:
        """Outliers should be flagged, not dropped by default."""
        df = pd.DataFrame({
            "feature_a": [1.0, 2.0, 3.0, 4.0, 100.0],  # 100.0 is an outlier
            "target": [0, 1, 0, 1, 0],
        })
        result_df, log = engineer_features(
            df, pandas_engine, target_column="target",
            detect_outliers=True, drop_outlier_rows=False,
        )
        assert "outlier_flag" in result_df.columns
        assert result_df["outlier_flag"].sum() > 0

    def test_outlier_dropped(
        self, pandas_engine: PandasEngine,
    ) -> None:
        """When configured, outlier rows should be dropped."""
        df = pd.DataFrame({
            "feature_a": [1.0, 2.0, 3.0, 4.0, 100.0],
            "target": [0, 1, 0, 1, 0],
        })
        result_df, log = engineer_features(
            df, pandas_engine, target_column="target",
            detect_outliers=True, drop_outlier_rows=True,
        )
        assert len(result_df) < 5

    def test_scaling(
        self, pandas_engine: PandasEngine,
    ) -> None:
        """Numeric features should be min-max scaled to [0, 1]."""
        df = pd.DataFrame({
            "feature_a": [10.0, 20.0, 30.0, 40.0, 50.0],
            "target": [0, 1, 0, 1, 0],
        })
        result_df, log = engineer_features(
            df, pandas_engine, target_column="target", scale_numeric=True
        )
        assert result_df["feature_a"].min() == 0.0
        assert result_df["feature_a"].max() == 1.0

    def test_target_excluded_from_scaling(
        self, pandas_engine: PandasEngine,
    ) -> None:
        """The target column should not be scaled."""
        df = pd.DataFrame({
            "feature_a": [10.0, 20.0, 30.0, 40.0, 50.0],
            "target": [100.0, 200.0, 300.0, 400.0, 500.0],
        })
        result_df, log = engineer_features(
            df, pandas_engine, target_column="target", scale_numeric=True
        )
        # Target should retain original values
        assert result_df["target"].min() == 100.0
        assert result_df["target"].max() == 500.0

    def test_categorical_encoded(
        self, pandas_engine: PandasEngine, classification_df: pd.DataFrame
    ) -> None:
        """Categorical features should be label-encoded."""
        result_df, log = engineer_features(
            classification_df, pandas_engine, target_column="label"
        )
        # 'label' is excluded, but if there were other categoricals they'd be encoded
        assert result_df["feature_a"].dtype != "object"

    def test_feature_selection_removes_low_variance(
        self, pandas_engine: PandasEngine,
    ) -> None:
        """Features with near-zero variance should be dropped."""
        df = pd.DataFrame({
            "good_feature": [1.0, 2.0, 3.0, 4.0, 5.0],
            "constant_feature": [5.0, 5.0, 5.0, 5.0, 5.0],
            "target": [0, 1, 0, 1, 0],
        })
        result_df, log = engineer_features(
            df, pandas_engine, target_column="target", select_features=True
        )
        assert "constant_feature" not in result_df.columns
        assert "good_feature" in result_df.columns


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
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
