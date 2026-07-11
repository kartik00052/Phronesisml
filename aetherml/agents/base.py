"""Base contracts for the AetherML agent system.

Every agent in the framework must satisfy the ``BaseAgent`` protocol.
The protocol uses structural subtyping (``Protocol``) so agents do not
need to inherit from a base class — they only need to implement the
required attributes and methods with the correct signatures.

Design rationale:
- ``Protocol`` over ABC: avoids diamond-inheritance issues when agents
  also need domain-specific base classes (e.g. LLM-backed agents).
- ``async run``: agents may perform I/O (file reads, LLM calls, DB
  queries) and async keeps the workflow non-blocking.
- ``AgentResult``: a lightweight return type that carries the agent's
  output payload and optional metadata, keeping the contract uniform
  across all agents regardless of what they produce.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from aetherml.exceptions import AgentNotImplementedError


class AgentResult(BaseModel):
    """Standardised return value from every agent ``run()`` call.

    Attributes:
        success: Whether the agent completed without error.
        data: Agent-specific output payload.  The shape varies per agent
              and is documented in each agent's own module docstring.
        error: Human-readable error message when ``success`` is False.
        exception: Original exception object when ``success`` is False.
            Preserves the exception type, traceback, and cause chain for
            diagnostics.  May be ``None`` for configuration/validation
            errors that do not originate from an exception.
        metadata: Arbitrary key-value metadata (e.g. row counts, timings).
    """

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    exception: Any = Field(default=None, exclude=True)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Tool(BaseModel):
    """Descriptor for a tool an agent exposes to the workflow or LLM.

    This is a data descriptor, not a callable — the actual tool
    implementation lives in the agent; the ``Tool`` object is a
    serialisable declaration used for discovery and documentation.
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class BaseAgent(Protocol):
    """Protocol that every AetherML agent must satisfy.

    Agents are stateless with respect to the workflow — all mutable
    state lives in ``WorkflowState`` and is passed in on every ``run()``
    call.  This makes agents independently testable and composable.
    """

    name: str
    description: str

    async def run(self, state: Any) -> AgentResult:  # noqa: ANN401
        """Execute the agent's core logic against the current workflow state.

        Agents MUST return an ``AgentResult`` — they MUST NOT raise
        exceptions for expected/transient failures (bad data, missing
        columns, model failures).  Instead, return
        ``AgentResult(success=False, error=..., exception=exc)`` so the
        workflow can decide whether to continue or abort.

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

    async def run(self, state: Any) -> AgentResult:  # noqa: ANN401
        raise AgentNotImplementedError(
            f"Agent '{self.name}' has not been implemented yet."
        )

    def get_tools(self) -> list[Tool]:
        return []
