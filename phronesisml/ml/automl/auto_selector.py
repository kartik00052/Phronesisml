"""Rule-based model recommendation from dataset metadata.

Selects a ranked list of candidate models based on the task type
(classification / regression / ambiguous), dataset size, feature count,
and feature types.  This is a deterministic, inspectable heuristic —
no black-box selection.

Candidate sets are intentionally small and explicit per task type.
The caller (``ml.automl.trainer``) evaluates each candidate with
resource-bounded hyperparameter search.

Scalability:
- Recommendation is O(n_columns) — negligible.
- Candidate set size is bounded by design (3-5 models per task type).
- Future: support custom candidate pools via configuration.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Numeric targets with more than this many unique values are treated as
# regression, never classification or ambiguous.  Single source of truth
# shared by target detection, model selection, training, and evaluation —
# this exact boundary was the source of BUG-02 drift; do not reintroduce
# per-module copies.
MAX_CLASSIFICATION_UNIQUE_VALUES = 20


def resolve_task_class(target_values: Any, task_type: str) -> str:
    """Resolve an ``ambiguous`` task type to a concrete task class.

    Explicit ``task_type`` values pass through unchanged.  For
    ``"ambiguous"``, the actual target values decide the class:

    - Non-numeric targets are treated as classification.
    - Numeric targets with more than ``MAX_CLASSIFICATION_UNIQUE_VALUES``
      unique values are regression.
    - Numeric targets within the cardinality window with non-integral
      values are regression (continuous).
    - Everything else is treated as classification.

    This is the selector-side rule (BUG-02 fix) that keeps the candidate
    pool, the scoring metric, and evaluation consistent for continuous
    targets.

    Args:
        target_values: Array-like of target values (e.g. a pandas Series).
        task_type: Recorded task type from Target Detection.

    Returns:
        ``"classification"``, ``"regression"``, or the original value of
        ``task_type`` if it was not ``"ambiguous"``.

    """
    if task_type != "ambiguous":
        return task_type

    try:
        target_series = pd.Series(target_values)
    except Exception:
        return "classification"

    if not pd.api.types.is_numeric_dtype(target_series):
        return "classification"

    unique_target = np.unique(target_series.dropna().to_numpy())
    if len(unique_target) > MAX_CLASSIFICATION_UNIQUE_VALUES:
        return "regression"

    with contextlib.suppress(ValueError, TypeError):
        if not np.all(unique_target == unique_target.astype(int)):
            return "regression"

    return "classification"


@dataclass(frozen=True)
class CandidateModel:
    """A recommended model with its default hyperparameter search space.

    Attributes:
        name: Human-readable model name (e.g. ``"logistic_regression"``).
        estimator_path: Fully-qualified sklearn class path
            (e.g. ``"sklearn.linear_model.LogisticRegression"``).
        param_space: Dict mapping parameter names to lists of values
            to search over.  An empty dict means use sklearn defaults
            with no HPO.
        tags: Free-form metadata (e.g. ``{"linear": True}``).

    """

    name: str
    estimator_path: str
    param_space: dict[str, list[Any]] = field(default_factory=dict)
    tags: dict[str, Any] = field(default_factory=dict)


# ── Classification candidates ──────────────────────────────────────

_CLASSIFICATION_CANDIDATES: list[CandidateModel] = [
    CandidateModel(
        name="logistic_regression",
        estimator_path="sklearn.linear_model.LogisticRegression",
        param_space={
            "C": [0.01, 0.1, 1.0, 10.0, 100.0],
            "max_iter": [200],
        },
        tags={"linear": True, "fast": True},
    ),
    CandidateModel(
        name="random_forest",
        estimator_path="sklearn.ensemble.RandomForestClassifier",
        param_space={
            "n_estimators": [50, 100, 200],
            "max_depth": [None, 5, 10, 20],
            "min_samples_split": [2, 5],
        },
        tags={"ensemble": True, "robust": True},
    ),
    CandidateModel(
        name="gradient_boosting",
        estimator_path="sklearn.ensemble.GradientBoostingClassifier",
        param_space={
            "n_estimators": [50, 100, 200],
            "max_depth": [3, 5, 7],
            "learning_rate": [0.01, 0.1, 0.2],
        },
        tags={"ensemble": True, "high_performance": True},
    ),
]

# ── Regression candidates ──────────────────────────────────────────

_REGRESSION_CANDIDATES: list[CandidateModel] = [
    CandidateModel(
        name="linear_regression",
        estimator_path="sklearn.linear_model.LinearRegression",
        param_space={},
        tags={"linear": True, "fast": True},
    ),
    CandidateModel(
        name="random_forest",
        estimator_path="sklearn.ensemble.RandomForestRegressor",
        param_space={
            "n_estimators": [50, 100, 200],
            "max_depth": [None, 5, 10, 20],
            "min_samples_split": [2, 5],
        },
        tags={"ensemble": True, "robust": True},
    ),
    CandidateModel(
        name="gradient_boosting",
        estimator_path="sklearn.ensemble.GradientBoostingRegressor",
        param_space={
            "n_estimators": [50, 100, 200],
            "max_depth": [3, 5, 7],
            "learning_rate": [0.01, 0.1, 0.2],
        },
        tags={"ensemble": True, "high_performance": True},
    ),
]

# ── Clustering candidates ───────────────────────────────────────

_CLUSTERING_CANDIDATES: list[CandidateModel] = [
    CandidateModel(
        name="kmeans",
        estimator_path="sklearn.cluster.KMeans",
        param_space={
            "n_clusters": [2, 3, 4, 5, 6, 8, 10],
            "n_init": [10],
        },
        tags={"clustering": True, "fast": True},
    ),
    CandidateModel(
        name="agglomerative",
        estimator_path="sklearn.cluster.AgglomerativeClustering",
        param_space={
            "n_clusters": [2, 3, 4, 5, 6, 8, 10],
            "linkage": ["ward", "complete"],
        },
        tags={"clustering": True, "fast": True},
    ),
]

# ── Anomaly detection candidates ─────────────────────────────────

_ANOMALY_CANDIDATES: list[CandidateModel] = [
    CandidateModel(
        name="isolation_forest",
        estimator_path="sklearn.ensemble.IsolationForest",
        param_space={
            "n_estimators": [100, 200],
            "contamination": [0.05, 0.1, 0.15],
        },
        tags={"anomaly": True, "fast": True},
    ),
    CandidateModel(
        name="local_outlier_factor",
        estimator_path="sklearn.neighbors.LocalOutlierFactor",
        param_space={
            "n_neighbors": [10, 20, 30],
            "contamination": [0.05, 0.1, 0.15],
        },
        tags={"anomaly": True, "fast": True},
    ),
]

# ── Ambiguous candidates (superset of both) ────────────────────────

_AMBIGUOUS_CANDIDATES: list[CandidateModel] = [
    CandidateModel(
        name="logistic_regression",
        estimator_path="sklearn.linear_model.LogisticRegression",
        param_space={
            "C": [0.01, 0.1, 1.0, 10.0, 100.0],
            "max_iter": [200],
        },
        tags={"linear": True, "fast": True, "classification": True},
    ),
    CandidateModel(
        name="linear_regression",
        estimator_path="sklearn.linear_model.LinearRegression",
        param_space={},
        tags={"linear": True, "fast": True, "regression": True},
    ),
    CandidateModel(
        name="random_forest",
        estimator_path="sklearn.ensemble.RandomForestClassifier",
        param_space={
            "n_estimators": [50, 100, 200],
            "max_depth": [None, 5, 10, 20],
        },
        tags={"ensemble": True, "classification": True},
    ),
    CandidateModel(
        name="gradient_boosting",
        estimator_path="sklearn.ensemble.GradientBoostingClassifier",
        param_space={
            "n_estimators": [50, 100, 200],
            "max_depth": [3, 5, 7],
            "learning_rate": [0.01, 0.1, 0.2],
        },
        tags={"ensemble": True, "classification": True},
    ),
]


def recommend_models(
    task_type: str | None,
    n_rows: int,
    n_features: int,
    n_numeric_features: int,
    n_categorical_features: int,
) -> list[CandidateModel]:
    """Return a ranked list of candidate models for the given dataset.

    The ranking is based on dataset characteristics:
    - Small datasets (< 1000 rows): prefer simpler, faster models.
    - Large datasets: allow more complex models.
    - Many features: prefer regularised or tree-based models.

    Args:
        task_type: ``"classification"``, ``"regression"``, or
            ``"ambiguous"`` (from Target Detection).
        n_rows: Number of rows in the training data.
        n_features: Total number of feature columns.
        n_numeric_features: Number of numeric feature columns.
        n_categorical_features: Number of categorical feature columns.

    Returns:
        A list of ``CandidateModel`` instances, ordered by estimated
        suitability (best first).

    """
    if task_type == "classification":
        candidates = list(_CLASSIFICATION_CANDIDATES)
    elif task_type == "regression":
        candidates = list(_REGRESSION_CANDIDATES)
    elif task_type == "clustering":
        candidates = list(_CLUSTERING_CANDIDATES)
    elif task_type == "anomaly_detection":
        candidates = list(_ANOMALY_CANDIDATES)
    else:
        # Ambiguous or unknown: try classification candidates first,
        # they'll fail gracefully if the target is truly continuous.
        candidates = list(_AMBIGUOUS_CANDIDATES)

    # Apply dataset-aware re-ranking
    candidates = _rerank_by_dataset(candidates, n_rows, n_features)

    logger.info(
        "Recommended %d candidate models for %s task (%d rows, %d features).",
        len(candidates),
        task_type,
        n_rows,
        n_features,
    )
    return candidates


def _rerank_by_dataset(
    candidates: list[CandidateModel],
    n_rows: int,
    n_features: int,
) -> list[CandidateModel]:
    """Re-rank candidates based on dataset size and dimensionality.

    Heuristics:
    - Very small datasets (< 100 rows): prefer linear models (less
      prone to overfitting).
    - High-dimensional data (features > rows): prefer regularised
      models or tree-based models.
    - Large datasets: no preference change (keep original order).
    """
    scored: list[tuple[float, CandidateModel]] = []

    for c in candidates:
        score = 0.0

        # Small dataset bonus for simple models
        if n_rows < 100 and c.tags.get("fast"):
            score += 0.3

        # High-dimensionality bonus for tree-based / regularised
        if n_features > n_rows and c.tags.get("ensemble"):
            score += 0.2
        if n_features > n_rows and c.tags.get("linear"):
            score += 0.1  # Linear is still ok with regularisation

        scored.append((score, c))

    # Stable sort by score descending, preserving original order on tie
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def candidate_to_dict(candidate: CandidateModel) -> dict[str, Any]:
    """Serialize a CandidateModel to a plain dict for WorkflowState."""
    return {
        "name": candidate.name,
        "estimator_path": candidate.estimator_path,
        "param_space": candidate.param_space,
        "tags": candidate.tags,
    }


def build_recommendation_report(
    df: pd.DataFrame,
    task_type: str,
    target_column: str | None = None,
) -> dict[str, Any]:
    """Produce a JSON-able model recommendation report from a DataFrame.

    Engine-light wrapper over ``recommend_models`` that derives dataset
    characteristics (rows, feature counts) directly from the DataFrame
    and serialises the ranked candidates.

    Args:
        df: Engineered feature DataFrame (engine-light pandas).
        task_type: ``"classification"``, ``"regression"``, ``"clustering"``,
            ``"anomaly_detection"``, or ``"ambiguous"``.
        target_column: Target column to exclude from the feature count.

    Returns:
        A dict with ``task_type``, ``n_rows``, ``n_features``,
        ``n_numeric_features``, ``n_categorical_features``, ``cost``
        (low/medium/high), and ``candidates`` (list of serialized
        ``CandidateModel`` dicts).
    """
    feature_cols = [c for c in df.columns if c != target_column]
    numeric_features = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    categorical_features = [c for c in feature_cols if c not in numeric_features]

    candidates = recommend_models(
        task_type=task_type,
        n_rows=int(df.shape[0]),
        n_features=len(feature_cols),
        n_numeric_features=len(numeric_features),
        n_categorical_features=len(categorical_features),
    )

    return {
        "task_type": task_type,
        "target_column": target_column,
        "n_rows": int(df.shape[0]),
        "n_features": len(feature_cols),
        "n_numeric_features": len(numeric_features),
        "n_categorical_features": len(categorical_features),
        "cost": estimate_training_cost(int(df.shape[0]), len(feature_cols), candidates),
        "candidates": [candidate_to_dict(c) for c in candidates],
    }


def estimate_training_cost(
    n_rows: int,
    n_features: int,
    candidates: list[CandidateModel] | None = None,
) -> str:
    """Estimate training cost as low / medium / high.

    Heuristic: rows × features × candidate_complexity_score.
    - Linear models (fast tag): complexity 1
    - Ensemble models: complexity 3
    - Sum across all candidates weighted by their param_space size.

    Returns one of ``"low"``, ``"medium"``, or ``"high"``.
    """
    if not candidates:
        return "low"

    complexity = 0.0
    for c in candidates:
        base = 1.0 if c.tags.get("fast") else 3.0
        # Larger param spaces mean more HPO trials → higher cost
        param_factor = 1.0 + len(c.param_space) * 0.2
        complexity += base * param_factor

    score = n_rows * n_features * complexity

    if score < 500_000:
        return "low"
    if score < 5_000_000:
        return "medium"
    return "high"
