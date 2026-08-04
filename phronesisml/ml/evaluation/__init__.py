"""Evaluation — model scoring with problem-type-appropriate metrics.

Public API:
    - ``evaluate_model()``: compute metrics and build evaluation report.
    - ``metric_summary()``: flatten/summarise a metrics dict.
    - ``compare_models()``: rank multiple model evaluations.
"""

from phronesisml.ml.evaluation.metrics import evaluate_model
from phronesisml.ml.evaluation.report import compare_models, metric_summary

__all__ = ["compare_models", "evaluate_model", "metric_summary"]
