"""Engine selection schemas — engine recommendation + capability matrix.

``EngineRecommendation`` mirrors ``frontend/src/types/dataset.ts`` (camelCase
with a snake_case ``routing`` payload).  ``EngineCapabilities`` mirrors the
camelCase engine descriptor used by the engine profile UI.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EngineRecommendRequest(BaseModel):
    bytes: int = Field(gt=0)
    rows: int | None = None
    cols: int | None = None

    model_config = ConfigDict(extra="allow")


class EngineRoutingView(BaseModel):
    n_rows: int | None = None
    n_cols: int | None = None
    memory_bytes: int | None = None
    pandas_max_bytes: int | None = None

    model_config = ConfigDict(extra="allow")


class EngineRecommendation(BaseModel):
    engine: str
    reason: str
    routing: EngineRoutingView | None = None

    model_config = ConfigDict(extra="allow")


class EngineCapabilities(BaseModel):
    name: str
    description: str | None = None
    modelTypes: list[str] = Field(default_factory=list, alias="modelTypes")
    taskTypes: list[str] = Field(default_factory=list, alias="taskTypes")
    supportsGPU: bool = Field(default=False, alias="supportsGPU")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class EngineReport(BaseModel):
    engines: list[str]
    enginesAvailable: list[str] = Field(default_factory=list, alias="enginesAvailable")
    enginesMissing: list[str] = Field(default_factory=list, alias="enginesMissing")

    model_config = ConfigDict(populate_by_name=True, extra="allow")
