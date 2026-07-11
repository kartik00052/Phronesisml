"""SHAP-based model explainability with resource-bounded computation.

Selects the appropriate SHAP explainer based on model class (tree
explainer for tree-based models, KernelExplainer as fallback for others)
and computes global feature importance via mean absolute SHAP values.

Resource bounds:
- ``max_samples`` (default 100): caps the number of rows used for SHAP
  value computation.  Full-dataset SHAP on non-tree explainers can be
  extremely slow — this prevents resource exhaustion if exposed via API.
- If the dataset exceeds the cap, a random sample is drawn and the
  output flags that explanations are based on a sample, not the full
  dataset.  This is visible in the result, not a silent truncation.

Explainer selection (rule-based):
- Tree-based models (RandomForest, GradientBoosting, XGBoost, etc.):
  ``shap.TreeExplainer`` — exact, fast.
- Linear models (LinearRegression, LogisticRegression, etc.):
  ``shap.LinearExplainer`` — exact for linear models.
- Everything else: ``shap.KernelExplainer`` with a sample-based
  background dataset — approximate but universal.

Scalability:
- TreeExplainer: O(TLD) where T=trees, L=leaves, D=depth — fast.
- LinearExplainer: O(n_features) — fast.
- KernelExplainer: O(n_samples * n_features * n_neighbors) — slow
  for large datasets, hence the ``max_samples`` cap.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Default resource bound for SHAP computation.
DEFAULT_MAX_SAMPLES = 100

# Tree-based model class name prefixes (case-insensitive check).
_TREE_MODEL_KEYWORDS = frozenset(
    {
        "forest",
        "boosting",
        "tree",
        "xgb",
        "lgbm",
        "catboost",
        "extra tree",
    }
)

# Linear model class name prefixes (case-insensitive check).
_LINEAR_MODEL_KEYWORDS = frozenset(
    {
        "linear",
        "logistic",
        "ridge",
        "lasso",
        "elastic",
        "sgd",
    }
)


def compute_shap_explanations(
    model: Any,
    X: np.ndarray[Any, Any],
    feature_names: list[str],
    max_samples: int = DEFAULT_MAX_SAMPLES,
) -> dict[str, Any]:
    """Compute SHAP-based feature importance explanations.

    Args:
        model: A trained sklearn-compatible estimator.
        X: Feature matrix (n_samples, n_features).
        feature_names: Names of the feature columns.
        max_samples: Maximum number of rows to use for SHAP computation.
            Enforced as a hard ceiling — if ``len(X) > max_samples``,
            a random sample is drawn and ``sampled`` is set to ``True``.

    Returns:
        A dict with keys: ``feature_importance`` (dict mapping feature
        name → mean absolute SHAP value), ``explainer_type`` (str),
        ``sampled`` (bool), ``n_samples_used`` (int),
        ``max_samples`` (int).

    """
    try:
        import shap
    except ImportError as exc:
        msg = "SHAP library is required for explainability. Install it with: pip install shap"
        raise ImportError(msg) from exc

    # ── Enforce resource bound ───────────────────────────────────────
    sampled = False
    n_rows = X.shape[0]

    if n_rows > max_samples:
        rng = np.random.RandomState(42)
        indices = rng.choice(n_rows, size=max_samples, replace=False)
        X_sample = X[indices]
        sampled = True
        logger.info(
            "SHAP: sampleddataset from %d to %d rows (max_samples=%d).",
            n_rows,
            max_samples,
            max_samples,
        )
    else:
        X_sample = X

    # ── Select explainer type ────────────────────────────────────────
    explainer_type_name, explainer = _create_explainer(model, X_sample, shap)

    # ── Compute SHAP values ──────────────────────────────────────────
    shap_values = explainer.shap_values(X_sample)

    # ── Compute global feature importance ────────────────────────────
    feature_importance = _compute_global_importance(
        shap_values,
        feature_names,
        model,
    )

    logger.info(
        "SHAP explanations complete: explainer=%s, features=%d, sampled=%s.",
        explainer_type_name,
        len(feature_importance),
        sampled,
    )

    return {
        "feature_importance": feature_importance,
        "explainer_type": explainer_type_name,
        "sampled": sampled,
        "n_samples_used": X_sample.shape[0],
        "max_samples": max_samples,
    }


def _create_explainer(
    model: Any,
    X: np.ndarray[Any, Any],
    shap: Any,
) -> tuple[str, Any]:
    """Create the appropriate SHAP explainer based on model type.

    Returns a tuple of (explainer_type_name, explainer_instance).

    Selection logic (rule-based):
    - Tree-based models → TreeExplainer (exact, fast)
    - Linear models → LinearExplainer (exact for linear)
    - Everything else → KernelExplainer (approximate, universal)
    """
    model_class_name = type(model).__name__.lower()

    # Check for tree-based models
    if any(kw in model_class_name for kw in _TREE_MODEL_KEYWORDS):
        logger.info("SHAP: using TreeExplainer for %s.", type(model).__name__)
        return "TreeExplainer", shap.TreeExplainer(model)

    # Check for linear models
    if any(kw in model_class_name for kw in _LINEAR_MODEL_KEYWORDS):
        logger.info("SHAP: using LinearExplainer for %s.", type(model).__name__)
        return "LinearExplainer", shap.LinearExplainer(model, X)

    # Fallback: KernelExplainer with sample-based background
    background_size = min(100, X.shape[0])
    background = X[:background_size]
    logger.info(
        "SHAP: using KernelExplainer for %s (background=%d).",
        type(model).__name__,
        background_size,
    )
    return "KernelExplainer", shap.KernelExplainer(model.predict, background)


def _compute_global_importance(
    shap_values: Any,
    feature_names: list[str],
    model: Any,
) -> dict[str, float]:
    """Compute global feature importance as mean absolute SHAP value per feature.

    For multi-class classification, SHAP returns a list of arrays
    (one per class).  We average the absolute values across classes.
    """
    # Handle multi-class: shap_values is a list of arrays
    if isinstance(shap_values, list):
        # Average absolute SHAP values across all classes
        combined = np.mean([np.abs(sv) for sv in shap_values], axis=0)
    else:
        combined = np.abs(shap_values)

    # Mean across samples
    mean_importance = np.mean(combined, axis=0)

    # Map to feature names
    importance_dict = {}
    for i, name in enumerate(feature_names):
        if i < len(mean_importance):
            importance_dict[name] = float(mean_importance[i])

    return importance_dict
