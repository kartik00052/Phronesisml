"""LangGraph workflow orchestration layer.

This package contains the state model, routing logic, graph builder,
and node wrappers that orchestrate agent execution via LangGraph.

Modules:
    state   — ``WorkflowState`` Pydantic model (single source of truth)
    router  — Conditional routing functions for the graph
    graph   — ``build_graph()`` compiles the LangGraph topology
    nodes   — ``make_node()`` wraps agents into graph nodes
"""

from __future__ import annotations
