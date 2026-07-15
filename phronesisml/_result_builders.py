"""Result builder functions for the simple API.

Each function extracts data from a ``Phronesis`` workflow state and
constructs the appropriate result dataclass.  These are internal
helpers — the public API lives in ``simple.py``.
"""

from __future__ import annotations

from typing import Any

from phronesisml.results import (
    AnomalyResult,
    CleanResult,
    ClusteringResult,
    DatasetProfile,
    ExplainResult,
    FeatureResult,
    ModelResult,
    TargetResult,
    TaskDetectionResult,
    TrainResult,
    ValidationResult,
)

__all__ = [
    "build_dataset_profile",
    "build_clean_result",
    "build_validation_result",
    "build_target_result",
    "build_feature_result",
    "build_model_result",
    "build_explain_result",
    "build_train_result",
    "build_clustering_result",
    "build_anomaly_result",
    "build_task_detection_result",
]


def build_dataset_profile(ml: Any) -> DatasetProfile:
    """Build DatasetProfile from phronesisml state after EDA."""
    import pandas as pd

    state = ml._state
    profile = state.data_profile or {}
    raw = state.raw_data

    if raw is not None:
        df = raw if isinstance(raw, pd.DataFrame) else pd.DataFrame(raw)
        shape = (len(df), len(df.columns))
        dtypes = {c: str(d) for c, d in df.dtypes.items()}
        column_names = list(df.columns)
        missing = {k: int(v) for k, v in df.isnull().sum().items() if v > 0}
        memory = int(df.memory_usage(deep=True).sum())
    else:
        shape = (0, 0)
        dtypes = {}
        column_names = []
        missing = {}
        memory = 0

    numeric_summary = profile.get("numeric_summary", {})
    categorical_summary = profile.get("categorical_summary", {})

    if "memory_bytes" in profile:
        memory = profile["memory_bytes"]

    shape_raw = profile.get("shape", {})
    if isinstance(shape_raw, dict) and shape_raw:
        shape = (shape_raw.get("rows", shape[0]), shape_raw.get("columns", shape[1]))

    vr = state.validation_report or {}

    return DatasetProfile(
        shape=shape,
        dtypes=dtypes,
        numeric_summary=numeric_summary,
        categorical_summary=categorical_summary,
        missing_counts=missing,
        memory_usage_bytes=memory,
        column_names=column_names,
        validation_passed=vr.get("passed", False),
    )


def build_clean_result(ml: Any) -> CleanResult:
    """Build CleanResult from phronesisml state after ETL."""
    import pandas as pd

    state = ml._state
    processed = state.processed_data

    if processed is not None:
        df = processed if isinstance(processed, pd.DataFrame) else pd.DataFrame(processed)
        n_rows, n_columns = df.shape
        column_names = list(df.columns)
    else:
        n_rows = state.row_count or 0
        n_columns = 0
        column_names = []

    return CleanResult(
        n_rows=n_rows,
        n_columns=n_columns,
        transform_log=state.transform_log or [],
        column_names=column_names,
    )


def build_validation_result(ml: Any) -> ValidationResult:
    """Build ValidationResult from phronesisml state after validation."""
    import pandas as pd

    state = ml._state
    vr = state.validation_report or {}
    validated = state.validated_data

    if validated is not None:
        df = validated if isinstance(validated, pd.DataFrame) else pd.DataFrame(validated)
        n_rows, n_columns = df.shape
    else:
        n_rows = 0
        n_columns = 0

    issues: list[str] = []
    if not vr.get("passed", True):
        for col in vr.get("null_columns", []):
            issues.append(f"Column '{col}' has null values")
        for col in vr.get("empty_columns", []):
            issues.append(f"Column '{col}' is entirely empty")
        if vr.get("duplicate_rows", 0) > 0:
            issues.append(f"{vr['duplicate_rows']} duplicate rows detected")

    return ValidationResult(
        passed=vr.get("passed", False),
        n_rows=n_rows,
        n_columns=n_columns,
        null_columns=vr.get("null_columns", []),
        empty_columns=vr.get("empty_columns", []),
        duplicate_rows=vr.get("duplicate_rows", 0),
        issues=issues,
    )


