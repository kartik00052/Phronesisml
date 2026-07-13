"""Unit tests for the EDA agent and its underlying profiler."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from phronesisml.agents.base import BaseAgent
from phronesisml.agents.eda.agent import EDAAgent
from phronesisml.data.profilers.stats import profile_dataset
from phronesisml.engines.pandas_engine import PandasEngine


class TestEDAAgentProtocol:
    """Verify the EDAAgent satisfies the BaseAgent protocol."""

    def test_isinstance_base_agent(self, pandas_engine: PandasEngine) -> None:
        agent = EDAAgent(engine=pandas_engine)
        assert isinstance(agent, BaseAgent)

    def test_has_required_attributes(self, pandas_engine: PandasEngine) -> None:
        agent = EDAAgent(engine=pandas_engine)
        assert hasattr(agent, "name")
        assert hasattr(agent, "description")
        assert agent.name == "eda"
        assert isinstance(agent.description, str)

    def test_has_run_method(self, pandas_engine: PandasEngine) -> None:
        agent = EDAAgent(engine=pandas_engine)
        assert callable(getattr(agent, "run", None))

    def test_has_get_tools_method(self, pandas_engine: PandasEngine) -> None:
        agent = EDAAgent(engine=pandas_engine)
        tools = agent.get_tools()
        assert isinstance(tools, list)


class TestEDAAgentRun:
    """Test EDAAgent.run() with various state inputs."""

    @pytest.mark.asyncio
    async def test_normal_input(self, pandas_engine: PandasEngine, sample_df: pd.DataFrame) -> None:
        agent = EDAAgent(engine=pandas_engine)
        state = _make_state(validated_data=sample_df)
        result = await agent.run(state)

        assert result.success is True
        profile = result.data["data_profile"]
        assert profile["shape"]["rows"] == 5
        assert profile["shape"]["columns"] == 4
        assert "age" in profile["numeric_columns"]
        assert "salary" in profile["numeric_columns"]
        assert "name" in profile["categorical_columns"]
        assert "department" in profile["categorical_columns"]

    @pytest.mark.asyncio
    async def test_falls_back_to_processed_data(
        self, pandas_engine: PandasEngine, sample_df: pd.DataFrame
    ) -> None:
        """EDA agent should use processed_data when validated_data is None."""
        agent = EDAAgent(engine=pandas_engine)
        state = _make_state(validated_data=None, processed_data=sample_df)
        result = await agent.run(state)

        assert result.success is True
        assert result.data["data_profile"]["shape"]["rows"] == 5

    @pytest.mark.asyncio
    async def test_empty_dataframe(
        self, pandas_engine: PandasEngine, empty_df: pd.DataFrame
    ) -> None:
        agent = EDAAgent(engine=pandas_engine)
        state = _make_state(validated_data=empty_df)
        result = await agent.run(state)

        # Empty DataFrame should still be profiled (no rows, but columns exist)
        assert result.success is True
        assert result.data["data_profile"]["shape"]["rows"] == 0

    @pytest.mark.asyncio
    async def test_single_row(
        self, pandas_engine: PandasEngine, single_row_df: pd.DataFrame
    ) -> None:
        agent = EDAAgent(engine=pandas_engine)
        state = _make_state(validated_data=single_row_df)
        result = await agent.run(state)

        assert result.success is True
        profile = result.data["data_profile"]
        assert profile["shape"]["rows"] == 1

    @pytest.mark.asyncio
    async def test_all_null_column(
        self, pandas_engine: PandasEngine, all_null_column_df: pd.DataFrame
    ) -> None:
        agent = EDAAgent(engine=pandas_engine)
        state = _make_state(validated_data=all_null_column_df)
        result = await agent.run(state)

        assert result.success is True
        profile = result.data["data_profile"]
        assert "empty_col" in profile["categorical_columns"]

    @pytest.mark.asyncio
    async def test_no_data(self, pandas_engine: PandasEngine) -> None:
        agent = EDAAgent(engine=pandas_engine)
        state = _make_state(validated_data=None, processed_data=None)
        result = await agent.run(state)

        assert result.success is False
        assert "no validated_data" in result.error.lower()


class TestProfileDataset:
    """Test the underlying profile_dataset function."""

    def test_numeric_stats(self, pandas_engine: PandasEngine, sample_df: pd.DataFrame) -> None:
        profile = profile_dataset(sample_df, pandas_engine)
        age_stats = profile["numeric_summary"]["age"]
        assert "mean" in age_stats
        assert "std" in age_stats
        assert "min" in age_stats
        assert "max" in age_stats
        assert "50%" in age_stats  # median

    def test_categorical_stats(self, pandas_engine: PandasEngine, sample_df: pd.DataFrame) -> None:
        profile = profile_dataset(sample_df, pandas_engine)
        dept_stats = profile["categorical_summary"]["department"]
        assert "cardinality" in dept_stats
        assert dept_stats["cardinality"] == 2  # Engineering, Marketing
        assert "top_values" in dept_stats

    def test_shape_and_memory(self, pandas_engine: PandasEngine, sample_df: pd.DataFrame) -> None:
        profile = profile_dataset(sample_df, pandas_engine)
        assert profile["shape"] == {"rows": 5, "columns": 4}
        assert profile["memory_bytes"] > 0


def _make_state(**kwargs: Any) -> Any:
    """Create a minimal state-like object for testing."""
    from types import SimpleNamespace

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
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
