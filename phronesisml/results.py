"""Typed result objects for the PhronesisML simple API.

All frozen dataclasses returned by the simple API functions
(``analyze``, ``clean``, ``validate``, etc.) are defined here as
the single source of truth.  This avoids duplication between
``simple.py`` and ``sdk.py`` and makes the result types reusable.

Usage::

    from phronesisml.results import DatasetProfile, TrainResult

    profile = DatasetProfile(shape=(100, 5), ...)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "AnomalyResult",
    "CleanResult",
    "ClusteringResult",
    "DatasetProfile",
    "ExplainResult",
    "FeatureResult",
    "ModelResult",
    "TaskDetectionResult",
    "TargetResult",
    "TrainResult",
    "ValidationResult",
]


@dataclass(frozen=True)
class DatasetProfile:
    """Structured profile of a dataset after upload + ETL + validation + EDA.

    Example::

        profile = analyze("data.csv")
        print(f"{profile.shape[0]} rows, {profile.shape[1]} columns")
        for col, count in profile.missing_counts.items():
            print(f"  {col}: {count} missing")
    """

    shape: tuple[int, int]
    dtypes: dict[str, str]
    numeric_summary: dict[str, dict[str, float]]
    categorical_summary: dict[str, dict[str, Any]]
    missing_counts: dict[str, int]
    memory_usage_bytes: int
    column_names: list[str]
    validation_passed: bool


@dataclass(frozen=True)
class CleanResult:
    """Result of running upload + ETL on a dataset.

    Example::

        result = clean("data.csv", null_strategy="fill")
        print(f"Cleaned {result.n_rows} rows")
    """

    n_rows: int
    n_columns: int
    transform_log: list[dict[str, Any]]
    column_names: list[str]


@dataclass(frozen=True)
class ValidationResult:
    """Result of running upload + ETL + validation on a dataset.

    Example::

        result = validate("data.csv")
        if result.passed:
            print("All checks passed")
        else:
            print(f"Issues: {result.issues}")
    """

    passed: bool
    n_rows: int
    n_columns: int
    null_columns: list[str]
    empty_columns: list[str]
    duplicate_rows: int
    issues: list[str]


@dataclass(frozen=True)
class TargetResult:
    """Result of automatic target detection.

    Example::

        result = detect_target("data.csv")
        print(f"Target: {result.column} ({result.task_type})")
    """

    column: str
    task_type: str
    confidence: float
    ambiguity_reason: str | None


@dataclass(frozen=True)
class FeatureResult:
    """Result of feature engineering.

    Example::

        result = engineer("data.csv")
        print(f"{result.n_features} features from {result.n_rows} rows")
    """

    feature_names: list[str]
    n_features: int
    n_rows: int


@dataclass(frozen=True)
class ModelResult:
    """Result of model selection and evaluation.

    Example::

        result = select_model("data.csv")
        print(f"Best: {result.best_model_type} (score={result.best_score:.4f})")
    """

    best_model_type: str
    best_score: float
    candidates: list[dict[str, Any]]
    best_params: dict[str, Any]
    truncated: bool
    trials_used: int
    task_type: str | None
    evaluation_metrics: dict[str, Any] | None
    ambiguity_caveat: str | None
    estimated_training_cost: str = "unknown"


@dataclass(frozen=True)
class ExplainResult:
    """Result of SHAP-based model explanation.

    Example::

        result = explain("data.csv")
        for feature, importance in result.feature_importance.items():
            print(f"  {feature}: {importance:.4f}")
    """

    feature_importance: dict[str, float]
    explainer_type: str
    sampled: bool
    n_samples_used: int
    n_features_used: int = 0
    max_samples: int = 0


@dataclass(frozen=True)
class TrainResult:
    """Full pipeline result with model, explanation, and report.

    Example::

        result = train("data.csv")
        print(f"Model: {result.best_model_type}")
        print(result.report)
    """

    best_model_type: str
    best_score: float
    candidates: list[dict[str, Any]]
    best_params: dict[str, Any]
    task_type: str | None
    feature_importance: dict[str, float]
    explainer_type: str
    report: str
    artifact_uri: str | None
    estimated_training_cost: str = "unknown"


@dataclass(frozen=True)
class ClusteringResult:
    """Result of clustering analysis.

    Example::

        result = cluster("data.csv")
        print(f"Algorithm: {result.algorithm}, Clusters: {result.n_clusters}")
    """

    algorithm: str
    n_clusters: int
    silhouette_score: float | None
    davies_bouldin_score: float | None
    calinski_harabasz_score: float | None
    cluster_labels: list[int]
    params: dict[str, Any]
    report: str


@dataclass(frozen=True)
class AnomalyResult:
    """Result of anomaly detection.

    Example::

        result = detect_anomalies("data.csv")
        print(f"Anomalies: {result.n_anomalies} of {result.n_total}")
    """

    algorithm: str
    n_anomalies: int
    n_total: int
    contamination: float
    anomaly_labels: list[int]
    anomaly_scores: list[float]
    params: dict[str, Any]
    report: str


@dataclass(frozen=True)
class TaskDetectionResult:
    """Result of unified task detection.

    Example::

        result = detect_task("data.csv")
        print(f"Task: {result.task_type} (confidence: {result.confidence:.2f})")
    """

    task_type: str
    target_column: str | None
    confidence: float
    ambiguity_reason: str | None