def build_target_result(ml: Any) -> TargetResult:
    """Build TargetResult from phronesisml state after target detection."""
    state = ml._state
    return TargetResult(
        column=state.target_column or "",
        task_type=state.task_type or "unknown",
        confidence=state.target_detection_confidence or 0.0,
        ambiguity_reason=state.ambiguity_reason,
    )


def build_feature_result(ml: Any) -> FeatureResult:
    """Build FeatureResult from phronesisml state after feature engineering."""
    state = ml._state
    feature_names = state.feature_names or []
    return FeatureResult(
        feature_names=feature_names,
        n_features=len(feature_names),
        n_rows=state.row_count or 0,
    )


def build_model_result(ml: Any) -> ModelResult:
    """Build ModelResult from phronesisml state after evaluation."""
    state = ml._state
    bp = state.best_pipeline or {}
    eval_report = state.evaluation_report or {}
    return ModelResult(
        best_model_type=bp.get("model_type", "unknown"),
        best_score=bp.get("score", 0.0),
        candidates=state.candidate_models or [],
        best_params=bp.get("best_params", {}),
        truncated=bp.get("truncated", False),
        trials_used=bp.get("trials_used", 0),
        task_type=state.task_type,
        evaluation_metrics=eval_report.get("metrics"),
        ambiguity_caveat=eval_report.get("ambiguity_caveat"),
        estimated_training_cost=bp.get("estimated_training_cost", "unknown"),
    )


def build_explain_result(ml: Any) -> ExplainResult:
    """Build ExplainResult from phronesisml state after explainability."""
    state = ml._state
    er = state.explanation_report or {}
    return ExplainResult(
        feature_importance=er.get("feature_importance", {}),
        explainer_type=er.get("explainer_type", "none"),
        sampled=er.get("sampled", False),
        n_samples_used=er.get("n_samples_used", 0),
    )


def build_train_result(ml: Any) -> TrainResult:
    """Build TrainResult from phronesisml state after full pipeline."""
    state = ml._state
    bp = state.best_pipeline or {}
    er = state.explanation_report or {}
    return TrainResult(
        best_model_type=bp.get("model_type", "unknown"),
        best_score=bp.get("score", 0.0),
        candidates=state.candidate_models or [],
        best_params=bp.get("best_params", {}),
        task_type=state.task_type,
        feature_importance=er.get("feature_importance", {}),
        explainer_type=er.get("explainer_type", "none"),
        report=str(state.final_report or ""),
        artifact_uri=state.artifact_uri,
        estimated_training_cost=bp.get("estimated_training_cost", "unknown"),
    )


def build_clustering_result(ml: Any) -> ClusteringResult:
    """Build ClusteringResult from phronesisml state after clustering."""
    state = ml._state
    metrics = state.cluster_metrics or {}
    labels = state.cluster_labels or []
    return ClusteringResult(
        algorithm=metrics.get("algorithm", "unknown"),
        n_clusters=metrics.get("n_clusters", 0),
        silhouette_score=metrics.get("silhouette_score"),
        davies_bouldin_score=metrics.get("davies_bouldin_score"),
        calinski_harabasz_score=metrics.get("calinski_harabasz_score"),
        cluster_labels=labels,
        params=metrics.get("params", {}),
        report=str(state.final_report or ""),
    )


def build_anomaly_result(ml: Any) -> AnomalyResult:
    """Build AnomalyResult from phronesisml state after anomaly detection."""
    state = ml._state
    metrics = state.anomaly_metrics or {}
    labels = state.anomaly_labels or []
    scores = state.anomaly_scores or []
    n_total = len(labels) if labels else 0
    return AnomalyResult(
        algorithm=metrics.get("algorithm", "unknown"),
        n_anomalies=metrics.get("n_anomalies", 0),
        n_total=n_total,
        contamination=metrics.get("expected_contamination", 0.1),
        anomaly_labels=labels,
        anomaly_scores=scores,
        params=metrics.get("params", {}),
        report=str(state.final_report or ""),
    )


def build_task_detection_result(ml: Any) -> TaskDetectionResult:
    """Build TaskDetectionResult from phronesisml state."""
    state = ml._state
    return TaskDetectionResult(
        task_type=state.task_type or "unknown",
        target_column=state.target_column,
        confidence=state.target_detection_confidence or 0.0,
        ambiguity_reason=state.ambiguity_reason,
    )
