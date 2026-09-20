"""Run schemas — 1:1 with ``frontend/src/types/run.ts``.

``RunRequest`` accepts the full new-run wizard payload (extra keys tolerated
for forwards-compatibility).  ``Run`` / ``RunSummary`` / ``RecentRunActivity``
match the frontend contract field-for-field.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class RunRequest(BaseModel):
    dataPath: str | None = Field(default=None, alias="dataPath")
    fileName: str | None = Field(default=None, alias="fileName")
    datasetId: str | None = Field(default=None, alias="datasetId")
    engine: str | None = "auto"
    nullStrategy: str = Field(default="drop", alias="nullStrategy")
    stages: list[str] = Field(default_factory=list, alias="stages")
    mode: str = Field(default="balanced", alias="mode")
    targetOverride: str | None = Field(default=None, alias="targetOverride")
    taskOverride: str | None = Field(default=None, alias="taskOverride")
    cv: int | None = Field(default=None, alias="cv")
    modelType: str | None = Field(default=None, alias="modelType")
    maxTrials: int | None = Field(default=None, alias="maxTrials")
    maxTimeSeconds: int | None = Field(default=None, alias="maxTimeSeconds")
    varianceThreshold: float | None = Field(default=None, alias="varianceThreshold")
    correlationThreshold: float | None = Field(default=None, alias="correlationThreshold")
    minFeatures: int | None = Field(default=None, alias="minFeatures")
    samplingStrategy: str | None = Field(default=None, alias="samplingStrategy")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class SamplingInfo(BaseModel):
    was_sampled: bool
    sampling_method: str | None = None
    sampling_ratio: float | None = None
    original_rows: int | None = None
    sample_rows: int | None = None
    random_state: int | None = None
    reason: str | None = None

    model_config = ConfigDict(extra="allow")


class ResourceReport(BaseModel):
    n_rows: int
    n_cols: int
    total_cells: int
    estimated_memory_mb: float
    estimated_encoded_features: int
    estimated_encoded_memory_mb: float
    estimated_train_test_memory_mb: float
    estimated_shap_memory_mb: float
    estimated_runtime_seconds: float
    requires_sampling: bool
    recommended_sample_size: int
    recommended_sample_fraction: float
    sampling_reason: str
    auto_sample_size: int
    available_memory_gb: float

    model_config = ConfigDict(extra="allow")


class RunError(BaseModel):
    type: str
    message: str
    context: dict[str, str] | None = None

    model_config = ConfigDict(extra="allow")


class RunSummary(BaseModel):
    id: str
    datasetName: str
    datasetPath: str
    fileFormat: str
    rows: int = 0
    columns: int = 0
    fileSizeBytes: int = 0
    taskType: str = "unknown"
    targetColumn: str | None = None
    engine: str = "pandas"
    engineReason: str = ""
    bestModelType: str | None = None
    bestScore: float | None = None
    primaryMetric: str = ""
    status: RunStatus = "queued"
    mode: str = "balanced"
    createdAt: str
    updatedAt: str
    durationMs: int | None = None
    trialCount: int | None = None
    hpoTruncated: bool | None = None
    stagesRequested: list[str] | None = None
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Run(BaseModel):
    id: str
    status: RunStatus
    request: RunRequest
    summary: RunSummary
    sampling: SamplingInfo | None = None
    resourceReport: ResourceReport | None = None
    warnings: list[str] = Field(default_factory=list)
    error: RunError | None = None
    logs: list[str] = Field(default_factory=list)
    stagesRequested: list[str] = Field(default_factory=list)
    stagesExecuted: list[str] = Field(default_factory=list)
    totalDurationMs: int | None = None
    createdAt: str
    updatedAt: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class RecentRunActivity(BaseModel):
    id: str
    datasetName: str
    status: RunStatus
    taskType: str
    bestModelType: str | None
    bestScore: float | None
    createdAt: str
    durationMs: int | None

    model_config = ConfigDict(extra="allow")


class RunLogs(BaseModel):
    run_id: str
    logs: list[str]

    model_config = ConfigDict(extra="allow")
