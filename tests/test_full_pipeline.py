"""Tests for the full 11-stage pipeline graph construction and composition root.

These tests verify that the workflow graph can be built with all
11 stages wired correctly, and that _compose_agents produces a
complete agent dict without dead agents.
"""

from __future__ import annotations

from typing import Any

import pytest

from phronesisml.exceptions import ConfigurationError
from phronesisml.workflow.graph import PIPELINE_ORDER, build_graph


def _make_stub(name: str) -> Any:
    from phronesisml.agents.base import AgentResult, _StubAgent

    stub = _StubAgent(name=name, description=f"Stub for {name}")

    class _Agent:
        name = stub.name
        description = stub.description

        async def run(self, state: Any) -> AgentResult:
            return await stub.run(state)

        def get_tools(self) -> list:
            return stub.get_tools()

    return _Agent()


class TestPipelineOrder:
    def test_pipeline_order_has_11_stages(self) -> None:
        assert len(PIPELINE_ORDER) == 11

    def test_pipeline_order_starts_with_upload(self) -> None:
        assert PIPELINE_ORDER[0] == "upload"

    def test_pipeline_order_ends_with_storage(self) -> None:
        assert PIPELINE_ORDER[-1] == "storage"

    def test_no_engine_selection_in_order(self) -> None:
        assert "engine_selection" not in PIPELINE_ORDER

    def test_no_rag_in_order(self) -> None:
        assert "rag" not in PIPELINE_ORDER


class TestFullPipelineGraph:
    def test_all_11_stages_build(self) -> None:
        agents = {name: _make_stub(name) for name in PIPELINE_ORDER}
        graph = build_graph(agents)
        assert graph is not None

    def test_subset_stages_build(self) -> None:
        agents = {name: _make_stub(name) for name in PIPELINE_ORDER}
        graph = build_graph(agents, stages=["upload", "etl", "validation"])
        assert graph is not None

    def test_single_stage_builds(self) -> None:
        agents = {"upload": _make_stub("upload")}
        graph = build_graph(agents, stages=["upload"])
        assert graph is not None

    def test_unknown_stage_in_full_list_raises(self) -> None:
        agents = {name: _make_stub(name) for name in PIPELINE_ORDER}
        agents["engine_selection"] = _make_stub("engine_selection")
        with pytest.raises(ConfigurationError, match="Unknown stage"):
            build_graph(agents, stages=PIPELINE_ORDER + ["engine_selection"])

    def test_missing_agent_for_stage_raises(self) -> None:
        agents = {name: _make_stub(name) for name in PIPELINE_ORDER if name != "eda"}
        with pytest.raises(ConfigurationError, match="Agent for stage"):
            build_graph(agents, stages=PIPELINE_ORDER)


class TestComposeAgents:
    def test_compose_returns_all_pipeline_agents(self) -> None:
        from phronesisml import _compose_agents
        from phronesisml.configs.settings import PhronesisConfig

        config = PhronesisConfig()
        agents = _compose_agents(config, data_path="/tmp/fake.csv")

        # All 11 pipeline stages must be present
        for stage in PIPELINE_ORDER:
            assert stage in agents, f"Missing agent for stage: {stage}"

        # Dead agents must NOT be present
        assert "engine_selection" not in agents
        assert "rag" not in agents

    def test_compose_agent_names_match_stages(self) -> None:
        from phronesisml import _compose_agents
        from phronesisml.configs.settings import PhronesisConfig

        config = PhronesisConfig()
        agents = _compose_agents(config, data_path="/tmp/fake.csv")

        for stage in PIPELINE_ORDER:
            assert agents[stage].name == stage
