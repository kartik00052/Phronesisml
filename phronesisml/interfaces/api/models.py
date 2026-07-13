"""Pydantic models for the Phronesis REST API.

All request and response schemas live here.  The SDK surface never
depends on these models — changes here never leak into the core.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Standard envelope ────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Structured error information."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    details: Any = Field(None, description="Optional structured error context.")
    documentation: str = Field(
        "",
        description="Link to documentation for this error code.",
    )


class APIResponse(BaseModel):
    """Standard API response envelope.

    Every endpoint returns this structure.  On success ``success`` is
    ``True`` and ``data`` contains the payload.  On failure ``success``
    is ``False`` and ``error`` contains structured error information.
    """

    model_config = ConfigDict(extra="forbid")

    success: bool
    data: Any = None
    error: ErrorDetail | None = None


# ── Job models ───────────────────────────────────────────────────


class JobData(BaseModel):
    """Status and result of an asynchronous job."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., description="Unique job identifier.")
    status: str = Field(
        ...,
        description="Job status: queued, running, completed, failed.",
    )
    created_at: str = Field(..., description="ISO-8601 creation timestamp.")
    started_at: str | None = Field(None, description="ISO-8601 start timestamp.")
    completed_at: str | None = Field(None, description="ISO-8601 completion timestamp.")
    result: dict[str, Any] | None = Field(None, description="Job result payload.")
    error: str | None = Field(None, description="Error message if job failed.")


# ── Health / version / capabilities ──────────────────────────────


class HealthData(BaseModel):
    """Health-check payload."""

    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    version: str
    python: str
    platform: str
    engines: list[str]


class VersionData(BaseModel):
    """SDK version information."""

    model_config = ConfigDict(extra="forbid")

    version: str
    python: str
    sdk: str = "phronesisml"


class CapabilitiesData(BaseModel):
    """System capabilities for client discovery."""

    model_config = ConfigDict(extra="forbid")

    file_formats: list[str] = Field(
        ...,
        description="Supported file extensions (without dot).",
    )
    engines: list[str] = Field(..., description="Available computation engines.")
    pipeline_stages: list[str] = Field(
        ...,
        description="All available pipeline stage names.",
    )
    limits: dict[str, Any] = Field(
        ...,
        description="System limits (max upload size, etc.).",
    )
    job_persistence: str = Field(
        default="in-memory-single-process",
        description=(
            "Job storage backend. 'in-memory-single-process' means jobs "
            "are lost on restart and not shared across processes/workers. "
            "For production, use a persistent backend (Redis, database)."
        ),
    )


# ── Constants (derived from SDK, not duplicated) ────────────────

ALLOWED_EXTENSIONS: set[str] = {
    ".csv",
    ".xlsx",
    ".xls",
    ".json",
    ".parquet",
    ".feather",
    ".arrow",
}

MAX_UPLOAD_SIZE_MB: int = 100

DOCUMENTATION_BASE_URL: str = "https://docs.Phronesis.ai/errors"
