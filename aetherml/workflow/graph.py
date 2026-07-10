"""Workflow graph — LangGraph StateGraph definition.

Builds the directed graph that orchestrates agent execution.  The graph
is constructed dynamically via ``build_graph()``, which accepts
pre-initialised agents and a list of stages to include, then wires them
into the LangGraph topology.

Current topology (linear):
    upload → etl → [end]

Extended topology (with validation + eda):
    upload → etl → validation → eda → [end]

Full pipeline (future):
    upload → validation → engine_selection → etl → [profiling ∥ eda]
    → feature_engineering → target_detection → model_selection
    → evaluation → explainability → reporting → storage

Design:
- The graph is rebuilt on every ``build_graph()`` call.  This is cheap
  (LangGraph compiles quickly) and keeps the function side-effect-free.
- ``WorkflowState`` is passed as the graph's state schema.
- The ``stages`` parameter controls which agents are wired in, in the
  order defined by ``PIPELINE_ORDER``.
- Routing functions return generic labels (``"proceed"`` or ``"__end__"``);
  ``build_graph`` maps ``"proceed"`` to the concrete next stage name.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from aetherml.agents.base import BaseAgent
from aetherml.workflow.nodes import make_node
from aetherml.workflow.router import (
    route_after_eda,
    route_after_etl,
    route_after_evaluation,
    route_after_feature_engineering,
    route_after_model_selection,
    route_after_target_detection,
    route_after_upload,
    route_after_validation,
)
from aetherml.workflow.state import WorkflowState

logger = logging.getLogger(__name__)

# Canonical pipeline order — stages must appear in this sequence.
# Target detection must run before feature engineering (FE needs to
# know which column is the target to exclude it from transforms).
PIPELINE_ORDER: list[str] = [
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

# Maps each stage name to its routing function.
_STAGE_ROUTERS: dict[str, Any] = {
    "upload": route_after_upload,
    "etl": route_after_etl,
    "validation": route_after_validation,
    "eda": route_after_eda,
    "target_detection": route_after_target_detection,
    "feature_engineering": route_after_feature_engineering,
    "model_selection": route_after_model_selection,
    "evaluation": route_after_evaluation,
}


def build_graph(
    agents: dict[str, BaseAgent],
    stages: list[str] | None = None,
) -> Any:
    """Build and compile the LangGraph workflow graph.

    Args:
        agents: Mapping of agent name → agent instance.  Must include
            at least ``"upload"`` and ``"etl"``.  Additional agents are
            wired only if they appear in *stages*.
        stages: Ordered list of stage names to include.  If ``None``,
            defaults to ``["upload", "etl"]`` for backward compatibility.

    Returns:
        A compiled LangGraph ``StateGraph`` ready for execution.
    """
    if stages is None:
        stages = ["upload", "etl"]

    # Validate requested stages
    valid_names = set(PIPELINE_ORDER)
    for stage in stages:
        if stage not in valid_names:
            msg = f"Unknown stage: {stage!r}. Valid stages: {sorted(valid_names)}"
            raise ValueError(msg)

    # Build the ordered list of nodes to wire
    ordered_stages = [s for s in PIPELINE_ORDER if s in stages]

    graph = StateGraph(WorkflowState)

    # ── Add nodes ───────────────────────────────────────────────────
    for stage_name in ordered_stages:
        agent = agents.get(stage_name)
        if agent is None:
            msg = f"Agent for stage '{stage_name}' not provided."
            raise ValueError(msg)
        graph.add_node(stage_name, make_node(agent))

    # ── Wire edges ──────────────────────────────────────────────────
    if not ordered_stages:
        msg = "No stages to wire — empty pipeline."
        raise ValueError(msg)

    graph.set_entry_point(ordered_stages[0])

    for i, stage_name in enumerate(ordered_stages):
        is_last = i == len(ordered_stages) - 1
        router = _STAGE_ROUTERS.get(stage_name)

        if is_last:
            if router is not None:
                # Last stage: "proceed" also means end (no next stage)
                graph.add_conditional_edges(
                    stage_name,
                    router,
                    {"proceed": END, "__end__": END},
                )
            else:
                graph.add_edge(stage_name, END)
        else:
            next_stage = ordered_stages[i + 1]
            if router is not None:
                graph.add_conditional_edges(
                    stage_name,
                    router,
                    {"proceed": next_stage, "__end__": END},
                )
            else:
                graph.add_edge(stage_name, next_stage)

    logger.info("Workflow graph built: %s", " → ".join(ordered_stages) + " → end")
    return graph.compile()
