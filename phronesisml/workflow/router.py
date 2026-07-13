"""Workflow router — conditional routing logic for the LangGraph graph.

This module defines routing functions that determine which node executes
next based on the current workflow state.

Routing functions return generic labels (``"proceed"`` or ``"__end__"``).
``build_graph()`` maps ``"proceed"`` to the actual next stage name based
on which stages are included in the pipeline.  This keeps routing
functions decoupled from the specific graph topology.

Current implementation: linear routing (Upload → ETL → Validation →
EDA → End).

Known future improvements (TODO):
- Add feedback loops: Evaluation → Feature Engineering when metrics are poor.
- Add parallel branching: Profiling + EDA running concurrently.
- Add skip logic: allow users to bypass optional stages (EDA, explainability).
- Add conditional branches: different paths for classification vs regression.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)


def route_after_upload(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the upload node.

    If data was loaded successfully, proceed to the next stage.
    Otherwise, end the workflow.
    """
    if getattr(state, "raw_data", None) is not None:
        logger.info("Upload succeeded — proceeding.")
        return "proceed"
    logger.warning("Upload produced no data — ending workflow.")
    return "__end__"


def route_after_etl(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the ETL node.

    If ETL produced processed data, proceed to the next stage.
    Otherwise, end the workflow.
    """
    if getattr(state, "processed_data", None) is not None:
        logger.info("ETL succeeded — proceeding.")
        return "proceed"
    logger.warning("ETL produced no processed data — ending workflow.")
    return "__end__"


def route_after_validation(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the Validation node.

    If validation produced validated data, proceed to the next stage.
    Otherwise, end the workflow.
    """
    if getattr(state, "validated_data", None) is not None:
        logger.info("Validation succeeded — proceeding.")
        return "proceed"
    logger.warning("Validation produced no validated data — ending workflow.")
    return "__end__"


def route_after_eda(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the EDA node.

    If EDA produced a data profile, proceed to target detection.
    Otherwise, end the workflow.
    """
    if getattr(state, "data_profile", None) is not None:
        logger.info("EDA succeeded — proceeding.")
        return "proceed"
    logger.warning("EDA produced no data profile — ending workflow.")
    return "__end__"


def route_after_target_detection(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the Target Detection node.

    If target detection found a target column, proceed to feature
    engineering.  Even ambiguous detections proceed — the ambiguity
    is surfaced to the user but does not block the pipeline.
    """
    if getattr(state, "target_column", None) is not None:
        logger.info("Target detection succeeded — proceeding.")
        return "proceed"
    logger.warning("No target column detected — ending workflow.")
    return "__end__"


def route_after_feature_engineering(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the Feature Engineering node.

    If feature engineering produced features, proceed to model
    selection.  Otherwise, end the workflow.
    """
    if getattr(state, "features", None) is not None:
        logger.info("Feature engineering succeeded — proceeding to model selection.")
        return "proceed"
    logger.warning("Feature engineering produced no features — ending workflow.")
    return "__end__"


def route_after_model_selection(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the Model Selection node.

    If a trained model was produced, proceed to evaluation.
    Otherwise, end the workflow.
    """
    if getattr(state, "trained_model", None) is not None:
        logger.info("Model selection succeeded — proceeding to evaluation.")
        return "proceed"
    logger.warning("No trained model produced — ending workflow.")
    return "__end__"


def route_after_evaluation(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the Evaluation node.

    If evaluation produced a report, proceed to explainability.
    Otherwise, end the workflow.
    """
    if getattr(state, "evaluation_report", None) is not None:
        logger.info("Evaluation succeeded — proceeding to explainability.")
        return "proceed"
    logger.warning("Evaluation produced no report — ending workflow.")
    return "__end__"


def route_after_explainability(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the Explainability node.

    If explanation was produced, proceed to reporting.
    Otherwise, end the workflow.
    """
    if getattr(state, "explanation_report", None) is not None:
        logger.info("Explainability succeeded — proceeding to reporting.")
        return "proceed"
    logger.warning("Explainability produced no report — ending workflow.")
    return "__end__"


def route_after_reporting(state: Any) -> Literal["proceed", "__end__"]:
    """Route after the Reporting node.

    If the report was assembled, proceed (to storage or end, depending
    on the pipeline stages).  Otherwise, end the workflow.
    """
    if getattr(state, "final_report", None) is not None:
        logger.info("Report assembled — proceeding.")
        return "proceed"
    logger.warning("Report assembly produced no output — ending.")
    return "__end__"
