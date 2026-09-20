"""Model / evaluation schemas — 1:1 with ``frontend/src/types/model.ts``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class BestPipeline(BaseModel):
    model_type: str
    params: dict[str, Any]
    best_params: dict[str, Any]
    score: float | None = None
    trials_used: int | None = None
    time_elapsed: float | None = None
    truncated: bool = False
    estimated_training_cost: str = "unknown"

    model_config = ConfigDict(extra="allow")


class ModelRankingRow(BaseModel):
    rank: int = 0
    model_type: str
    primary_score: float | None = None
    secondary_metrics: dict[str, Any] = {}
    trials_used: int | None = None
    time_elapsed: float | None = None
    truncated: bool = False
    estimated_training_cost: str = "unknown"
    best: bool = False
    status: str = "ready"

    model_config = ConfigDict(extra="allow")


class ModelDetail(BaseModel):
    model_type: str
    model_class: str = ""
    best_params: dict[str, Any] = {}
    score: float | None = None
    trials_used: int | None = None
    time_elapsed: float | None = None
    truncated: bool = False
    estimated_training_cost: str = "unknown"
    taskType: str = "unknown"
    targetColumn: str | None = None
    nFeatures: int | None = None
    nSamples: int | None = None
    evaluation: dict[str, Any] | None = None
    rank: int = 0
    best: bool = False

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class MetricDescriptor(BaseModel):
    key: str
    label: str
    higherIsBetter: bool
    precision: int | None = None

    model_config = ConfigDict(extra="allow")
