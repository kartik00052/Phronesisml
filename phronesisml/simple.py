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
from typing import TYPE_CHECKING, Any, TypeVar

from phronesisml._result_builders import (
    build_anomaly_result as _build_anomaly_result,
)
from phronesisml._result_builders import (
    build_clean_result as _build_clean_result,
)
from phronesisml._result_builders import (
    build_clustering_result as _build_clustering_result,
)
from phronesisml._result_builders import (
    build_dataset_profile as _build_dataset_profile,
)
from phronesisml._result_builders import (
    build_explain_result as _build_explain_result,
)
from phronesisml._result_builders import (
    build_feature_result as _build_feature_result,
)
from phronesisml._result_builders import (
    build_model_result as _build_model_result,
)
from phronesisml._result_builders import (
    build_target_result as _build_target_result,
)
from phronesisml._result_builders import (
    build_task_detection_result as _build_task_detection_result,
)
from phronesisml._result_builders import (
    build_train_result as _build_train_result,
)
from phronesisml._result_builders import (
    build_validation_result as _build_validation_result,
)
from phronesisml._stages import (
    _STAGES_ANALYZE,
    _STAGES_ANOMALY,
    _STAGES_CLEAN,
    _STAGES_CLUSTER,
    _STAGES_DETECT_TARGET,
    _STAGES_DETECT_TASK,
    _STAGES_ENGINEER,
    _STAGES_EXPLAIN,
    _STAGES_REPORT,
    _STAGES_SELECT_MODEL,
    _STAGES_TRAIN,
    _STAGES_VALIDATE,
)
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

if TYPE_CHECKING:
    from phronesisml.sdk import ModelComparison, SavedRun

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

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
    include_outlier_flag: bool = False,
) -> Any:
    """Build an PhronesisConfig from flat keyword arguments."""
    from phronesisml.configs.settings import (
        EngineConfig,
        FeatureSelectionConfig,
        PhronesisConfig,
    )

    return PhronesisConfig(
        null_strategy=null_strategy,
        engine=EngineConfig(preferred=engine),  # type: ignore[arg-type]
        feature_selection=FeatureSelectionConfig(
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
            include_outlier_flag=include_outlier_flag,
        ),
    )


async def _run_stages_async(ml: Any, stages: list[str]) -> None:
    """Run pipeline stages asynchronously on an Phronesis instance."""
    await ml._run_stages(stages)


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
    overrides: dict[str, dict[str, Any]] | None = None
    if cv is not None:
        overrides = {"model_selection": {"cv": cv}}
    ml = Phronesis(path, config=config, agent_overrides=overrides)
    await _run_stages_async(ml, _STAGES_SELECT_MODEL)
    return _build_model_result(ml)


def evaluate(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
) -> ModelResult:
    """Evaluate models on a dataset (alias of :func:`select_model`).

    Runs model selection and evaluation, returning the best model with
    its metrics.  Equivalent to ``select_model`` with the same
    arguments.

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
    """
    return _run_sync(
        evaluate_async(
            path,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
            cv=cv,
        )
    )


async def evaluate_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
) -> ModelResult:
    """Async variant of :func:`evaluate` -- selects and evaluates models.

    Delegates to :func:`select_model_async` (identical stage set:
    model selection plus evaluation).
    """
    return await select_model_async(
        path,
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
        cv=cv,
    )


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
    overrides: dict[str, dict[str, Any]] | None = None
    if cv is not None or model_type is not None:
        overrides = {"model_selection": {}}
        if cv is not None:
            overrides["model_selection"]["cv"] = cv
        if model_type is not None:
            overrides["model_selection"]["model_type"] = model_type
    ml = Phronesis(path, config=config, agent_overrides=overrides)
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
    ml._state.task_type = "clustering"
    ml._state.target_column = None
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
    ml._state.task_type = "anomaly_detection"
    ml._state.target_column = None
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


# ── Extended API: profiling ───────────────────────────────────────


