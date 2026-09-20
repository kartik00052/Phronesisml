"""Dashboard statistics schemas — 1:1 with ``frontend/src/types/run.ts``.

``engineBreakdown`` / ``taskBreakdown`` are keyed records (engine/task name →
count), matching the frontend ``Record<EngineName, number>`` maps.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DashboardStats(BaseModel):
    totalRuns: int = Field(default=0, alias="totalRuns")
    activeRuns: int = Field(default=0, alias="activeRuns")
    completedRuns: int = Field(default=0, alias="completedRuns")
    failedRuns: int = Field(default=0, alias="failedRuns")
    totalDatasets: int = Field(default=0, alias="totalDatasets")
    totalModels: int = Field(default=0, alias="totalModels")
    avgBestScore: float | None = Field(default=None, alias="avgBestScore")
    totalArtifacts: int = Field(default=0, alias="totalArtifacts")
    engineBreakdown: dict[str, int] = Field(default_factory=dict, alias="engineBreakdown")
    taskBreakdown: dict[str, int] = Field(default_factory=dict, alias="taskBreakdown")

    model_config = ConfigDict(populate_by_name=True, extra="allow")
