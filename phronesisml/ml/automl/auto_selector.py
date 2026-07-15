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

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


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
