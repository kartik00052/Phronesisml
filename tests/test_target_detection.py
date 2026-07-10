"""Unit tests for the Target Detection agent and its underlying detector."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from aetherml.agents.base import BaseAgent
from aetherml.agents.target_detection.agent import TargetDetectionAgent
from aetherml.data.profilers.stats import profile_dataset
from aetherml.engines.pandas_engine import PandasEngine
from aetherml.ml.target_detection.detector import AMBIGUITY_THRESHOLD, detect_target


class TestTargetDetectionAgentProtocol:
    """Verify the TargetDetectionAgent satisfies the BaseAgent protocol."""

    def test_isinstance_base_agent(self, pandas_engine: PandasEngine) -> None:
        agent = TargetDetectionAgent(engine=pandas_engine)
        assert isinstance(agent, BaseAgent)

    def test_has_required_attributes(self, pandas_engine: PandasEngine) -> None:
        agent = TargetDetectionAgent(engine=pandas_engine)
        assert agent.name == "target_detection"
        assert isinstance(agent.description, str)

    def test_has_run_method(self, pandas_engine: PandasEngine) -> None:
        agent = TargetDetectionAgent(engine=pandas_engine)
        assert callable(getattr(agent, "run", None))

    def test_has_get_tools_method(self, pandas_engine: PandasEngine) -> None:
        agent = TargetDetectionAgent(engine=pandas_engine)
        tools = agent.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "detect_target"


class TestTargetDetectionAgentRun:
    """Test TargetDetectionAgent.run() with various state inputs."""

    @pytest.mark.asyncio
    async def test_classification_target(
        self, pandas_engine: PandasEngine, classification_df: pd.DataFrame
    ) -> None:
        """A 'label' column with name hint + categorical should detect classification."""
        agent = TargetDetectionAgent(engine=pandas_engine)
        profile = profile_dataset(classification_df, pandas_engine)
        state = _make_state(
            processed_data=classification_df,
            data_profile=profile,
        )
        result = await agent.run(state)

        assert result.success is True
        assert result.data["target_column"] == "label"
        assert result.data["task_type"] == "classification"
        assert result.data["target_detection_confidence"] >= AMBIGUITY_THRESHOLD
        assert result.data["ambiguity_reason"] is None

    @pytest.mark.asyncio
    async def test_regression_target(
        self, pandas_engine: PandasEngine, regression_df: pd.DataFrame
    ) -> None:
        """A 'target' column with name hint + high-cardinality numeric should detect regression."""
        agent = TargetDetectionAgent(engine=pandas_engine)
        profile = profile_dataset(regression_df, pandas_engine)
        state = _make_state(
            processed_data=regression_df,
            data_profile=profile,
        )
        result = await agent.run(state)

        assert result.success is True
        assert result.data["target_column"] == "target"
        assert result.data["task_type"] == "regression"
        assert result.data["target_detection_confidence"] >= AMBIGUITY_THRESHOLD
        assert result.data["ambiguity_reason"] is None

    @pytest.mark.asyncio
    async def test_ambiguous_target(
        self, pandas_engine: PandasEngine, ambiguous_target_df: pd.DataFrame
    ) -> None:
        """A numeric column with 3 unique values should be flagged as ambiguous."""
        agent = TargetDetectionAgent(engine=pandas_engine)
        profile = profile_dataset(ambiguous_target_df, pandas_engine)
        state = _make_state(
            processed_data=ambiguous_target_df,
            data_profile=profile,
        )
        result = await agent.run(state)

        assert result.success is True
        # The 'grade' column should be detected (it has 3 unique values)
        assert result.data["target_column"] == "grade"
        assert result.data["task_type"] == "ambiguous"
        assert result.data["target_detection_confidence"] < AMBIGUITY_THRESHOLD
        assert result.data["ambiguity_reason"] is not None
        assert "3 unique values" in result.data["ambiguity_reason"]
        assert "grade" in result.data["ambiguity_reason"]

    @pytest.mark.asyncio
    async def test_no_data_profile(self, pandas_engine: PandasEngine) -> None:
        """Should fail gracefully when no data_profile is in state."""
        agent = TargetDetectionAgent(engine=pandas_engine)
        state = _make_state(processed_data=pd.DataFrame({"a": [1]}), data_profile=None)
        result = await agent.run(state)

        assert result.success is False
        assert "data_profile" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_data(self, pandas_engine: PandasEngine) -> None:
        """Should fail gracefully when no data is in state."""
        agent = TargetDetectionAgent(engine=pandas_engine)
        state = _make_state(processed_data=None, validated_data=None)
        result = await agent.run(state)

        assert result.success is False
        assert "no processed_data" in result.error.lower()


class TestDetectTarget:
    """Test the underlying detect_target function."""

    def test_name_hint_boosts_confidence(
        self, pandas_engine: PandasEngine, classification_df: pd.DataFrame
    ) -> None:
        """Columns with target-like names should get a confidence boost."""
        profile = profile_dataset(classification_df, pandas_engine)
        result = detect_target(classification_df, pandas_engine, profile)
        assert result["target_column"] == "label"
        assert "name_hint" in str(result["candidates"])

    def test_ambiguous_numeric_low_cardinality(
        self, pandas_engine: PandasEngine, ambiguous_target_df: pd.DataFrame
    ) -> None:
        """Numeric columns with 2-5 unique values should be flagged ambiguous."""
        profile = profile_dataset(ambiguous_target_df, pandas_engine)
        result = detect_target(ambiguous_target_df, pandas_engine, profile)

        # Find the grade candidate
        grade_candidate = [
            c for c in result["candidates"] if c["column"] == "grade"
        ][0]
        assert grade_candidate["task_type"] == "ambiguous"
        assert grade_candidate["ambiguity_reason"] is not None
        assert "3 unique values" in grade_candidate["ambiguity_reason"]

    def test_no_viable_target(
        self, pandas_engine: PandasEngine, features_only_df: pd.DataFrame
    ) -> None:
        """When no column stands out, confidence should be low."""
        profile = profile_dataset(features_only_df, pandas_engine)
        result = detect_target(features_only_df, pandas_engine, profile)
        # All columns are features — no strong target signal
        assert result["confidence"] < 0.5

    def test_constant_column_not_target(
        self, pandas_engine: PandasEngine,
    ) -> None:
        """A column with only one unique value should not be detected as target."""
        df = pd.DataFrame({
            "feature": [1.0, 2.0, 3.0, 4.0, 5.0],
            "constant": [5, 5, 5, 5, 5],
        })
        profile = profile_dataset(df, pandas_engine)
        result = detect_target(df, pandas_engine, profile)
        assert result["target_column"] != "constant"


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
