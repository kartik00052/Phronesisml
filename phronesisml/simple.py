"""Simple API — zero-friction entry points for common ML tasks.

Every function in this module is a synchronous wrapper around the
existing ``Phronesis`` class (which itself delegates to LangGraph-orchestrated
agents).  No business logic is duplicated; all computation flows through
the same pipeline infrastructure.

Usage::

    from phronesisml import analyze, train

    profile = analyze("data.csv")
    print(profile.shape)

    result = train("data.csv")
    print(result.best_model_type)

Each function also has an ``_async`` variant for use inside already-async
contexts (FastAPI, Jupyter async mode)::

    profile = await analyze_async("data.csv")
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


# ── Typed return objects ─────────────────────────────────────────
# Re-exported from phronesisml.results for backward compatibility.
from phronesisml.results import (  # noqa: E402, F401
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

# ── Pipeline stage constants ─────────────────────────────────────

_STAGES_ANALYZE = ["upload", "etl", "validation", "eda"]
_STAGES_CLEAN = ["upload", "etl"]
_STAGES_VALIDATE = ["upload", "etl", "validation"]
_STAGES_DETECT_TARGET = ["upload", "etl", "validation", "eda", "target_detection"]
_STAGES_ENGINEER = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
]
_STAGES_SELECT_MODEL = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
]
_STAGES_EXPLAIN = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "explainability",
]
_STAGES_REPORT = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "explainability",
    "reporting",
]
_STAGES_TRAIN = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "explainability",
    "reporting",
    "storage",
]

_STAGES_CLUSTER = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "reporting",
]

_STAGES_ANOMALY = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "reporting",
]

_STAGES_DETECT_TASK = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
]


# ── Internal helpers ─────────────────────────────────────────────


def _run_sync(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run a coroutine synchronously, detecting nested event loops."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        raise RuntimeError(
            "This function cannot be called from inside a running event loop "
            "(e.g. inside FastAPI or Jupyter's async mode). "
            "Use the corresponding _async variant with 'await' instead."
        )


def _build_config(
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
) -> Any:
    """Build an PhronesisConfig from flat keyword arguments."""
    from phronesisml.configs.settings import (
        EngineConfig,
        FeatureSelectionConfig,
        PhronesisConfig,
    )

    return PhronesisConfig(
        engine=EngineConfig(preferred=engine),
        feature_selection=FeatureSelectionConfig(
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
        ),
    )


async def _run_stages_async(ml: Any, stages: list[str]) -> None:
    """Run pipeline stages asynchronously on an Phronesis instance."""
    await ml._run_stages(stages)


def _build_dataset_profile(ml: Any) -> DatasetProfile:
    """Build DatasetProfile from phronesisml state after EDA."""
    import pandas as pd

    state = ml._state
    profile = state.data_profile or {}
    raw = state.raw_data

    # Compute shape from raw data
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

    # Get EDA profile data
    numeric_summary = profile.get("numeric_summary", {})
    categorical_summary = profile.get("categorical_summary", {})

    # Override memory if profile has it
    if "memory_bytes" in profile:
        memory = profile["memory_bytes"]

    # Get shape from profile if available
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


def _build_clean_result(ml: Any) -> CleanResult:
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


def _build_validation_result(ml: Any) -> ValidationResult:
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


def _build_target_result(ml: Any) -> TargetResult:
    """Build TargetResult from phronesisml state after target detection."""
    state = ml._state
    return TargetResult(
        column=state.target_column or "",
        task_type=state.task_type or "unknown",
        confidence=state.target_detection_confidence or 0.0,
        ambiguity_reason=state.ambiguity_reason,
    )


def _build_feature_result(ml: Any) -> FeatureResult:
    """Build FeatureResult from phronesisml state after feature engineering."""
    state = ml._state
    feature_names = state.feature_names or []
    return FeatureResult(
        feature_names=feature_names,
        n_features=len(feature_names),
        n_rows=state.row_count or 0,
    )


def _build_model_result(ml: Any) -> ModelResult:
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


def _build_explain_result(ml: Any) -> ExplainResult:
    """Build ExplainResult from phronesisml state after explainability."""
    state = ml._state
    er = state.explanation_report or {}
    return ExplainResult(
        feature_importance=er.get("feature_importance", {}),
        explainer_type=er.get("explainer_type", "none"),
        sampled=er.get("sampled", False),
        n_samples_used=er.get("n_samples_used", 0),
    )


def _build_train_result(ml: Any) -> TrainResult:
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


def _build_clustering_result(ml: Any) -> ClusteringResult:
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


def _build_anomaly_result(ml: Any) -> AnomalyResult:
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


def _build_task_detection_result(ml: Any) -> TaskDetectionResult:
    """Build TaskDetectionResult from phronesisml state."""
    state = ml._state
    return TaskDetectionResult(
        task_type=state.task_type or "unknown",
        target_column=state.target_column,
        confidence=state.target_detection_confidence or 0.0,
        ambiguity_reason=state.ambiguity_reason,
    )


# ── Public API: sync functions ───────────────────────────────────


def analyze(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> DatasetProfile:
    """Load, clean, validate, and profile a dataset.

    Runs upload, ETL, validation, and EDA stages. Returns a structured
    dataset profile with shape, dtypes, per-column statistics, and
    memory usage.

    Args:
        path: Path to a CSV, Excel, JSON, or Parquet file.
        engine: Force a specific engine (``"pandas"``, ``"polars"``,
            ``"spark"``). ``None`` for auto-selection.
        null_strategy: Null handling strategy (``"drop"``, ``"fill"``,
            ``"flag"``). Default ``"drop"``.

    Returns:
        A ``DatasetProfile`` with shape, dtypes, summaries, and
        memory usage.

    Example::

        from phronesisml import analyze

        profile = analyze("data.csv")
        print(f"{profile.shape[0]} rows, {profile.shape[1]} columns")
        print(f"Memory: {profile.memory_usage_bytes / 1024:.1f} KB")
    """
    return _run_sync(analyze_async(path, engine=engine, null_strategy=null_strategy))


async def analyze_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> DatasetProfile:
    """Async variant of :func:`analyze`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(engine=engine, null_strategy=null_strategy)
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_ANALYZE)
    return _build_dataset_profile(ml)


