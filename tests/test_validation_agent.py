"""Unit tests for the Validation agent and its underlying checks."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from phronesisml.agents.base import BaseAgent
from phronesisml.agents.validation.agent import ValidationAgent
from phronesisml.data.validators.checks import validate_dataframe
from phronesisml.engines.pandas_engine import PandasEngine
from phronesisml.exceptions import DataValidationError


class TestValidationAgentProtocol:
    """Verify the ValidationAgent satisfies the BaseAgent protocol."""

    def test_isinstance_base_agent(self, pandas_engine: PandasEngine) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        assert isinstance(agent, BaseAgent)

    def test_has_required_attributes(self, pandas_engine: PandasEngine) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        assert hasattr(agent, "name")
        assert hasattr(agent, "description")
        assert agent.name == "validation"
        assert isinstance(agent.description, str)

    def test_has_run_method(self, pandas_engine: PandasEngine) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        assert callable(getattr(agent, "run", None))

    def test_has_get_tools_method(self, pandas_engine: PandasEngine) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        tools = agent.get_tools()
        assert isinstance(tools, list)


class TestValidationAgentRun:
    """Test ValidationAgent.run() with various state inputs."""

    @pytest.mark.asyncio
    async def test_normal_input(self, pandas_engine: PandasEngine, sample_df: pd.DataFrame) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        state = _make_state(processed_data=sample_df)
        result = await agent.run(state)

        assert result.success is True
        assert result.data["validated_data"] is not None
        report = result.data["validation_report"]
        assert report["passed"] is True
        assert report["shape"]["rows"] == 5
        assert report["shape"]["columns"] == 4
        assert report["duplicate_rows"] == 0

    @pytest.mark.asyncio
    async def test_empty_dataframe(
        self, pandas_engine: PandasEngine, empty_df: pd.DataFrame
    ) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        state = _make_state(processed_data=empty_df)
        result = await agent.run(state)

        assert result.success is False
        assert "zero rows" in result.error.lower()

    @pytest.mark.asyncio
    async def test_zero_columns(
        self, pandas_engine: PandasEngine, zero_columns_df: pd.DataFrame
    ) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        state = _make_state(processed_data=zero_columns_df)
        result = await agent.run(state)

        assert result.success is False
        assert "zero columns" in result.error.lower()

    @pytest.mark.asyncio
    async def test_single_row(
        self, pandas_engine: PandasEngine, single_row_df: pd.DataFrame
    ) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        state = _make_state(processed_data=single_row_df)
        result = await agent.run(state)

        assert result.success is True
        report = result.data["validation_report"]
        assert report["shape"]["rows"] == 1

    @pytest.mark.asyncio
    async def test_all_null_column(
        self, pandas_engine: PandasEngine, all_null_column_df: pd.DataFrame
    ) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        state = _make_state(processed_data=all_null_column_df)
        result = await agent.run(state)

        assert result.success is True
        report = result.data["validation_report"]
        assert "empty_col" in report["empty_columns"]
        assert "empty_col" in report["null_columns"]

    @pytest.mark.asyncio
    async def test_duplicate_rows(
        self, pandas_engine: PandasEngine, duplicate_rows_df: pd.DataFrame
    ) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        state = _make_state(processed_data=duplicate_rows_df)
        result = await agent.run(state)

        assert result.success is True
        report = result.data["validation_report"]
        assert report["duplicate_rows"] == 1

    @pytest.mark.asyncio
    async def test_no_processed_data(self, pandas_engine: PandasEngine) -> None:
        agent = ValidationAgent(engine=pandas_engine)
        state = _make_state(processed_data=None)
        result = await agent.run(state)

        assert result.success is False
        assert "no processed_data" in result.error.lower()


class TestValidateDataframe:
    """Test the underlying validate_dataframe function."""

    def test_normal_data(self, pandas_engine: PandasEngine, sample_df: pd.DataFrame) -> None:
        df, report = validate_dataframe(sample_df, pandas_engine)
        assert report["passed"] is True
        assert report["shape"]["rows"] == 5
        assert report["shape"]["columns"] == 4
        assert isinstance(report["dtypes"], dict)
        assert isinstance(report["null_counts"], dict)

    def test_empty_raises(self, pandas_engine: PandasEngine, empty_df: pd.DataFrame) -> None:
        with pytest.raises(DataValidationError, match="zero rows"):
            validate_dataframe(empty_df, pandas_engine)

    def test_zero_columns_raises(
        self, pandas_engine: PandasEngine, zero_columns_df: pd.DataFrame
    ) -> None:
        with pytest.raises(DataValidationError, match="zero columns"):
            validate_dataframe(zero_columns_df, pandas_engine)


def _make_state(**kwargs: Any) -> Any:
    """Create a minimal state-like object for testing.

    Uses a simple namespace to simulate WorkflowState without requiring
    the full Pydantic model (which may not have all fields set).
    """
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
