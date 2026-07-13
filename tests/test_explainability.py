"""Tests for the Explainability agent and SHAP explainer module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from phronesisml.agents.explainability.agent import ExplainabilityAgent
from phronesisml.engines.pandas_engine import PandasEngine
from phronesisml.ml.explainability.shap_explainer import (
    DEFAULT_MAX_SAMPLES,
    _compute_global_importance,
    _create_explainer,
)
from phronesisml.workflow.state import WorkflowState

# ── Helpers ──────────────────────────────────────────────────────────


class _MockTreeModel:
    """Mock tree-based model for explainer selection tests."""

    def __init__(self) -> None:
        self.__class__.__name__ = "RandomForestClassifier"

    def predict(self, X: Any) -> Any:
        return np.zeros(X.shape[0])


class _MockLinearModel:
    """Mock linear model for explainer selection tests."""

    def __init__(self) -> None:
        self.__class__.__name__ = "LinearRegression"

    def predict(self, X: Any) -> Any:
        return np.zeros(X.shape[0])


class _MockUnknownModel:
    """Mock unknown model type (triggers KernelExplainer)."""

    def __init__(self) -> None:
        self.__class__.__name__ = "CustomModel"

    def predict(self, X: Any) -> Any:
        return np.zeros(X.shape[0])


def _make_shap_mock() -> MagicMock:
    """Create a mock shap module with tree, linear, and kernel explainers."""
    shap = MagicMock()

    # TreeExplainer
    tree_explainer = MagicMock()
    tree_explainer.shap_values.return_value = np.random.rand(5, 3)
    shap.TreeExplainer.return_value = tree_explainer

    # LinearExplainer
    linear_explainer = MagicMock()
    linear_explainer.shap_values.return_value = np.random.rand(5, 3)
    shap.LinearExplainer.return_value = linear_explainer

    # KernelExplainer
    kernel_explainer = MagicMock()
    kernel_explainer.shap_values.return_value = np.random.rand(5, 3)
    shap.KernelExplainer.return_value = kernel_explainer

    return shap


def _make_state(
    model: Any = None,
    features: pd.DataFrame = None,
    feature_names: list[str] | None = None,
    target_column: str | None = None,
) -> WorkflowState:
    """Create a WorkflowState with the given inputs for testing."""
    state = WorkflowState(
        run_id="test-run",
        status="running",
    )
    state.trained_model = model
    state.features = features
    state.feature_names = feature_names
    state.target_column = target_column
    return state


# ── Protocol tests ───────────────────────────────────────────────────


class TestExplainabilityAgentProtocol:
    """Verify ExplainabilityAgent satisfies BaseAgent protocol."""

    def test_has_run_method(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        assert hasattr(agent, "run")
        assert callable(agent.run)

    def test_has_get_tools_method(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        assert hasattr(agent, "get_tools")
        assert callable(agent.get_tools)

    def test_isinstance_base_agent(self) -> None:
        from phronesisml.agents.base import BaseAgent

        agent = ExplainabilityAgent(engine=PandasEngine())
        assert isinstance(agent, BaseAgent)

    def test_get_tools_returns_list(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        tools = agent.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "explain_model"


# ── run() tests ──────────────────────────────────────────────────────


class TestExplainabilityAgentRun:
    """Test ExplainabilityAgent.run() logic."""

    @pytest.mark.asyncio
    async def test_no_trained_model_returns_failure(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        state = _make_state(model=None)
        result = await agent.run(state)
        assert not result.success
        assert "trained_model" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_data_returns_failure(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        state = _make_state(model=_MockTreeModel(), features=None)
        state.validated_data = None
        state.processed_data = None
        result = await agent.run(state)
        assert not result.success
        assert "features" in result.error.lower() or "processed_data" in result.error.lower()

    @pytest.mark.asyncio
    async def test_shap_not_installed_returns_graceful_degradation(self) -> None:
        """Missing SHAP must degrade gracefully, not crash the pipeline."""
        agent = ExplainabilityAgent(engine=PandasEngine())
        X = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        state = _make_state(model=_MockTreeModel(), features=X)
        state.validated_data = None
        state.processed_data = None

        with patch(
            "phronesisml.agents.explainability.agent.compute_shap_explanations",
            side_effect=ImportError("No module named 'shap'"),
        ):
            result = await agent.run(state)
            # Graceful degradation: success=True with empty report
            assert result.success is True
            report = result.data["explanation_report"]
            assert report["explainer_type"] == "none"
            assert report["feature_importance"] == {}

    @pytest.mark.asyncio
    async def test_successful_run(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        X = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        state = _make_state(
            model=_MockTreeModel(),
            features=X,
            feature_names=["a", "b"],
        )

        mock_report = {
            "feature_importance": {"a": 0.6, "b": 0.4},
            "explainer_type": "TreeExplainer",
            "sampled": False,
            "n_samples_used": 3,
            "max_samples": DEFAULT_MAX_SAMPLES,
        }

        with patch(
            "phronesisml.agents.explainability.agent.compute_shap_explanations",
            return_value=mock_report,
        ):
            result = await agent.run(state)

        assert result.success
        assert "explanation_report" in result.data
        report = result.data["explanation_report"]
        assert report["explainer_type"] == "TreeExplainer"
        assert not report["sampled"]
        assert result.metadata["explainer_type"] == "TreeExplainer"

    @pytest.mark.asyncio
    async def test_falls_back_to_validated_data(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        X = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        state = _make_state(model=_MockTreeModel(), features=None)
        state.validated_data = X

        mock_report = {
            "feature_importance": {"a": 0.5, "b": 0.5},
            "explainer_type": "TreeExplainer",
            "sampled": False,
            "n_samples_used": 2,
            "max_samples": DEFAULT_MAX_SAMPLES,
        }

        with patch(
            "phronesisml.agents.explainability.agent.compute_shap_explanations",
            return_value=mock_report,
        ):
            result = await agent.run(state)

        assert result.success

    @pytest.mark.asyncio
    async def test_falls_back_to_processed_data(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        X = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        state = _make_state(model=_MockTreeModel(), features=None)
        state.validated_data = None
        state.processed_data = X

        mock_report = {
            "feature_importance": {"a": 0.5, "b": 0.5},
            "explainer_type": "TreeExplainer",
            "sampled": False,
            "n_samples_used": 2,
            "max_samples": DEFAULT_MAX_SAMPLES,
        }

        with patch(
            "phronesisml.agents.explainability.agent.compute_shap_explanations",
            return_value=mock_report,
        ):
            result = await agent.run(state)

        assert result.success

    @pytest.mark.asyncio
    async def test_shap_computation_exception_returns_failure(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        X = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        state = _make_state(model=_MockTreeModel(), features=X)

        with patch(
            "phronesisml.agents.explainability.agent.compute_shap_explanations",
            side_effect=RuntimeError("SHAP crashed"),
        ):
            result = await agent.run(state)

        assert not result.success
        assert "shap computation failed" in result.error.lower()


# ── Resource bounds tests ────────────────────────────────────────────


class TestResourceBounds:
    """Test SHAP resource bounds (max_samples)."""

    @pytest.mark.asyncio
    async def test_max_samples_from_config(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine(), max_samples=50)
        assert agent._max_samples == 50

    @pytest.mark.asyncio
    async def test_default_max_samples(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine())
        assert agent._max_samples == DEFAULT_MAX_SAMPLES


# ── Explainer selection tests ────────────────────────────────────────


class TestExplainerSelection:
    """Test that the correct explainer is selected based on model class."""

    def test_tree_model_selects_tree_explainer(self) -> None:
        shap = _make_shap_mock()
        model = _MockTreeModel()
        X = np.random.rand(10, 3)

        explainer_type, explainer = _create_explainer(model, X, shap)
        assert explainer_type == "TreeExplainer"
        shap.TreeExplainer.assert_called_once_with(model)

    def test_linear_model_selects_linear_explainer(self) -> None:
        shap = _make_shap_mock()
        model = _MockLinearModel()
        X = np.random.rand(10, 3)

        explainer_type, explainer = _create_explainer(model, X, shap)
        assert explainer_type == "LinearExplainer"
        shap.LinearExplainer.assert_called_once()

    def test_unknown_model_selects_kernel_explainer(self) -> None:
        shap = _make_shap_mock()
        model = _MockUnknownModel()
        X = np.random.rand(10, 3)

        explainer_type, explainer = _create_explainer(model, X, shap)
        assert explainer_type == "KernelExplainer"
        shap.KernelExplainer.assert_called_once()


# ── Global importance computation tests ──────────────────────────────


class TestComputeGlobalImportance:
    """Test _compute_global_importance with different SHAP value shapes."""

    def test_single_output(self) -> None:
        shap_values = np.array([[0.1, 0.3, 0.2], [0.2, 0.1, 0.3]])
        feature_names = ["a", "b", "c"]

        importance = _compute_global_importance(shap_values, feature_names, None)
        assert len(importance) == 3
        assert "a" in importance
        assert importance["b"] == pytest.approx(0.2)

    def test_multi_class_output(self) -> None:
        # List of arrays: one per class
        shap_values = [
            np.array([[0.1, 0.2], [0.3, 0.1]]),
            np.array([[0.2, 0.1], [0.1, 0.3]]),
        ]
        feature_names = ["x", "y"]

        importance = _compute_global_importance(shap_values, feature_names, None)
        assert len(importance) == 2
        assert "x" in importance
        assert "y" in importance

    def test_empty_feature_names(self) -> None:
        shap_values = np.array([[0.1, 0.2]])
        importance = _compute_global_importance(shap_values, [], None)
        assert importance == {}

    def test_more_features_than_names(self) -> None:
        shap_values = np.array([[0.1, 0.2, 0.3]])
        feature_names = ["a", "b"]

        importance = _compute_global_importance(shap_values, feature_names, None)
        assert len(importance) == 2


# ── Resource bounds integration tests ────────────────────────────────


class TestResourceBoundsIntegration:
    """Test resource bounds are enforced during SHAP computation."""

    @pytest.mark.asyncio
    async def test_sampled_output_flagged(self) -> None:
        agent = ExplainabilityAgent(engine=PandasEngine(), max_samples=5)
        # Create features with more rows than max_samples
        X = pd.DataFrame({"a": range(20), "b": range(20)})
        state = _make_state(model=_MockTreeModel(), features=X)

        mock_report = {
            "feature_importance": {"a": 0.5, "b": 0.5},
            "explainer_type": "TreeExplainer",
            "sampled": True,
            "n_samples_used": 5,
            "max_samples": 5,
        }

        with patch(
            "phronesisml.agents.explainability.agent.compute_shap_explanations",
            return_value=mock_report,
        ):
            result = await agent.run(state)

        assert result.success
        assert result.data["explanation_report"]["sampled"] is True
        assert result.data["explanation_report"]["n_samples_used"] == 5


# ── Import check ─────────────────────────────────────────────────────


class TestImportChecks:
    """Verify no LLM/Gemma imports anywhere in the explainability module."""

    def test_no_llm_imports_in_shap_explainer(self) -> None:
        from pathlib import Path

        base = Path(__file__).parent.parent / "phronesisml" / "ml" / "explainability"
        shap_file = base / "shap_explainer.py"
        lines = shap_file.read_text().splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"'):
                continue
            for kw in ["openai", "langchain", "gemma", "gemini"]:
                assert kw not in stripped.lower()

    def test_no_llm_imports_in_explainability_agent(self) -> None:
        from pathlib import Path

        base = Path(__file__).parent.parent / "phronesisml" / "agents" / "explainability"
        agent_file = base / "agent.py"
        lines = agent_file.read_text().splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"'):
                continue
            for kw in ["openai", "langchain", "gemma", "gemini"]:
                assert kw not in stripped.lower()
