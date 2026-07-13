"""Unit tests for previously-stub agents: storage.

This agent was originally a stub (raising AgentNotImplementedError) and
has been implemented.  Tests verify its actual behavior.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from phronesisml.agents.base import BaseAgent
from phronesisml.agents.storage.agent import StorageAgent


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
