"""Base contracts for the Phronesis agent system.

Every agent in the framework must satisfy the ``BaseAgent`` protocol.
The protocol uses structural subtyping (``Protocol``) so agents do not
need to inherit from a base class — they only need to implement the
required attributes and methods with the correct signatures.

Design rationale:
- ``Protocol`` over ABC: avoids diamond-inheritance issues when agents
  also need domain-specific base classes (e.g. domain-specific agents).
- ``async run``: agents may perform I/O (file reads, DB
  queries) and async keeps the workflow non-blocking.
- ``AgentResult``: a lightweight return type that carries the agent's
  output payload and optional metadata, keeping the contract uniform
  across all agents regardless of what they produce.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = ["AgentResult", "BaseAgent", "ResolvedData", "Tool", "resolve_features_target"]

from pydantic import BaseModel, Field

from phronesisml.exceptions import AgentNotImplementedError

# Re-export from services for backward compatibility
from phronesisml.services.data_resolution import ResolvedData, resolve_features_target


class AgentResult(BaseModel):
    """Standardised return value from every agent ``run()`` call.

    Attributes:
        success: Whether the agent completed without error.
        data: Agent-specific output payload.  The shape varies per agent
              and is documented in each agent's own module docstring.
        error: Human-readable error message when ``success`` is False.
        error_type: Exception class name when ``success`` is False.
            E.g. ``"DataLoadError"``, ``"ValueError"``.  Survives JSON
            serialization for non-Python consumers (FastAPI boundary).
        error_message: Original exception message when ``success`` is False.
            May differ from ``error`` (which is the agent-wrapped message).
        error_context: Optional structured context dict for debugging.
            Keys and values must be strings to survive serialization.
        metadata: Arbitrary key-value metadata (e.g. row counts, timings).

    """

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    error_context: dict[str, str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Tool(BaseModel):
    """Descriptor for a tool an agent exposes to the workflow.

    This is a data descriptor, not a callable — the actual tool
    implementation lives in the agent; the ``Tool`` object is a
    serialisable declaration used for discovery and documentation.
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class BaseAgent(Protocol):
    """Protocol that every Phronesis agent must satisfy.

    Agents are stateless with respect to the workflow — all mutable
    state lives in ``WorkflowState`` and is passed in on every ``run()``
    call.  This makes agents independently testable and composable.
    """

    name: str
    description: str

    async def run(self, state: Any) -> AgentResult:
        """Execute the agent's core logic against the current workflow state.

        Agents MUST return an ``AgentResult`` — they MUST NOT raise
        exceptions for expected/transient failures (bad data, missing
        columns, model failures).  Instead, return
        ``AgentResult(success=False, error=..., error_type=..., error_message=...)``
        so the workflow can decide whether to continue or abort.

        Agents SHOULD raise only for programming errors (bugs, missing
        dependencies) or truly unrecoverable failures (out of memory).

        Args:
            state: The shared ``WorkflowState`` instance.

        Returns:
            An ``AgentResult`` carrying the agent's output.

        """
        ...

    def get_tools(self) -> list[Tool]:
        """Return the list of tools this agent exposes."""
        ...


class _StubAgent:
    """Minimal stub that satisfies ``BaseAgent`` for agents not yet implemented.

    This is used only during the initial skeleton pass to validate that
    the protocol works structurally across all 15 agent directories.
    It will be replaced by real implementations in subsequent passes.
    """

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    async def run(self, state: Any) -> AgentResult:
        msg = f"Agent '{self.name}' has not been implemented yet."
        raise AgentNotImplementedError(msg)

    def get_tools(self) -> list[Tool]:
        return []