def profile(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> DatasetProfile:
    """Profile a dataset (alias of :func:`analyze`).

    Loads, cleans, validates, and summarizes a dataset.  Provided as a
    descriptive entry point mirroring the SDK's ``profile()`` method.

    Args:
        path: Path to a data file.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.

    Returns:
        A ``DatasetProfile`` with shape, dtypes, summaries, and
        memory usage.

    Example::

        from phronesisml import profile

        summary = profile("data.csv")
        print(f"{summary.shape[0]} rows, {summary.shape[1]} columns")
    """
    return _run_sync(profile_async(path, engine=engine, null_strategy=null_strategy))


async def profile_async(
    path: str,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
) -> DatasetProfile:
    """Async variant of :func:`profile`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(engine=engine, null_strategy=null_strategy)
    ml = Phronesis(path, config=config)
    await _run_stages_async(ml, _STAGES_ANALYZE)
    return _build_dataset_profile(ml)


# ── Extended API: prediction ──────────────────────────────────────


def predict(
    path: str,
    data: Any,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
    model_type: str | None = None,
    already_engineered: bool = False,
) -> list[Any]:
    """Train a model on a dataset and predict on new rows.

    Runs upload through model selection, then applies the saved feature
    transform recipe to *data* and returns one prediction per row.  The
    target column, if present in *data*, is ignored.

    Args:
        path: Path to the training data file.
        data: A pandas DataFrame (or array-like) shaped like the
            training data.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        variance_threshold: Drop features with variance below this.
        correlation_threshold: Drop features with target correlation below this.
        min_features: Minimum number of features to retain.
        cv: Number of cross-validation folds.  ``None`` uses a single
            train/test split.
        model_type: Optional name of a specific model to train.
        already_engineered: ``True`` if *data* already contains the
            engineered feature columns.

    Returns:
        A list of model predictions, one per input row.

    Example::

        from phronesisml import predict

        predictions = predict("data.csv", new_rows)
        print(f"{len(predictions)} predictions")
    """
    return _run_sync(
        predict_async(
            path,
            data,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
            cv=cv,
            model_type=model_type,
            already_engineered=already_engineered,
        )
    )


async def predict_async(
    path: str,
    data: Any,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
    model_type: str | None = None,
    already_engineered: bool = False,
) -> list[Any]:
    """Async variant of :func:`predict`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
    )
    overrides: dict[str, dict[str, Any]] | None = None
    if cv is not None or model_type is not None:
        overrides = {"model_selection": {}}
        if cv is not None:
            overrides["model_selection"]["cv"] = cv
        if model_type is not None:
            overrides["model_selection"]["model_type"] = model_type
    ml = Phronesis(path, config=config, agent_overrides=overrides)
    await _run_stages_async(ml, _STAGES_SELECT_MODEL)
    return ml._predict_ready(data, already_engineered=already_engineered)


# ── Extended API: model comparison ────────────────────────────────


def compare(
    path: str,
    model_types: list[str] | None = None,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
) -> ModelComparison:
    """Train several models on a dataset and rank them.

    The recommended baseline model is included automatically.  Each
    additional model is trained through the same resource-bounded HPO,
    then all models are ranked by the task's primary metric.

    Args:
        path: Path to a data file.
        model_types: Names of models to compare.  ``None`` compares
            every model in the recommended candidate pool.
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        variance_threshold: Drop features with variance below this.
        correlation_threshold: Drop features with target correlation below this.
        min_features: Minimum number of features to retain.
        cv: Number of cross-validation folds.  ``None`` uses a single
            train/test split.

    Returns:
        A ``ModelComparison`` with a best-first ``ranking``.

    Example::

        from phronesisml import compare

        result = compare("data.csv", ["random_forest", "logistic_regression"])
        print(result.best_model)
    """
    return _run_sync(
        compare_async(
            path,
            model_types,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
            cv=cv,
        )
    )