def clean(
    path: str,
    *,
    null_strategy: str = "drop",
    engine: str | None = None,
) -> CleanResult:
    """Load and clean a dataset (upload + ETL).

    Args:
        path: Path to a data file.
        null_strategy: Null handling strategy (``"drop"``, ``"fill"``,
            ``"flag"``). Default ``"drop"``.
        engine: Force a specific engine. ``None`` for auto-selection.

    Returns:
        A ``CleanResult`` with row/column counts and transform log.

    Example::

        from phronesisml import clean

        result = clean("data.csv", null_strategy="fill")
        print(f"Cleaned {result.n_rows} rows, {result.n_columns} columns")
    """
    return _run_sync(clean_async(path, null_strategy=null_strategy, engine=engine))


async def clean_async(
    path: str,
    *,
    null_strategy: str = "drop",
    engine: str | None = None,
) -> CleanResult:
    """Async variant of :func:`clean`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(engine=engine, null_strategy=null_strategy)
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_CLEAN)
    return _build_clean_result(ml)


def validate(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> ValidationResult:
    """Load, clean, and validate a dataset.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.

    Returns:
        A ``ValidationResult`` with pass/fail status and issues.

    Example::

        from phronesisml import validate

        result = validate("data.csv")
        if not result.passed:
            for issue in result.issues:
                print(issue)
    """
    return _run_sync(validate_async(path, engine=engine, null_strategy=null_strategy))


async def validate_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> ValidationResult:
    """Async variant of :func:`validate`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(engine=engine, null_strategy=null_strategy)
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_VALIDATE)
    return _build_validation_result(ml)


