"""Evaluation — model scoring with problem-type-appropriate metrics.

Public API:
    - ``evaluate_model()``: compute metrics and build evaluation report.
"""

from aetherml.ml.evaluation.metrics import evaluate_model

__all__ = ["evaluate_model"]
