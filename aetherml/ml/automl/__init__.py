"""AutoML — model recommendation and resource-bounded training.

This module provides rule-based model selection and hyperparameter
optimization with enforced resource bounds (``max_trials``,
``max_time_seconds``).

Public API:
    - ``recommend_models()``: rule-based candidate model selection.
    - ``train_models()``: resource-bounded training + HPO.
    - ``CandidateModel``: dataclass for candidate model descriptors.
"""

from aetherml.ml.automl.auto_selector import (
    CandidateModel,
    recommend_models,
)
from aetherml.ml.automl.trainer import train_models

__all__ = [
    "CandidateModel",
    "recommend_models",
    "train_models",
]
