"""Pipeline schemas — 1:1 with ``frontend/src/types/pipeline.ts``."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PipelineStageStatus = Literal[
    "idle", "queued", "running", "completed", "warning", "failed", "skipped", "sampled"
]


class StageSummary(BaseModel):
    """A stage summary carries whatever the backend exposed at completion."""

    model_config = ConfigDict(extra="allow")


class StageEvent(BaseModel):
    run_id: str
    stage: str
    status: str
    summary: dict[str, Any] | None = None
    ts: str

    model_config = ConfigDict(extra="allow")


class StageDetail(BaseModel):
    id: str
    name: str
    status: PipelineStageStatus
    queuedAt: str | None = None
    startedAt: str | None = None
    completedAt: str | None = None
    durationMs: int | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    error: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class PipelineProgress(BaseModel):
    runId: str = Field(alias="runId")
    status: str
    completedStages: list[str] = Field(default_factory=list, alias="completedStages")
    currentStage: str | None = Field(default=None, alias="currentStage")
    currentStagesCompleted: int = Field(default=0, alias="currentStagesCompleted")
    totalStages: int = Field(default=0, alias="totalStages")
    messages: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class PipelineOverview(BaseModel):
    runId: str = Field(alias="runId")
    mode: str
    stagesRequested: list[str] = Field(default_factory=list, alias="stagesRequested")
    stagesExecuted: list[str] = Field(default_factory=list, alias="stagesExecuted")
    sampling: dict[str, Any] | None = None
    totalDurationMs: int = Field(default=0, alias="totalDurationMs")

    model_config = ConfigDict(populate_by_name=True, extra="allow")
