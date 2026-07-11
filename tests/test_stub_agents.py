"""Unit tests for previously-stub agents: engine_selection, storage, rag.

These agents were originally stubs (raising AgentNotImplementedError) and
have been implemented.  Tests verify their actual behavior.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from aetherml.agents.base import BaseAgent
from aetherml.agents.engine_selection.agent import EngineSelectionAgent
from aetherml.agents.rag.agent import RAGAgent
from aetherml.agents.storage.agent import StorageAgent


class TestEngineSelectionAgent:
    """Tests for the implemented EngineSelectionAgent."""

    @pytest.mark.asyncio
    async def test_run_returns_engine_name(self) -> None:
        agent = EngineSelectionAgent()
        state = SimpleNamespace(data_path=None, raw_data=None)
        result = await agent.run(state)
        assert result.success is True
        assert "active_engine" in result.data
        assert result.data["active_engine"] in ("pandas", "polars", "spark")

    @pytest.mark.asyncio
    async def test_run_records_metadata(self) -> None:
        agent = EngineSelectionAgent()
        state = SimpleNamespace(data_path="/some/path.csv", raw_data=None)
        result = await agent.run(state)
        assert result.success is True
        assert result.metadata["data_path"] == "/some/path.csv"

    def test_get_tools_returns_one_tool(self) -> None:
        agent = EngineSelectionAgent()
        tools = agent.get_tools()
        assert len(tools) == 1
        assert tools[0].name == "select_engine"

    def test_name(self) -> None:
        agent = EngineSelectionAgent()
        assert agent.name == "engine_selection"

    def test_description(self) -> None:
        agent = EngineSelectionAgent()
        assert isinstance(agent.description, str)
        assert len(agent.description) > 0

    def test_isinstance_base_agent(self) -> None:
        agent = EngineSelectionAgent()
        assert isinstance(agent, BaseAgent)


class TestStorageAgent:
    """Tests for the implemented StorageAgent."""

    @pytest.mark.asyncio
    async def test_run_persists_metadata(self, tmp_path: Any) -> None:
        agent = StorageAgent(base_dir=tmp_path)
        state = SimpleNamespace(
            run_id="test_run_001",
            evaluation_report={"metrics": {"rmse": 0.5}},
            final_report="# Report",
            target_column="target",
            task_type="regression",
            best_pipeline=None,
        )
        result = await agent.run(state)
        assert result.success is True
        assert "artifact_uri" in result.data
        assert len(result.metadata["saved_files"]) >= 2

    @pytest.mark.asyncio
    async def test_run_handles_no_data(self, tmp_path: Any) -> None:
        agent = StorageAgent(base_dir=tmp_path)
        state = SimpleNamespace(
            run_id="test_run_002",
            evaluation_report=None,
            final_report=None,
            target_column=None,
            task_type=None,
            best_pipeline=None,
        )
        result = await agent.run(state)
        assert result.success is True

    def test_get_tools_returns_one_tool(self) -> None:
        agent = StorageAgent()
        tools = agent.get_tools()
        assert len(tools) == 1
        assert tools[0].name == "save_artifacts"

    def test_name(self) -> None:
        agent = StorageAgent()
        assert agent.name == "storage"

    def test_description(self) -> None:
        agent = StorageAgent()
        assert isinstance(agent.description, str)
        assert len(agent.description) > 0

    def test_isinstance_base_agent(self) -> None:
        agent = StorageAgent()
        assert isinstance(agent, BaseAgent)


class TestRAGAgent:
    """Tests for the implemented RAGAgent."""

    @pytest.mark.asyncio
    async def test_run_degrades_gracefully(self) -> None:
        """RAG agent should return success even when Qdrant is unreachable."""
        agent = RAGAgent()
        state = SimpleNamespace(
            target_column="target",
            task_type="regression",
            best_pipeline=None,
            evaluation_report=None,
        )
        result = await agent.run(state)
        # Degrades gracefully — Qdrant not available, but no crash
        assert result.success is True
        assert result.data["rag_context"]["status"] != "success"

    def test_get_tools_returns_one_tool(self) -> None:
        agent = RAGAgent()
        tools = agent.get_tools()
        assert len(tools) == 1
        assert tools[0].name == "retrieve_knowledge"

    def test_name(self) -> None:
        agent = RAGAgent()
        assert agent.name == "rag"

    def test_description(self) -> None:
        agent = RAGAgent()
        assert isinstance(agent.description, str)
        assert len(agent.description) > 0

    def test_isinstance_base_agent(self) -> None:
        agent = RAGAgent()
        assert isinstance(agent, BaseAgent)
