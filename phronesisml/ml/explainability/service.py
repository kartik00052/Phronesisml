"""Centralized explainability service for PhronesisML.

Provides a single, production-grade entry point for all SHAP-based model
explainability.  This service is the canonical owner of:

- Explainer routing (Tree → Linear → Permutation → Kernel)
- Wrapped estimator unwrapping (Pipelines, GridSearchCV, etc.)
- Resource management (sampling, background dataset size)
- Deterministic random sampling
- Structured failure handling with actionable diagnostics

Design principles:
- All explainability logic lives here.  Agents, SDK, CLI, and API
  layers delegate to this service — no duplicated business logic.
- The service consumes only standardized inputs (fitted model, feature
  matrix, feature names).  It does not depend on training logic.
- SHAP is a core dependency.  Failures during computation are reported
  with structured diagnostics (not silently swallowed).
- Extensible routing: new explainers can be added by registering a
  predicate + factory pair in ``_EXPLAINER_REGISTRY``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ExplainConfig:
    """Configuration for explainability computation.

    All fields have safe defaults so that callers can use
    ``ExplainConfig()`` without arguments.
    """

    max_samples: int = 100
    """Maximum rows to use for SHAP computation.  Enforced as a hard
    ceiling — if the dataset exceeds this, a random sample is drawn."""

    max_features: int = 50
    """Maximum features to use for SHAP computation.  If the feature
    matrix has more columns, the top features by variance are selected."""

    background_size: int = 100
    """Number of background samples for KernelExplainer."""

    random_seed: int = 42
    """Seed for deterministic random sampling."""

    compute_shap_values: bool = True
    """Whether to compute SHAP values (False = importance only via
    permutation as fallback)."""


# ── Explainer registry ────────────────────────────────────────────


@runtime_checkable
class ExplainerPredicate(Protocol):
    """Protocol for explainer routing predicates."""

    def __call__(self, model: Any, model_info: _ModelInfo) -> bool: ...


@dataclass
class _ModelInfo:
    """Extracted metadata about a model for routing decisions."""

    class_name: str
    class_name_lower: str
    module: str
    has_predict_proba: bool
    has_feature_importances_: bool
    n_features: int


@dataclass
class ExplainerEntry:
    """A registered explainer: predicate + factory + name."""

    name: str
    predicate: Any  # Callable[[Any, _ModelInfo], bool]
    factory: Any  # Callable[[Any, np.ndarray, Any], tuple[str, Any]]


# Registry: order matters — first matching predicate wins.
_EXPLAINER_REGISTRY: list[ExplainerEntry] = []


def register_explainer(
    name: str,
    predicate: Any,
    factory: Any,
) -> None:
    """Register a new explainer in the routing registry.

    Args:
        name: Human-readable name (e.g. ``"TreeExplainer"``).
        predicate: Callable ``(model, model_info) -> bool``.
        factory: Callable ``(model, X, shap) -> (name, explainer)``.

    """
    _EXPLAINER_REGISTRY.append(ExplainerEntry(name=name, predicate=predicate, factory=factory))


def _is_tree_model(model: Any, info: _ModelInfo) -> bool:
    """Check if model is tree-based via class name and API surface."""
    keywords = frozenset(
        {
            "forest",
            "boosting",
            "tree",
            "xgb",
            "lgbm",
            "catboost",
            "extra tree",
            "histgradient",
        }
    )
    if any(kw in info.class_name_lower for kw in keywords):
        return True
    # Heuristic: tree models typically have feature_importances_
    return info.has_feature_importances_ and info.class_name_lower not in {
        "svc",
        "svr",
        "linearsvc",
    }


def _is_linear_model(model: Any, info: _ModelInfo) -> bool:
    """Check if model is linear via class name."""
    keywords = frozenset(
        {
            "linear",
            "logistic",
            "ridge",
            "lasso",
            "elastic",
            "sgd",
            "bayesianridge",
            "ardregression",
            "huber",
            "ransac",
            "theilsen",
        }
    )
    return any(kw in info.class_name_lower for kw in keywords)


def _tree_factory(model: Any, X: np.ndarray[Any, Any], shap: Any) -> tuple[str, Any]:
    """Create a TreeExplainer."""
    return "TreeExplainer", shap.TreeExplainer(model)


def _linear_factory(model: Any, X: np.ndarray[Any, Any], shap: Any) -> tuple[str, Any]:
    """Create a LinearExplainer."""
    return "LinearExplainer", shap.LinearExplainer(model, X)


def _permutation_factory(model: Any, X: np.ndarray[Any, Any], shap: Any) -> tuple[str, Any]:
    """Create a PermutationExplainer (model-agnostic, faster than Kernel)."""
    background_size = min(100, X.shape[0])
    background = X[:background_size]
    return "PermutationExplainer", shap.PermutationExplainer(model.predict, background)


def _kernel_factory(model: Any, X: np.ndarray[Any, Any], shap: Any) -> tuple[str, Any]:
    """Create a KernelExplainer (universal fallback)."""
    background_size = min(100, X.shape[0])
    background = X[:background_size]
    return "KernelExplainer", shap.KernelExplainer(model.predict, background)


# Register default explainers in priority order.
register_explainer("TreeExplainer", _is_tree_model, _tree_factory)
register_explainer("LinearExplainer", _is_linear_model, _linear_factory)
register_explainer("PermutationExplainer", lambda m, i: True, _permutation_factory)
# KernelExplainer is never registered — it's the absolute fallback
# handled explicitly in _select_explainer() if PermutationExplainer fails.


# ── Model unwrapping ─────────────────────────────────────────────


def _unwrap_model(model: Any) -> Any:
    """Recursively unwrap common sklearn wrappers to get the base estimator.

    Handles:
    - ``Pipeline`` → last step estimator
    - ``GridSearchCV`` / ``RandomizedSearchCV`` → ``.best_estimator_``
    - ``VotingClassifier`` / ``VotingRegressor`` → best estimator
    - ``BaggingClassifier`` / ``BaggingRegressor`` → ``.estimator``
    - ``StackingClassifier`` / ``StackingRegressor`` → ``.estimators_``[0]

    Does NOT unwrap:
    - ``CalibratedClassifierCV`` — it's a valid fitted wrapper with its
      own ``predict`` method; SHAP can explain it directly.

    Returns the deepest unwrapped estimator that is NOT itself a wrapper.
    """
    changed = True
    current = model

    while changed:
        changed = False
        class_lower = type(current).__name__.lower()

        # GridSearchCV / RandomizedSearchCV
        if hasattr(current, "best_estimator_"):
            current = current.best_estimator_
            changed = True
            continue

        # Pipeline — return the final estimator
        if hasattr(current, "steps") and hasattr(current, "named_steps"):
            try:
                steps = list(current.steps)
                if steps:
                    current = steps[-1][1]
                    changed = True
                    continue
            except Exception:
                pass

        # VotingClassifier / VotingRegressor — first fitted estimator
        if hasattr(current, "estimators_") and hasattr(current, "voting"):
            try:
                if current.estimators_:
                    first = current.estimators_[0]
                    current = first[1] if isinstance(first, tuple) else first
                    changed = True
                    continue
            except Exception:
                pass

        # Bagging — unwrap the base estimator (only if it's a bagging type)
        if (
            hasattr(current, "estimator")
            and not hasattr(current, "estimators_")
            and class_lower.startswith("bagging")
        ):
            current = current.estimator
            changed = True
            continue

        # Stacking — first estimator
        if (
            hasattr(current, "estimators_")
            and isinstance(current.estimators_, list)
            and class_lower.startswith("stacking")
            and current.estimators_
        ):
            first = current.estimators_[0]
            current = first[1] if isinstance(first, tuple) else first
            changed = True
            continue

    return current


def _extract_model_info(model: Any) -> _ModelInfo:
    """Extract metadata about a model for routing decisions."""
    return _ModelInfo(
        class_name=type(model).__name__,
        class_name_lower=type(model).__name__.lower(),
        module=type(model).__module__,
        has_predict_proba=callable(getattr(model, "predict_proba", None)),
        has_feature_importances_=hasattr(model, "feature_importances_"),
        n_features=getattr(model, "n_features_in_", 0),
    )


# ── Core service ──────────────────────────────────────────────────


def compute_explanations(
    model: Any,
    X: np.ndarray[Any, Any],
    feature_names: list[str],
    config: ExplainConfig | None = None,
) -> dict[str, Any]:
    """Compute SHAP-based feature importance explanations.

    This is the single entry point for all explainability logic.
    All other layers (agents, SDK, CLI, API) delegate here.

    Args:
        model: A trained estimator (may be wrapped in Pipeline, etc.).
        X: Feature matrix (n_samples, n_features).
        feature_names: Names of the feature columns.
        config: Optional configuration.  Defaults to ``ExplainConfig()``.

    Returns:
        A dict with keys: ``feature_importance`` (dict mapping feature
        name → mean absolute SHAP value), ``explainer_type`` (str),
        ``sampled`` (bool), ``n_samples_used`` (int),
        ``max_samples`` (int).

    """
    if config is None:
        config = ExplainConfig()

    try:
        import shap  # noqa: F401
    except ImportError as exc:
        msg = (
            "SHAP library is required for explainability but is not installed. "
            "It should be installed as a core dependency — this is an "
            "environment issue.  Install with: pip install phronesisml"
        )
        raise ImportError(msg) from exc

    # ── Validate inputs ─────────────────────────────────────────────
    if X.shape[0] == 0:
        msg = "Cannot explain an empty dataset (0 samples)."
        raise ValueError(msg)
    if X.shape[1] == 0:
        msg = "Cannot explain a model with 0 features."
        raise ValueError(msg)

    # ── Unwrap model ────────────────────────────────────────────────
    base_model = _unwrap_model(model)
    model_info = _extract_model_info(base_model)

    logger.info(
        "Explainability: base model=%s (from %s), features=%d.",
        model_info.class_name,
        type(model).__name__,
        X.shape[1],
    )

    # ── Cap feature dimensions ──────────────────────────────────────
    feature_names_used = list(feature_names)
    if X.shape[1] > config.max_features:
        # Select top features by variance (cheapest proxy for importance)
        variances = np.var(X, axis=0)
        top_indices = np.argsort(variances)[-config.max_features :]
        X = X[:, top_indices]
        feature_names_used = [feature_names[i] for i in top_indices]
        logger.info(
            "Explainability: capped features from %d to %d (by variance).",
            len(feature_names),
            config.max_features,
        )

    # ── Enforce row sampling ────────────────────────────────────────
    sampled = False
    n_rows = X.shape[0]

    if n_rows > config.max_samples:
        rng = np.random.RandomState(config.random_seed)
        indices = rng.choice(n_rows, size=config.max_samples, replace=False)
        X_sample = X[indices]
        sampled = True
        logger.info(
            "Explainability: sampled rows from %d to %d (max_samples=%d).",
            n_rows,
            config.max_samples,
            config.max_samples,
        )
    else:
        X_sample = X

    # ── Select and create explainer ─────────────────────────────────
    explainer_type_name, explainer = _select_explainer(
        base_model, X_sample, model_info, shap, config
    )

    # ── Compute SHAP values ─────────────────────────────────────────
    try:
        shap_values = explainer.shap_values(X_sample)
    except Exception as exc:
        # Fallback: try KernelExplainer if the selected explainer fails
        logger.warning(
            "Explainability: %s failed (%s), falling back to KernelExplainer.",
            explainer_type_name,
            exc,
        )
        fallback_background = X_sample[: min(config.background_size, X_sample.shape[0])]
        explainer_type_name = "KernelExplainer"
        explainer = shap.KernelExplainer(base_model.predict, fallback_background)
        shap_values = explainer.shap_values(X_sample)

    # ── Compute global feature importance ───────────────────────────
    feature_importance = _compute_global_importance(shap_values, feature_names_used)

    logger.info(
        "Explainability complete: explainer=%s, features=%d, sampled=%s.",
        explainer_type_name,
        len(feature_importance),
        sampled,
    )

    return {
        "feature_importance": feature_importance,
        "explainer_type": explainer_type_name,
        "sampled": sampled,
        "n_samples_used": X_sample.shape[0],
        "n_features_used": len(feature_names_used),
        "max_samples": config.max_samples,
    }


def _select_explainer(
    model: Any,
    X: np.ndarray[Any, Any],
    model_info: _ModelInfo,
    shap: Any,
    config: ExplainConfig,
) -> tuple[str, Any]:
    """Select the best SHAP explainer for the given model.

    Priority:
    1. TreeExplainer (exact, fast) — for tree-based models
    2. LinearExplainer (exact) — for linear models
    3. PermutationExplainer (model-agnostic) — for everything else
    4. KernelExplainer (universal fallback) — if PermutationExplainer unavailable

    Returns (explainer_type_name, explainer_instance).
    """
    # Walk the registry in order
    for entry in _EXPLAINER_REGISTRY:
        try:
            if entry.predicate(model, model_info):
                logger.info(
                    "Explainability: using %s for %s.",
                    entry.name,
                    model_info.class_name,
                )
                return entry.factory(model, X, shap)  # type: ignore[no-any-return]
        except Exception as exc:
            logger.debug(
                "Explainability: %s routing failed for %s: %s",
                entry.name,
                model_info.class_name,
                exc,
            )
            continue

    # Absolute fallback: KernelExplainer
    background_size = min(config.background_size, X.shape[0])
    background = X[:background_size]
    logger.info(
        "Explainability: using KernelExplainer for %s (background=%d).",
        model_info.class_name,
        background_size,
    )
    return "KernelExplainer", shap.KernelExplainer(model.predict, background)


def _compute_global_importance(
    shap_values: Any,
    feature_names: list[str],
) -> dict[str, float]:
    """Compute global feature importance as mean absolute SHAP value per feature.

    For multi-class classification, SHAP returns a list of arrays
    (one per class).  We average the absolute values across classes.
    """
    # Handle multi-class: shap_values is a list of arrays
    if isinstance(shap_values, list):
        combined = np.mean([np.abs(sv) for sv in shap_values], axis=0)
    else:
        combined = np.abs(shap_values)

    # Mean across samples
    mean_importance = np.mean(combined, axis=0)

    # If multi-class produced a 2D result (n_features, n_classes), reduce further
    if mean_importance.ndim > 1:
        mean_importance = np.mean(mean_importance, axis=tuple(range(1, mean_importance.ndim)))

    # Map to feature names
    importance_dict = {}
    for i, name in enumerate(feature_names):
        if i < len(mean_importance):
            importance_dict[name] = float(mean_importance[i])

    return importance_dict
