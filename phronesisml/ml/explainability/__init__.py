"""Explainability — SHAP-based model interpretation with resource bounds.

Public API:
    - ``compute_shap_explanations()``: resource-bounded SHAP feature importance.
    - ``DEFAULT_MAX_SAMPLES``: default resource bound for SHAP computation.
    - ``explanation_summary()`` / ``validate_explanation()``: engine-light
      summarizers for explanation results.
"""

from phronesisml.ml.explainability.service import compute_explanations
from phronesisml.ml.explainability.shap_explainer import (
    DEFAULT_MAX_SAMPLES,
    compute_shap_explanations,
)
from phronesisml.ml.explainability.summary import (
    explanation_summary,
    validate_explanation,
)

__all__ = [
    "DEFAULT_MAX_SAMPLES",
    "compute_explanations",
    "compute_shap_explanations",
    "explanation_summary",
    "validate_explanation",
]
