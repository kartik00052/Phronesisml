"""Feature engineering — transforming validated data into model-ready features.

``ml.feature_engineering.engineer`` contains the full engine-coupled
pipeline (``engineer_features``).  ``ml.feature_engineering.construction``
adds engine-light feature builders (interactions, polynomials, binning,
date extraction, and lightweight selection).
"""

from phronesisml.ml.feature_engineering.construction import (
    bin_continuous_features,
    correlation_feature_selector,
    create_interaction_features,
    create_polynomial_features,
    extract_date_features,
    feature_importance_report,
    variance_threshold_filter,
)
from phronesisml.ml.feature_engineering.engineer import engineer_features

__all__ = [
    "bin_continuous_features",
    "correlation_feature_selector",
    "create_interaction_features",
    "create_polynomial_features",
    "engineer_features",
    "extract_date_features",
    "feature_importance_report",
    "variance_threshold_filter",
]