async def compare_async(
    path: str,
    model_types: list[str] | None = None,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
) -> ModelComparison:
    """Async variant of :func:`compare`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
    )
    overrides: dict[str, dict[str, Any]] | None = None
    if cv is not None:
        overrides = {"model_selection": {"cv": cv}}
    ml = Phronesis(path, config=config, agent_overrides=overrides)
    await _run_stages_async(ml, _STAGES_SELECT_MODEL)
    return await ml._compare_core(model_types)


# ── Extended API: persistence ─────────────────────────────────────


def save(
    path: str,
    directory: str | None = None,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
    model_type: str | None = None,
) -> dict[str, Any]:
    """Run the full pipeline and persist the artifact suite.

    Runs every stage through storage, then writes the standard artifact
    set (including the trained model) to ``<directory>/<run_id>/``.

    Args:
        path: Path to a data file.
        directory: Base directory for artifacts.  ``None`` uses the
            pipeline default (``./Phronesis_artifacts/<run_id>/``).
        engine: Force a specific engine. ``None`` for auto-selection.
        null_strategy: Null handling strategy. Default ``"drop"``.
        variance_threshold: Drop features with variance below this.
        correlation_threshold: Drop features with target correlation below this.
        min_features: Minimum number of features to retain.
        cv: Number of cross-validation folds.  ``None`` uses a single
            train/test split.
        model_type: Optional name of a specific model to train.

    Returns:
        A dict with ``artifact_uri``, ``saved_files``, and ``warnings``.

    Example::

        from phronesisml import save, restore

        info = save("data.csv", "saved_runs")
        restored = restore(info["artifact_uri"])
        print(restored.predict(new_rows))
    """
    return _run_sync(
        save_async(
            path,
            directory,
            engine=engine,
            null_strategy=null_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            min_features=min_features,
            cv=cv,
            model_type=model_type,
        )
    )


async def save_async(
    path: str,
    directory: str | None = None,
    *,
    engine: str | None = None,
    null_strategy: str = "drop",
    variance_threshold: float = 0.01,
    correlation_threshold: float = 0.05,
    min_features: int = 1,
    cv: int | None = None,
    model_type: str | None = None,
) -> dict[str, Any]:
    """Async variant of :func:`save`."""
    from phronesisml.sdk import Phronesis

    config = _build_config(
        engine=engine,
        null_strategy=null_strategy,
        variance_threshold=variance_threshold,
        correlation_threshold=correlation_threshold,
        min_features=min_features,
    )
    overrides: dict[str, dict[str, Any]] | None = None
    if cv is not None or model_type is not None:
        overrides = {"model_selection": {}}
        if cv is not None:
            overrides["model_selection"]["cv"] = cv
        if model_type is not None:
            overrides["model_selection"]["model_type"] = model_type
    ml = Phronesis(path, config=config, agent_overrides=overrides)
    await _run_stages_async(ml, _STAGES_TRAIN)
    return ml._save_ready(directory)


def restore(directory: str) -> SavedRun:
    """Restore a saved run for offline prediction.

    Args:
        directory: The artifact directory produced by :func:`save` or
            ``Phronesis.save``.

    Returns:
        A ``SavedRun`` with a ``predict()`` method and run metadata.

    Example::

        from phronesisml import restore

        run = restore("saved_runs/run_abc")
        predictions = run.predict(new_rows)
    """
    return _run_sync(restore_async(directory))


async def restore_async(directory: str) -> SavedRun:
    """Async variant of :func:`restore`."""
    from phronesisml.sdk import Phronesis

    return Phronesis.restore(directory)


# ── Extended API: introspection ───────────────────────────────────


def version() -> str:
    """Return the installed ``phronesisml`` version.

    Example::

        from phronesisml import version

        print(version())
    """
    from phronesisml.sdk import Phronesis

    return Phronesis("").version()


async def version_async() -> str:
    """Async variant of :func:`version`."""
    return version()


def capabilities() -> dict[str, Any]:
    """Report the SDK's capabilities: engines, tasks, stages, APIs.

    Deterministic and offline — the same information surfaced by
    ``phronesisml capabilities``.

    Example::

        from phronesisml import capabilities

        info = capabilities()
        print(info["version"])
    """
    from phronesisml.sdk import Phronesis

    return Phronesis("").capabilities()


async def capabilities_async() -> dict[str, Any]:
    """Async variant of :func:`capabilities`."""
    return capabilities()


def health() -> dict[str, Any]:
    """Run offline dependency and self checks.

    Example::

        from phronesisml import health

        report = health()
        print(report["status"])
    """
    from phronesisml.sdk import Phronesis

    return Phronesis("").health()


async def health_async() -> dict[str, Any]:
    """Async variant of :func:`health`."""
    return health()