def detect_target(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> TargetResult:
    """Detect the prediction target and task type.

    Runs upload through target detection. Returns the detected column,
    task type (classification/regression), and confidence score.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.

    Returns:
        A ``TargetResult`` with column, task_type, and confidence.

    Example::

        from phronesisml import detect_target

        result = detect_target("data.csv")
        print(f"Target: {result.column} ({result.task_type})")
    """
    return _run_sync(detect_target_async(path, engine=engine, null_strategy=null_strategy))


async def detect_target_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> TargetResult:
    """Async variant of :func:`detect_target`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(engine=engine, null_strategy=null_strategy)
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_DETECT_TARGET)
    return _build_target_result(ml)


def engineer(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
) -> FeatureResult:
    """Engineer features from a dataset.

    Runs upload through feature engineering. Returns the engineered
    feature names and counts.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        variance_threshold: Drop features with variance below this.
        correlation_threshold: Drop features with target correlation below this.
        min_features: Minimum number of features to retain.

    Returns:
        A ``FeatureResult`` with feature names and counts.

    Example::

        from phronesisml import engineer

        result = engineer("data.csv", variance_threshold=0.005)
        print(f"{result.n_features} features engineered")
    """
    return _run_sync(
        engineer_async(
            path,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
        )
    )


async def engineer_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
) -> FeatureResult:
    """Async variant of :func:`engineer`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
    )
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_ENGINEER)
    return _build_feature_result(ml)


def select_model(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
) -> ModelResult:
    """Select and evaluate the best model for a dataset.

    Runs upload through model selection and evaluation. Returns the
    best model type, score, and evaluation metrics.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        variance_threshold: Drop features with variance below this.
        correlation_threshold: Drop features with target correlation below this.
        min_features: Minimum number of features to retain.
        cv: Number of cross-validation folds.  If ``None`` (default),
            uses a single train/test split.  Pass an integer ≥ 2 to
            enable k-fold cross-validation.

    Returns:
        A ``ModelResult`` with model type, score, and metrics.

    Example::

        from phronesisml import select_model

        result = select_model("data.csv")
        print(f"Best: {result.best_model_type} ({result.best_score:.4f})")
    """
    return _run_sync(
        select_model_async(
            path,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
            cv=cv,
        )
    )


async def select_model_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
) -> ModelResult:
    """Async variant of :func:`select_model`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
    )
    ml = Phronesis(path, config=config)
    if cv is not None:
        from phronesisml.agents.model_selection.agent import ModelSelectionAgent

        ml._get_agents()  # ensure agents exist
        ml._agents["model_selection"] = ModelSelectionAgent(
            engine=ml._eng,
            cv=cv,
        )
    await _run_stages_async(ml, _STAGES_SELECT_MODEL)
    return _build_model_result(ml)


def explain(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
) -> ExplainResult:
    """Explain model predictions using SHAP.

    Runs upload through explainability. Returns feature importance
    scores. SHAP is a core dependency and is always available.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        variance_threshold: Drop features with variance below this.
        correlation_threshold: Drop features with target correlation below this.
        min_features: Minimum number of features to retain.

    Returns:
        An ``ExplainResult`` with feature importance scores.

    Example::

        from phronesisml import explain

        result = explain("data.csv")
        for feature, importance in result.feature_importance.items():
            print(f"  {feature}: {importance:.4f}")
    """
    return _run_sync(
        explain_async(
            path,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
        )
    )


async def explain_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
) -> ExplainResult:
    """Async variant of :func:`explain`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
    )
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_EXPLAIN)
    return _build_explain_result(ml)


def report(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
) -> str:
    """Generate a Markdown report of the full pipeline.

    Runs upload through reporting. Returns a Markdown string
    summarizing all pipeline stages.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        variance_threshold: Drop features with variance below this.
        correlation_threshold: Drop features with target correlation below this.
        min_features: Minimum number of features to retain.

    Returns:
        A Markdown string with the pipeline report.

    Example::

        from phronesisml import report

        print(report("data.csv"))
    """
    return _run_sync(
        report_async(
            path,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
        )
    )


