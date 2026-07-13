"""Explainability — SHAP-based model interpretation with resource bounds.

Public API:
    - ``compute_shap_explanations()``: resource-bounded SHAP feature importance.
    - ``DEFAULT_MAX_SAMPLES``: default resource bound for SHAP computation.
"""

from phronesisml.ml.explainability.shap_explainer import (
    DEFAULT_MAX_SAMPLES,
    compute_shap_explanations,
)

__all__ = [
    "DEFAULT_MAX_SAMPLES",
    "compute_shap_explanations",
]
