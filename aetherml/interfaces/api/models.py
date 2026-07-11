"""Pydantic models for the AetherML REST API.

Request and response schemas used by ``app.py``.  Kept separate from
the SDK internals so that API surface changes don't leak into the core.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PipelineRequest(BaseModel):
    """Body for ``POST /pipeline``."""

    model_config = ConfigDict(extra="forbid")

    data_path: str = Field(..., min_length=1, description="Path to the input dataset.")
    engine: Literal["pandas", "polars", "spark"] | None = Field(
        None,
        description="Force an engine: pandas, polars, spark. None = auto.",
    )
    null_strategy: Literal["drop", "fill", "flag"] = Field(
        "drop",
        description="Null handling strategy: drop, fill, flag.",
    )
    stages: list[str] | None = Field(
        None,
        description="Ordered pipeline stages to execute. None = defaults.",
    )


class PipelineResponse(BaseModel):
    """Successful pipeline result."""

    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    result: dict[str, Any]


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    model_config = ConfigDict(extra="forbid")

    status: str = "error"
    error_type: str
    message: str
    detail: Any = None


class HealthResponse(BaseModel):
    """Health-check payload."""

    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    version: str
    python: str