async def report_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
) -> str:
    """Async variant of :func:`report`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
    )
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_REPORT)
    return str(ml._state.final_report or "")


def train(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
    model_type: str | None = None,
) -> TrainResult:
    """Run the full ML pipeline and return trained model details.

    Runs all 11 stages: upload, ETL, validation, EDA, target detection,
    feature engineering, model selection, evaluation, explainability,
    reporting, and storage.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        variance_threshold: Drop features with variance below this.
        correlation_threshold: Drop features with target correlation below this.
        min_features: Minimum number of features to retain.
        cv: Number of cross-validation folds.  If ``None`` (default),
            uses a single train/test split.  Pass an integer ≥ 2 to
            enable k-fold cross-validation.
        model_type: Optional name of a specific model to train
            (e.g. ``"random_forest"``).

    Returns:
        A ``TrainResult`` with model, explanation, report, and
        artifact location.

    Example::

        from phronesisml import train

        result = train("data.csv")
        print(f"Model: {result.best_model_type}")
        print(f"Report length: {len(result.report)} chars")
    """
    return _run_sync(
        train_async(
            path,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
            cv=cv,
            model_type=model_type,
        )
    )


async def train_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
    model_type: str | None = None,
) -> TrainResult:
    """Async variant of :func:`train`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
    )
    ml = Phronesis(path, config=config)
    if cv is not None or model_type is not None:
        from phronesisml.agents.model_selection.agent import ModelSelectionAgent

        ml._get_agents()
        ml._agents["model_selection"] = ModelSelectionAgent(
            engine=ml._eng,
            cv=cv,
            model_type=model_type,
        )
    await _run_stages_async(ml, _STAGES_TRAIN)
    return _build_train_result(ml)


# ── Unsupervised API: clustering ──────────────────────────────────


def cluster(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> ClusteringResult:
    """Run clustering analysis on a dataset.

    Executes upload through clustering evaluation. Automatically
    selects the best clustering algorithm (KMeans, DBSCAN,
    Agglomerative) based on silhouette score.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.

    Returns:
        A ``ClusteringResult`` with algorithm, scores, and labels.

    Example::

        from phronesisml import cluster

        result = cluster("data.csv")
        print(f"Algorithm: {result.algorithm}, Clusters: {result.n_clusters}")
    """
    return _run_sync(cluster_async(path, engine=engine, null_strategy=null_strategy))


async def cluster_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> ClusteringResult:
    """Async variant of :func:`cluster`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(engine=engine, null_strategy=null_strategy)
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_CLUSTER)
    return _build_clustering_result(ml)


# ── Unsupervised API: anomaly detection ───────────────────────────


def detect_anomalies(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    contamination: float = 0.1,
) -> AnomalyResult:
    """Run anomaly detection on a dataset.

    Executes upload through anomaly evaluation. Automatically
    selects the best algorithm (Isolation Forest, LOF).

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        contamination: Expected fraction of anomalies.

    Returns:
        An ``AnomalyResult`` with labels, scores, and metadata.

    Example::

        from phronesisml import detect_anomalies

        result = detect_anomalies("data.csv")
        print(f"Anomalies: {result.n_anomalies} of {result.n_total}")
    """
    return _run_sync(
        detect_anomalies_async(
            path,
            engine=engine,
            null_strategy=null_strategy,
            contamination=contamination,
        )
    )


async def detect_anomalies_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    contamination: float = 0.1,
) -> AnomalyResult:
    """Async variant of :func:`detect_anomalies`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(engine=engine, null_strategy=null_strategy)
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_ANOMALY)
    return _build_anomaly_result(ml)


# ── Unsupervised API: task detection ──────────────────────────────


def detect_task(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> TaskDetectionResult:
    """Detect the ML task type for a dataset.

    Determines whether the dataset is suited for supervised learning
    (classification/regression), unsupervised learning (clustering),
    anomaly detection, or analytics-only exploration.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.

    Returns:
        A ``TaskDetectionResult`` with task_type, confidence, and
        target_column (if supervised).

    Example::

        from phronesisml import detect_task

        result = detect_task("data.csv")
        print(f"Task: {result.task_type} (confidence: {result.confidence:.2f})")
    """
    return _run_sync(detect_task_async(path, engine=engine, null_strategy=null_strategy))


async def detect_task_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> TaskDetectionResult:
    """Async variant of :func:`detect_task`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(engine=engine, null_strategy=null_strategy)
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_DETECT_TASK)
    return _build_task_detection_result(ml)
