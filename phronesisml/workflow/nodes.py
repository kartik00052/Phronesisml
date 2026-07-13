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

        logger.info("Agent '%s' completed successfully.", agent.name)
        return result.data

    node_fn.__name__ = f"node_{agent.name}"
    node_fn.__doc__ = f"LangGraph node wrapping agent '{agent.name}'."
    return node_fn
