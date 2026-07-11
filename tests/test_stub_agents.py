"""Unit tests for stub agents: engine_selection, storage, rag."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aetherml.agents.base import BaseAgent
from aetherml.agents.engine_selection.agent import EngineSelectionAgent
from aetherml.agents.rag.agent import RAGAgent
from aetherml.agents.storage.agent import StorageAgent
from aetherml.exceptions import AgentNotImplementedError


class TestEngineSelectionAgent:
    @pytest.mark.asyncio
    async def test_run_raises_not_implemented(self) -> None:
        agent = EngineSelectionAgent()
        with pytest.raises(AgentNotImplementedError):
            await agent.run(SimpleNamespace())

    def test_get_tools_returns_empty(self) -> None:
        agent = EngineSelectionAgent()
        assert agent.get_tools() == []

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
    @pytest.mark.asyncio
    async def test_run_raises_not_implemented(self) -> None:
        agent = StorageAgent()
        with pytest.raises(AgentNotImplementedError):
            await agent.run(SimpleNamespace())

    def test_get_tools_returns_empty(self) -> None:
        agent = StorageAgent()
        assert agent.get_tools() == []

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
    @pytest.mark.asyncio
    async def test_run_raises_not_implemented(self) -> None:
        agent = RAGAgent()
        with pytest.raises(AgentNotImplementedError):
            await agent.run(SimpleNamespace())

    def test_get_tools_returns_empty(self) -> None:
        agent = RAGAgent()
        assert agent.get_tools() == []

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
