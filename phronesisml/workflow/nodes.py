"""Workflow nodes — thin wrappers that adapt agents to LangGraph node signatures.

LangGraph nodes are functions ``(state) -> state_update``.  Each node
wraps exactly one agent, calling ``agent.run(state)`` and translating
the ``AgentResult`` into a state update dict.

Design:
- Nodes are factory functions that capture the agent via closure.
- This keeps the graph definition clean and the agent-to-node mapping
  explicit.
- Agents read from state and return their output.  Nodes translate
  the output into a state update dict that LangGraph merges.

Failure handling:
- Agents that return ``AgentResult(success=False)`` are logged as errors
  and raise ``AgentError`` to halt the pipeline.
- Agents that return ``AgentResult(success=True)`` with diagnostic
  metadata (warnings, blockers) propagate those diagnostics to the state
  for downstream agents to inspect.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.agents.base import BaseAgent
from phronesisml.exceptions import AgentError, AgentNotImplementedError

logger = logging.getLogger(__name__)


def make_node(agent: BaseAgent) -> Any:
    """Create a LangGraph node function from a ``BaseAgent`` instance.

    The returned function accepts the workflow state and returns
    a dict of state updates.  If the agent raises ``AgentNotImplementedError``
    (i.e. it is a stub), the node logs a warning and returns an empty
    update so the workflow continues.

    Args:
        agent: An agent satisfying the ``BaseAgent`` protocol.

    Returns:
        An async callable suitable for use as a LangGraph node.

    """

    async def node_fn(state: Any) -> dict[str, Any]:
        logger.info("Running agent: %s", agent.name)
        try:
            result = await agent.run(state)
        except AgentNotImplementedError:
            logger.warning("Agent '%s' is not implemented — skipping.", agent.name)
            return {}
        except Exception as exc:
            logger.exception("Agent '%s' raised an unhandled exception.", agent.name)
            msg = f"Agent '{agent.name}' raised an unexpected error: {exc}"
            raise AgentError(msg) from exc

        if not result.success:
            logger.error("Agent '%s' failed: %s", agent.name, result.error)
            msg = f"Agent '{agent.name}' failed: {result.error}"
            raise AgentError(
                msg,
                error_type=result.error_type,
                error_message=result.error_message,
                error_context=result.error_context,
            )

        # ── Propagate diagnostics from metadata ──────────────────────
        # If the agent returned diagnostic information (warnings,
        # blockers, pre-flight results), merge it into the state update
        # so downstream agents can inspect it.
        state_update = dict(result.data) if result.data else {}
        if result.metadata:
            # Store metadata under agent name for downstream access
            # e.g. state_update["target_detection_metadata"] = {...}
            meta_key = f"{agent.name}_metadata"
            state_update[meta_key] = result.metadata

            # Propagate pre-flight warnings/blockers to top-level state
            # so routers can make informed decisions.
            preflight = result.metadata.get("preflight")
            if preflight is not None:
                if preflight.get("blockers"):
                    state_update["preflight_blockers"] = preflight["blockers"]
                if preflight.get("warnings"):
                    state_update["preflight_warnings"] = preflight["warnings"]

        logger.info("Agent '%s' completed successfully.", agent.name)
        return state_update

    node_fn.__name__ = f"node_{agent.name}"
    node_fn.__doc__ = f"LangGraph node wrapping agent '{agent.name}'."
    return node_fn
