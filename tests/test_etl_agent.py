"""Unit tests for the ETL agent."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from phronesisml.agents.base import BaseAgent
from phronesisml.agents.etl.agent import ETLAgent, ETLConfig


class TestETLConfigDefaults:
    def test_default_null_strategy(self) -> None:
        cfg = ETLConfig()
        assert cfg.null_strategy == "drop"

    def test_default_fill_value(self) -> None:
        cfg = ETLConfig()
        assert cfg.fill_value is None

    def test_default_type_map(self) -> None:
        cfg = ETLConfig()
        assert cfg.type_map is None

    def test_default_encode_columns(self) -> None:
        cfg = ETLConfig()
        assert cfg.encode_columns is None

    def test_custom_values(self) -> None:
        cfg = ETLConfig(
            null_strategy="fill",
            fill_value=0,
            type_map={"age": "int64"},
            encode_columns=["color"],
        )
        assert cfg.null_strategy == "fill"
        assert cfg.fill_value == 0
        assert cfg.type_map == {"age": "int64"}
        assert cfg.encode_columns == ["color"]


class TestETLAgentInit:
    def test_default_config(self) -> None:
        agent = ETLAgent()
        assert agent._config.null_strategy == "drop"
        assert agent._config.fill_value is None

    def test_none_config_uses_defaults(self) -> None:
        agent = ETLAgent(config=None)
        assert agent._config.null_strategy == "drop"

    def test_custom_config(self) -> None:
        cfg = ETLConfig(null_strategy="flag")
        agent = ETLAgent(config=cfg)
        assert agent._config.null_strategy == "flag"

    def test_name_and_description(self) -> None:
        agent = ETLAgent()
        assert agent.name == "etl"
        assert isinstance(agent.description, str)


class TestETLAgentGetTools:
    def test_returns_one_tool(self) -> None:
        agent = ETLAgent()
        tools = agent.get_tools()
        assert len(tools) == 1

    def test_tool_name(self) -> None:
        agent = ETLAgent()
        tools = agent.get_tools()
        assert tools[0].name == "clean_data"


class TestETLAgentRun:
    @pytest.mark.asyncio
    async def test_raw_data_none_returns_failure(self) -> None:
        agent = ETLAgent()
        state = SimpleNamespace(raw_data=None)
        result = await agent.run(state)
        assert result.success is False
        assert "no raw_data" in result.error.lower()

    @pytest.mark.asyncio
    async def test_raw_data_not_dataframe_returns_failure(self) -> None:
        agent = ETLAgent()
        state = SimpleNamespace(raw_data="not a dataframe")
        result = await agent.run(state)
        assert result.success is False
        assert "expected pandas dataframe" in result.error.lower()

    @pytest.mark.asyncio
    async def test_success_with_null_handling(self) -> None:
        agent = ETLAgent(config=ETLConfig(null_strategy="drop"))
        df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", "z"]})
        state = SimpleNamespace(raw_data=df)
        result = await agent.run(state)
        assert result.success is True
        assert result.data["processed_data"] is not None
        assert len(result.data["processed_data"]) == 2
        assert len(result.data["transform_log"]) >= 1

    @pytest.mark.asyncio
    async def test_success_with_type_casting(self) -> None:
        cfg = ETLConfig(type_map={"a": "float64"})
        agent = ETLAgent(config=cfg)
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        state = SimpleNamespace(raw_data=df)
        result = await agent.run(state)
        assert result.success is True
        assert result.data["processed_data"]["a"].dtype == "float64"

    @pytest.mark.asyncio
    async def test_success_with_encoding(self) -> None:
        agent = ETLAgent()
        df = pd.DataFrame({"a": [1, 2, 3], "color": ["red", "blue", "red"]})
        state = SimpleNamespace(raw_data=df)
        result = await agent.run(state)
        assert result.success is True
        processed = result.data["processed_data"]
        assert processed["color"].dtype != "object"

    @pytest.mark.asyncio
    async def test_isinstance_base_agent(self) -> None:
        agent = ETLAgent()
        assert isinstance(agent, BaseAgent)

    @pytest.mark.asyncio
    async def test_has_metadata(self) -> None:
        agent = ETLAgent()
        df = pd.DataFrame({"a": [1, 2]})
        state = SimpleNamespace(raw_data=df)
        result = await agent.run(state)
        assert result.success is True
        assert "columns" in result.metadata
