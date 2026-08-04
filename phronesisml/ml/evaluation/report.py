"""Evaluation reporting — thin helpers on top of ``evaluate_model``.

- ``metric_summary``: flatten a metrics dict into a ranked, human-readable
  summary with a primary metric highlighted.
- ``compare_models``: evaluate several trained models on the same data and
  rank them by a chosen primary metric.
"""

from __future__ import annotations

from typing import Any

# Preferred primary metric per task type (in order of preference).
_PRIMARY_METRICS: dict[str, tuple[str, ...]] = {
    "classification": ("f1_weighted", "f1", "roc_auc", "accuracy"),
    "regression": ("r2", "rmse", "mae"),
    "clustering": ("silhouette_score",),
    "anomaly_detection": ("f1", "precision"),
}

# Metrics that are "higher is better".
_HIGHER_IS_BETTER: frozenset[str] = frozenset(
    {
        "accuracy",
        "f1",
        "f1_weighted",
        "f1_macro",
        "f1_micro",
        "precision",
        "recall",
        "r2",
        "roc_auc",
        "silhouette_score",
        "adjusted_rand_score",
        "v_measure",
    }
)

# Metrics that are "lower is better".
_LOWER_IS_BETTER: frozenset[str] = frozenset(
    {"rmse", "mse", "mae", "mape", "log_loss", "brier_score", "davies_bouldin_score"}
)


def metric_summary(metrics: dict[str, Any], task_type: str = "classification") -> dict[str, Any]:
    """Summarise a metrics dict with a selected primary metric.

    Args:
        metrics: Metrics dict produced by ``evaluate_model``.
        task_type: Task type to select the primary metric.

    Returns:
        A dict with ``task_type``, ``primary_metric`` (name), and
        ``primary_value`` plus ``all_metrics`` (sorted best-first).
    """
    candidates = _PRIMARY_METRICS.get(task_type, ())
    primary: str | None = None
    for candidate in candidates:
        if candidate in metrics and metrics[candidate] is not None:
            primary = candidate
            break
    if primary is None and metrics:
        primary = next(iter(metrics))

    primary_value = metrics.get(primary) if primary else None

    def _key(item: tuple[str, Any]) -> float:
        name, value = item
        if value is None:
            return float("-inf")
        try:
            value = float(value)
        except (TypeError, ValueError):
            return float("-inf")
        if name in _LOWER_IS_BETTER:
            return -value
        return value

    ranked = sorted(metrics.items(), key=_key, reverse=True)
    return {
        "task_type": task_type,
        "primary_metric": primary,
        "primary_value": primary_value,
        "primary_higher_is_better": primary in _HIGHER_IS_BETTER,
        "all_metrics": [{k: v} for k, v in ranked],
    }


def compare_models(
    evaluations: list[dict[str, Any]],
    task_type: str = "classification",
) -> dict[str, Any]:
    """Rank multiple evaluation reports by a primary metric.

    Args:
        evaluations: List of dicts as returned by ``evaluate_model``.
        task_type: Task type for primary-metric selection.

    Returns:
        A dict with ``task_type``, ``primary_metric``, and ``ranking``
        (list of model name → primary value, best first).
    """
    primary_metric = _PRIMARY_METRICS.get(task_type, ("accuracy",))[0]
    rows: list[dict[str, Any]] = []
    for report in evaluations:
        metrics = report.get("metrics", {})
        model_info = report.get("model_info", {})
        name = model_info.get("name") if isinstance(model_info, dict) else None
        if name is None:
            name = report.get("model", "unnamed_model")
        value = metrics.get(primary_metric)
        try:
            numeric_value = float(value) if value is not None else None
        except (TypeError, ValueError):
            numeric_value = None

        if numeric_value is None:
            sort_value = float("-inf")
        elif primary_metric in _LOWER_IS_BETTER:
            sort_value = -numeric_value
        else:
            sort_value = numeric_value
        rows.append(
            {
                "model": name,
                "primary_metric": primary_metric,
                "value": numeric_value,
                "_sort_value": sort_value,
            }
        )

    rows.sort(key=lambda r: r["_sort_value"], reverse=True)
    rows = [{k: v for k, v in r.items() if k != "_sort_value"} for r in rows]
    return {
        "task_type": task_type,
        "primary_metric": primary_metric,
        "higher_is_better": primary_metric in _HIGHER_IS_BETTER,
        "ranking": rows,
    }
