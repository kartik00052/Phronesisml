"""Explainability schemas — 1:1 with ``frontend/src/types/explainability.ts``.

Built from the SDK's ``shap.json`` artifact (``explanation_report``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ExplanationReport(BaseModel):
    feature_importance: dict[str, float]
    explainer_type: str = "none"
    sampled: bool = False
    n_samples_used: int = 0
    n_features_used: int = 0
    max_samples: int = 0

    model_config = ConfigDict(extra="allow")


class FeatureImportanceItem(BaseModel):
    feature: str
    value: float

    model_config = ConfigDict(extra="allow")


class ShapPoint(BaseModel):
    feature: str
    shapValue: float
    featureValue: float

    model_config = ConfigDict(extra="allow")


class ExplanationSample(BaseModel):
    sampleId: int
    baseValue: float
    prediction: float
    predictionLabel: str | None = None
    importance: list[FeatureImportanceItem]
    beeswarm: list[ShapPoint]

    model_config = ConfigDict(extra="allow")


class ExplainabilityView(BaseModel):
    report: ExplanationReport
    importance: list[FeatureImportanceItem]
    beeswarm: list[ShapPoint]
    baseValue: float = 0.0
    prediction: float | None = None
    predictionLabel: str | None = None
    sampleId: int = 0
    samples: list[ExplanationSample] | None = None

    model_config = ConfigDict(extra="allow")
