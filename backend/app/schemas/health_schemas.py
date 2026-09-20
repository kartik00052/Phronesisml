"""Health & capabilities schemas — 1:1 with ``frontend/src/types/health.ts``.

Field names use snake_case where the frontend contract declares snake_case.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class DependencyInfo(BaseModel):
    installed: bool
    version: str | None = None
    optional: bool | None = None

    model_config = ConfigDict(extra="allow")


class HealthReport(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    python: str
    dependencies: dict[str, DependencyInfo]
    missing_core: list[str]
    database: dict | None = None
    storage: dict | None = None

    model_config = ConfigDict(extra="allow")


class CapabilitiesReport(BaseModel):
    name: str
    version: str
    offline: bool
    deterministic: bool
    task_types: list[str]
    engines: list[str]
    explainers: list[str]
    pipeline_stages: list[str]
    sdk_methods: list[str]
    cli_commands: list[str]
    extras: list[str]

    model_config = ConfigDict(extra="allow")
