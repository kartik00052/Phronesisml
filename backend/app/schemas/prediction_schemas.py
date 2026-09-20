"""Prediction schemas — model inference over a run's stored model.

``samples`` entries mirror the run's cleaned feature schema (best-effort
column matching; scalar columns only).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class PredictionRequest(BaseModel):
    samples: list[dict[str, Any]]

    model_config = ConfigDict(extra="allow")


class PredictionResponse(BaseModel):
    runId: str = ""
    modelType: str = ""
    predictions: list[dict[str, Any]]

    model_config = ConfigDict(populate_by_name=True, extra="allow")
