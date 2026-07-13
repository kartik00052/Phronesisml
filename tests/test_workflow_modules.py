"""Unit tests for workflow state, router, nodes, and graph modules."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from phronesisml.agents.base import AgentResult
from phronesisml.exceptions import AgentError, AgentNotImplementedError, ConfigurationError
from phronesisml.workflow.router import (
    route_after_eda,
    route_after_etl,
    route_after_evaluation,
    route_after_explainability,
    route_after_feature_engineering,
    route_after_model_selection,
    route_after_reporting,
    route_after_target_detection,
    route_after_upload,
    route_after_validation,
)
from phronesisml.workflow.state import WorkflowState

# ── State ────────────────────────────────────────────────────────────────


class TestWorkflowState:
    def test_default_all_none(self) -> None:
        state = WorkflowState()
        assert state.run_id is None
        assert state.status is None
        assert state.data_path is None
        assert state.raw_data is None
        assert state.file_format is None
        assert state.row_count is None
        assert state.validated_data is None
        assert state.validation_report is None
        assert state.processed_data is None
        assert state.transform_log is None
        assert state.data_profile is None
        assert state.eda_report is None
        assert state.features is None
        assert state.feature_names is None
        assert state.target_column is None
        assert state.task_type is None
        assert state.target_detection_confidence is None
        assert state.ambiguity_reason is None
        assert state.candidate_models is None
        assert state.best_pipeline is None
        assert state.trained_model is None
        assert state.evaluation_report is None
        assert state.explanation_report is None
        assert state.final_report is None
        assert state.artifact_uri is None

    def test_extra_allow_unknown_fields(self) -> None:
        state = WorkflowState(custom_field="hello", another=42)
        assert state.custom_field == "hello"  # type: ignore[attr-defined]
        assert state.another == 42  # type: ignore[attr-defined]

    def test_arbitrary_types_allowed_dataframe(self) -> None:
        df = pd.DataFrame({"a": [1, 2]})
        state = WorkflowState(raw_data=df)
        assert isinstance(state.raw_data, pd.DataFrame)
        assert len(state.raw_data) == 2

    def test_partial_construction(self) -> None:
        state = WorkflowState(data_path="/tmp/data.csv", row_count=100)
        assert state.data_path == "/tmp/data.csv"
        assert state.row_count == 100
        assert state.raw_data is None


# ── Router ───────────────────────────────────────────────────────────────


class TestRouter:
    def test_route_after_upload_proceed(self) -> None:
        state = SimpleNamespace(raw_data=pd.DataFrame())
        assert route_after_upload(state) == "proceed"

    def test_route_after_upload_end(self) -> None:
        state = SimpleNamespace(raw_data=None)
        assert route_after_upload(state) == "__end__"

    def test_route_after_etl_proceed(self) -> None:
        state = SimpleNamespace(processed_data=pd.DataFrame())
        assert route_after_etl(state) == "proceed"

    def test_route_after_etl_end(self) -> None:
        state = SimpleNamespace(processed_data=None)
        assert route_after_etl(state) == "__end__"

    def test_route_after_validation_proceed(self) -> None:
        state = SimpleNamespace(validated_data=pd.DataFrame())
        assert route_after_validation(state) == "proceed"

    def test_route_after_validation_end(self) -> None:
        state = SimpleNamespace(validated_data=None)
        assert route_after_validation(state) == "__end__"

    def test_route_after_eda_proceed(self) -> None:
        state = SimpleNamespace(data_profile={"cols": 5})
        assert route_after_eda(state) == "proceed"

    def test_route_after_eda_end(self) -> None:
        state = SimpleNamespace(data_profile=None)
        assert route_after_eda(state) == "__end__"

    def test_route_after_target_detection_proceed(self) -> None:
        state = SimpleNamespace(target_column="label")
        assert route_after_target_detection(state) == "proceed"

    def test_route_after_target_detection_end(self) -> None:
        state = SimpleNamespace(target_column=None)
        assert route_after_target_detection(state) == "__end__"

    def test_route_after_feature_engineering_proceed(self) -> None:
        state = SimpleNamespace(features=pd.DataFrame())
        assert route_after_feature_engineering(state) == "proceed"

    def test_route_after_feature_engineering_end(self) -> None:
        state = SimpleNamespace(features=None)
        assert route_after_feature_engineering(state) == "__end__"

    def test_route_after_model_selection_proceed(self) -> None:
        state = SimpleNamespace(trained_model="model")
        assert route_after_model_selection(state) == "proceed"

    def test_route_after_model_selection_end(self) -> None:
        state = SimpleNamespace(trained_model=None)
        assert route_after_model_selection(state) == "__end__"

    def test_route_after_evaluation_proceed(self) -> None:
        state = SimpleNamespace(evaluation_report={"acc": 0.9})
        assert route_after_evaluation(state) == "proceed"

    def test_route_after_evaluation_end(self) -> None:
        state = SimpleNamespace(evaluation_report=None)
        assert route_after_evaluation(state) == "__end__"

    def test_route_after_explainability_proceed(self) -> None:
        state = SimpleNamespace(explanation_report={"shap": True})
        assert route_after_explainability(state) == "proceed"

    def test_route_after_explainability_end(self) -> None:
        state = SimpleNamespace(explanation_report=None)
        assert route_after_explainability(state) == "__end__"

    def test_route_after_reporting_proceed_with_report(self) -> None:
        state = SimpleNamespace(final_report="report")
        assert route_after_reporting(state) == "proceed"

    def test_route_after_reporting_end_even_without_report(self) -> None:
        state = SimpleNamespace(final_report=None)
        assert route_after_reporting(state) == "__end__"

    def test_missing_attribute_routes_to_end(self) -> None:
        state = SimpleNamespace()  # no raw_data
        assert route_after_upload(state) == "__end__"


# ── Nodes ────────────────────────────────────────────────────────────────


class TestMakeNode:
    @pytest.mark.asyncio
    async def test_success_path(self) -> None:
        from phronesisml.workflow.nodes import make_node

        mock_agent = AsyncMock()
        mock_agent.name = "test_agent"
        mock_agent.run.return_value = AgentResult(success=True, data={"key": "value"})
        node_fn = make_node(mock_agent)
        result = await node_fn(SimpleNamespace())
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_failure_path_raises_agent_error(self) -> None:
        from phronesisml.workflow.nodes import make_node

        mock_agent = AsyncMock()
        mock_agent.name = "failing_agent"
        mock_agent.run.return_value = AgentResult(success=False, error="something broke")
        node_fn = make_node(mock_agent)
        with pytest.raises(AgentError, match="failing_agent.*something broke"):
            await node_fn(SimpleNamespace())

    @pytest.mark.asyncio
    async def test_not_implemented_returns_empty(self) -> None:
        from phronesisml.workflow.nodes import make_node

        mock_agent = AsyncMock()
        mock_agent.name = "stub_agent"
        mock_agent.run.side_effect = AgentNotImplementedError("not done")
        node_fn = make_node(mock_agent)
        result = await node_fn(SimpleNamespace())
        assert result == {}

    @pytest.mark.asyncio
    async def test_generic_exception_wrapped_in_agent_error(self) -> None:
        from phronesisml.workflow.nodes import make_node

        mock_agent = AsyncMock()
        mock_agent.name = "crash_agent"
        mock_agent.run.side_effect = RuntimeError("boom")
        node_fn = make_node(mock_agent)
        with pytest.raises(AgentError, match="crash_agent.*boom"):
            await node_fn(SimpleNamespace())

    @pytest.mark.asyncio
    async def test_return_value_has_correct_name(self) -> None:
        from phronesisml.workflow.nodes import make_node

        mock_agent = AsyncMock()
        mock_agent.name = "my_agent"
        mock_agent.run.return_value = AgentResult(success=True, data={})
        node_fn = make_node(mock_agent)
        assert node_fn.__name__ == "node_my_agent"

    @pytest.mark.asyncio
    async def test_agent_error_preserves_metadata(self) -> None:
        from phronesisml.workflow.nodes import make_node

        mock_agent = AsyncMock()
        mock_agent.name = "meta_agent"
        mock_agent.run.return_value = AgentResult(
            success=False,
            error="fail",
            error_type="ValueError",
            error_message="bad value",
            error_context={"col": "x"},
        )
        node_fn = make_node(mock_agent)
        with pytest.raises(AgentError) as exc_info:
            await node_fn(SimpleNamespace())
        assert exc_info.value.error_type == "ValueError"
        assert exc_info.value.error_message == "bad value"
        assert exc_info.value.error_context == {"col": "x"}


# ── Graph ────────────────────────────────────────────────────────────────


class TestBuildGraph:
    def test_stages_none_defaults_to_upload_etl(self) -> None:
        from phronesisml.workflow.graph import build_graph

        agents = {
            "upload": _make_stub_agent("upload"),
            "etl": _make_stub_agent("etl"),
        }
        graph = build_graph(agents, stages=None)
        assert graph is not None

    def test_unknown_stage_raises(self) -> None:
        from phronesisml.workflow.graph import build_graph

        agents = {"upload": _make_stub_agent("upload")}
        with pytest.raises(ConfigurationError, match="Unknown stage"):
            build_graph(agents, stages=["upload", "nonexistent"])

    def test_missing_agent_raises(self) -> None:
        from phronesisml.workflow.graph import build_graph

        agents = {}  # no agents provided
        with pytest.raises(ConfigurationError, match="Agent for stage"):
            build_graph(agents, stages=["upload", "etl"])

    def test_empty_stages_raises(self) -> None:
        from phronesisml.workflow.graph import build_graph

        agents = {"upload": _make_stub_agent("upload")}
        with pytest.raises(ConfigurationError, match="No stages to wire"):
            build_graph(agents, stages=[])

    def test_pipeline_order_contains_expected_stages(self) -> None:
        from phronesisml.workflow.graph import PIPELINE_ORDER

        expected = [
            "upload",
            "etl",
            "validation",
            "eda",
            "target_detection",
            "feature_engineering",
            "model_selection",
            "evaluation",
            "explainability",
            "reporting",
            "storage",
        ]
        assert expected == PIPELINE_ORDER


def _make_stub_agent(name: str) -> Any:
    """Create a minimal stub agent for graph tests."""
    from phronesisml.agents.base import _StubAgent

    stub = _StubAgent(name=name, description=f"Stub for {name}")

    class _Agent:
        name = stub.name
        description = stub.description

        async def run(self, state: Any) -> AgentResult:
            return await stub.run(state)

        def get_tools(self) -> list:
            return stub.get_tools()

    return _Agent()
