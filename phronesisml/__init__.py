"""Phronesis — public SDK surface.

This is the canonical entry point for programmatic use of Phronesis.
All public API is exposed here; ``interfaces/cli/`` consumes this
surface.

Usage::

    # Simple API (recommended for quickstart)
    from phronesisml import analyze, train

    profile = analyze("data.csv")
    result = train("data.csv")

    # OOP API
    from phronesisml import Phronesis

    ml = Phronesis("data.csv")
    ml.run()
    print(ml.report())

    # Advanced API (full control)
    import phronesisml

    result = await phronesisml.run_pipeline(data_path="data.csv")
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.configs.settings import PhronesisConfig
from phronesisml.exceptions import ConfigurationError, PhronesisError, WorkflowError
from phronesisml.sdk import (
    DatasetSummary,
    EDAReport,
    EvaluationMetrics,
    ExplanationReport,
    FeatureReport,
    ModelInfo,
    Phronesis,
    TargetInfo,
    ValidationReport,
)
from phronesisml.simple import (
    CleanResult,
    DatasetProfile,
    ExplainResult,
    FeatureResult,
    ModelResult,
    TargetResult,
    TrainResult,
    ValidationResult,
    analyze,
    analyze_async,
    clean,
    clean_async,
    detect_target,
    detect_target_async,
    engineer,
    engineer_async,
    explain,
    explain_async,
    report,
    report_async,
    select_model,
    select_model_async,
    train,
    train_async,
    validate,
    validate_async,
)
from phronesisml.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

__version__ = "0.2.0"

__all__ = [
    # ── Simple API ──────────────────────────────────────
    "analyze",
    "analyze_async",
    "clean",
    "clean_async",
    "validate",
    "validate_async",
    "detect_target",
    "detect_target_async",
    "engineer",
    "engineer_async",
    "select_model",
    "select_model_async",
    "explain",
    "explain_async",
    "report",
    "report_async",
    "train",
    "train_async",
    "CleanResult",
    "DatasetProfile",
    "ExplainResult",
    "FeatureResult",
    "ModelResult",
    "TargetResult",
    "TrainResult",
    "ValidationResult",
    # ── OOP API ─────────────────────────────────────────
    "Phronesis",
    "DatasetSummary",
    "EDAReport",
    "EvaluationMetrics",
    "ExplanationReport",
    "FeatureReport",
    "ModelInfo",
    "TargetInfo",
    "ValidationReport",
    # ── Advanced API ────────────────────────────────────
    "PhronesisConfig",
    "PhronesisError",
    "ConfigurationError",
    "WorkflowError",
    "WorkflowState",
    "run_pipeline",
    "__version__",
]


def _compose_agents(
    config: PhronesisConfig,
    data_path: str,
) -> dict[str, Any]:
    """Manually compose all agents via constructor injection.

    This is the composition root — the only place where concrete agent
    and engine classes are instantiated.  The rest of the SDK depends
    on abstractions (``BaseAgent``, ``BaseEngine``).

    All agent imports are deferred to this function so that
    ``import phronesisml`` does not pull in every dependency eagerly.
    """
    from phronesisml.agents.eda.agent import EDAAgent
    from phronesisml.agents.etl.agent import ETLAgent, ETLConfig
    from phronesisml.agents.evaluation.agent import EvaluationAgent
    from phronesisml.agents.explainability.agent import ExplainabilityAgent
    from phronesisml.agents.feature_engineering.agent import FeatureEngineeringAgent
    from phronesisml.agents.model_selection.agent import ModelSelectionAgent
    from phronesisml.agents.reporting.agent import ReportingAgent
    from phronesisml.agents.storage.agent import StorageAgent
    from phronesisml.agents.target_detection.agent import TargetDetectionAgent
    from phronesisml.agents.upload.agent import UploadAgent
    from phronesisml.agents.validation.agent import ValidationAgent
    from phronesisml.engines.engine_selector import select_engine

    # Select the computation engine
    engine = select_engine(config=config, data_path=data_path)

    # Instantiate agents with their dependencies
    agents: dict[str, Any] = {
        "upload": UploadAgent(engine=engine),
        "validation": ValidationAgent(engine=engine),
        "etl": ETLAgent(config=ETLConfig(null_strategy="drop")),
        "eda": EDAAgent(engine=engine),
        "target_detection": TargetDetectionAgent(engine=engine),
        "feature_engineering": FeatureEngineeringAgent(
            engine=engine,
            feature_selection_config=config.feature_selection,
        ),
        "model_selection": ModelSelectionAgent(engine=engine),
        "evaluation": EvaluationAgent(engine=engine),
        "explainability": ExplainabilityAgent(engine=engine),
        "reporting": ReportingAgent(),
        "storage": StorageAgent(),
    }
    return agents


_FULL_PIPELINE_STAGES: list[str] = [
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


async def run_pipeline(
    data_path: str,
    engine_preference: str | None = None,
    null_strategy: str = "drop",
    stages: list[str] | None = None,
    config: PhronesisConfig | None = None,
) -> dict[str, Any]:
    """Run the Phronesis pipeline on a dataset.

    This is the primary public API.  It:
    1. Builds configuration (from *config* or defaults).
    2. Composes agents via manual DI.
    3. Constructs the LangGraph workflow with the requested stages.
    4. Executes the graph with the initial state.

    Args:
        data_path: Path to the input dataset.
        engine_preference: Force a specific engine (``"pandas"``, ``"polars"``,
            ``"spark"``).  ``None`` for auto-selection.
        null_strategy: Null handling strategy (``"drop"``, ``"fill"``, ``"flag"``).
        stages: Ordered list of pipeline stages to execute.  If ``None``,
            runs the full pipeline (all 11 stages).
        config: Optional pre-built configuration.  If ``None``, a config is
            constructed from the other arguments.

    Returns:
        A dict summarising the pipeline results.

    Raises:
        WorkflowError: If the workflow graph execution fails.

    """
    if config is None:
        config = PhronesisConfig()
    if engine_preference is not None:
        config.engine.preferred = engine_preference
    if stages is None:
        stages = list(_FULL_PIPELINE_STAGES)

    logger.info("Phronesis pipeline starting — data_path=%s", data_path)

    # 1–3. Compose agents, build graph, build initial state
    try:
        agents = _compose_agents(config, data_path)
        from phronesisml.workflow.graph import build_graph

        graph = build_graph(agents, stages=stages)
        initial_state = WorkflowState(data_path=data_path)
    except WorkflowError:
        raise
    except ConfigurationError as exc:
        msg = f"Pipeline configuration failed: {exc}"
        logger.exception(msg)
        raise WorkflowError(msg) from exc
    except Exception as exc:
        msg = f"Pipeline setup failed: {exc}"
        logger.exception(msg)
        raise WorkflowError(msg) from exc

    # 4. Execute
    try:
        final_state = await graph.ainvoke(initial_state)
    except WorkflowError:
        raise
    except Exception as exc:
        msg = f"Workflow execution failed: {exc}"
        logger.exception(msg)
        raise WorkflowError(msg) from exc

    logger.info("Phronesis pipeline complete.")

    # Extract summary from the final state
    if isinstance(final_state, dict):
        return _extract_summary(final_state)
    return _extract_summary(final_state.model_dump())


def _extract_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Build a summary dict from the final workflow state."""
    processed = state.get("processed_data")
    validated = state.get("validated_data")
    profile = state.get("data_profile")
    best_pipeline = state.get("best_pipeline")
    evaluation_report = state.get("evaluation_report")

    return {
        "row_count": state.get("row_count"),
        "column_count": (
            len(processed.columns)
            if processed is not None
            else (len(validated.columns) if validated is not None else None)
        ),
        "transformations": (
            len(state["transform_log"]) if state.get("transform_log") is not None else 0
        ),
        "validation_passed": (
            state["validation_report"].get("passed")
            if state.get("validation_report") is not None
            else None
        ),
        "numeric_columns": (profile.get("numeric_columns") if profile is not None else None),
        "categorical_columns": (
            profile.get("categorical_columns") if profile is not None else None
        ),
        "target_column": state.get("target_column"),
        "task_type": state.get("task_type"),
        "target_detection_confidence": state.get("target_detection_confidence"),
        "ambiguity_reason": state.get("ambiguity_reason"),
        "n_features": (
            len(state["feature_names"]) if state.get("feature_names") is not None else None
        ),
        "best_model_type": (best_pipeline.get("model_type") if best_pipeline is not None else None),
        "best_model_score": (best_pipeline.get("score") if best_pipeline is not None else None),
        "hpo_truncated": (best_pipeline.get("truncated") if best_pipeline is not None else None),
        "evaluation_metrics": (
            evaluation_report.get("metrics") if evaluation_report is not None else None
        ),
        "evaluation_ambiguity_caveat": (
            evaluation_report.get("ambiguity_caveat") if evaluation_report is not None else None
        ),
        "explanation_sampled": (
            state["explanation_report"].get("sampled")
            if state.get("explanation_report") is not None
            else None
        ),
        "explanation_explainer_type": (
            state["explanation_report"].get("explainer_type")
            if state.get("explanation_report") is not None
            else None
        ),
        "final_report_length": (
            len(state["final_report"]) if state.get("final_report") is not None else None
        ),
    }
