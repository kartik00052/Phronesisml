"""Task detection — unified ML problem identification.

Extends the original target detection to also identify unsupervised
learning opportunities (clustering, anomaly detection, analytics-only).

Detection pipeline:
1. Attempt supervised target detection (classification/regression).
2. If no viable target found, evaluate unsupervised task suitability:
   a. Anomaly detection: if dataset has outlier-susceptible features.
   b. Clustering: if dataset has numeric features with varied distributions.
   c. Analytics-only: fallback for datasets with no ML-suited structure.

Each detected task includes a confidence score and reasoning.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.engines.base_engine import NUMERIC_DTYPES, BaseEngine

logger = logging.getLogger(__name__)

# Task type constants
TASK_CLASSIFICATION = "classification"
TASK_REGRESSION = "regression"
TASK_CLUSTERING = "clustering"
TASK_ANOMALY = "anomaly_detection"
TASK_ANALYTICS = "analytics"
TASK_AMBIGUOUS = "ambiguous"

# Confidence thresholds
UNSUPERVISED_MIN_CONFIDENCE = 0.4


def detect_task(
    df: Any,
    engine: BaseEngine,
    data_profile: dict[str, Any],
    *,
    force_task: str | None = None,
) -> dict[str, Any]:
    """Detect the ML task type for a dataset.

    First attempts supervised detection (classification/regression).
    If no viable target is found, evaluates unsupervised tasks.

    Args:
        df: Engine-native DataFrame.
        engine: The active computation engine.
        data_profile: The EDA profile dict.
        force_task: Optional user override.  One of:
            "classification", "regression", "clustering",
            "anomaly_detection", "analytics".

    Returns:
        A dict with keys: ``task_type``, ``target_column``,
        ``confidence``, ``ambiguity_reason``, ``candidates``,
        ``unsupervised_metrics`` (populated if unsupervised).
    """
    if force_task:
        return _force_task_result(force_task)

    # Step 1: Try supervised detection
    supervised = _detect_supervised(df, engine, data_profile)
    if supervised["task_type"] in (TASK_CLASSIFICATION, TASK_REGRESSION):
        return supervised
    if supervised["task_type"] == TASK_AMBIGUOUS:
        return supervised

    # Step 2: No viable target — evaluate unsupervised
    unsupervised = _detect_unsupervised(df, engine, data_profile)

    # Merge results: best unsupervised task
    if unsupervised["task_type"] is not None:
        logger.info(
            "Unsupervised task detected: %s (confidence=%.2f)",
            unsupervised["task_type"],
            unsupervised["confidence"],
        )
        return unsupervised

    # Step 3: Fallback — analytics only
    logger.info("No ML task detected — analytics-only mode.")
    return {
        "task_type": TASK_ANALYTICS,
        "target_column": None,
        "confidence": 0.5,
        "ambiguity_reason": None,
        "candidates": [],
        "unsupervised_metrics": None,
    }


def _force_task_result(force_task: str) -> dict[str, Any]:
    """Return a result for a user-forced task type."""
    valid_tasks = {
        TASK_CLASSIFICATION,
        TASK_REGRESSION,
        TASK_CLUSTERING,
        TASK_ANOMALY,
        TASK_ANALYTICS,
    }
    if force_task not in valid_tasks:
        raise ValueError(f"Invalid task type: {force_task!r}. Valid: {sorted(valid_tasks)}")
    return {
        "task_type": force_task,
        "target_column": None,  # will be set by caller if supervised
        "confidence": 1.0,
        "ambiguity_reason": None,
        "candidates": [],
        "unsupervised_metrics": None,
    }


def _detect_supervised(
    df: Any,
    engine: BaseEngine,
    data_profile: dict[str, Any],
) -> dict[str, Any]:
    """Attempt supervised target detection (classification/regression)."""
    from phronesisml.ml.target_detection.detector import detect_target

    result = detect_target(df, engine, data_profile)
    return {
        "task_type": result["task_type"],
        "target_column": result["target_column"],
        "confidence": result["confidence"],
        "ambiguity_reason": result.get("ambiguity_reason"),
        "candidates": result.get("candidates", []),
        "unsupervised_metrics": None,
    }


def _detect_unsupervised(
    df: Any,
    engine: BaseEngine,
    data_profile: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate unsupervised learning task suitability."""
    collected = engine.cached_collect(df)
    dtypes = engine.dtypes(df)
    n_rows, n_cols = collected.shape

    # Find numeric columns
    numeric_cols = [c for c in engine.columns(df) if dtypes.get(c, "") in NUMERIC_DTYPES]

    # Try anomaly detection first (more specific)
    anomaly_result = _score_anomaly(collected, numeric_cols, n_rows, n_cols)
    if anomaly_result["confidence"] >= UNSUPERVISED_MIN_CONFIDENCE:
        return anomaly_result

    # Try clustering
    clustering_result = _score_clustering(collected, numeric_cols, n_rows, n_cols)
    if clustering_result["confidence"] >= UNSUPERVISED_MIN_CONFIDENCE:
        return clustering_result

    # Nothing suitable
    return {
        "task_type": None,
        "target_column": None,
        "confidence": 0.0,
        "ambiguity_reason": None,
        "candidates": [],
        "unsupervised_metrics": None,
    }


def _score_anomaly(
    collected: Any,
    numeric_cols: list[str],
    n_rows: int,
    n_cols: int,
) -> dict[str, Any]:
    """Score dataset suitability for anomaly detection.

    Heuristics:
    - At least 3 numeric features.
    - At least 50 rows.
    - Some variance in numeric features (not all constant).
    """
    if len(numeric_cols) < 3 or n_rows < 50:
        return _no_unsupervised_task()

    # Check variance — at least some features should have meaningful variance
    variances = collected[numeric_cols].var()
    high_var_count = sum(1 for v in variances if v > 0.01)
    if high_var_count < 2:
        return _no_unsupervised_task()

    confidence = 0.5
    # Bonus: high feature-to-sample ratio suggests anomaly detection is useful
    if n_cols > n_rows * 0.1:
        confidence += 0.1
    # Bonus: more numeric features increase confidence
    if len(numeric_cols) >= 5:
        confidence += 0.1

    confidence = min(1.0, confidence)

    return {
        "task_type": TASK_ANOMALY,
        "target_column": None,
        "confidence": confidence,
        "ambiguity_reason": None,
        "candidates": [],
        "unsupervised_metrics": None,
    }


def _score_clustering(
    collected: Any,
    numeric_cols: list[str],
    n_rows: int,
    n_cols: int,
) -> dict[str, Any]:
    """Score dataset suitability for clustering.

    Heuristics:
    - At least 2 numeric features.
    - At least 30 rows.
    - Some variance in numeric features.
    """
    if len(numeric_cols) < 2 or n_rows < 30:
        return _no_unsupervised_task()

    variances = collected[numeric_cols].var()
    high_var_count = sum(1 for v in variances if v > 0.01)
    if high_var_count < 2:
        return _no_unsupervised_task()

    confidence = 0.45
    # Bonus: moderate row count is good for clustering
    if 100 <= n_rows <= 10000:
        confidence += 0.1
    # Bonus: more numeric features
    if len(numeric_cols) >= 4:
        confidence += 0.1

    confidence = min(1.0, confidence)

    return {
        "task_type": TASK_CLUSTERING,
        "target_column": None,
        "confidence": confidence,
        "ambiguity_reason": None,
        "candidates": [],
        "unsupervised_metrics": None,
    }


def _no_unsupervised_task() -> dict[str, Any]:
    return {
        "task_type": None,
        "target_column": None,
        "confidence": 0.0,
        "ambiguity_reason": None,
        "candidates": [],
        "unsupervised_metrics": None,
    }
