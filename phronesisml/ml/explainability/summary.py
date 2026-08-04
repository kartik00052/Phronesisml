"""Explanation summarization — engine-light helpers for SHAP results.

Complements the explainability service (``compute_explanations``) with
pure functions that turn raw explanation dicts into concise, reportable
summaries and validation verdicts:

- ``explanation_summary``: top-N features + importance totals
- ``validate_explanation``: structural sanity check of a result dict

The helpers accept the canonical service output (``feature_importance``
mapping, ``explainer_type``, ``sampled``, ``n_samples_used``,
``n_features_used``, ``max_samples``) and remain tolerant of the legacy
explicit-shape keys (``feature_names``, ``explainer``, ``status``).
"""

from __future__ import annotations

from typing import Any


def validate_explanation(explanation: dict[str, Any] | None) -> dict[str, Any]:
    """Validate the structure of an explanation result dict.

    Args:
        explanation: Result dict produced by the explainability service
            (or ``None`` if computation failed).

    Returns:
        A dict with ``valid`` (bool) and ``issues`` (list of strings).
    """
    issues: list[str] = []
    if explanation is None:
        return {"valid": False, "issues": ["Explanation result is None."]}

    feature_importance = explanation.get("feature_importance")
    if feature_importance is None:
        issues.append("Missing expected key: 'feature_importance'.")
    elif not isinstance(feature_importance, dict) or not feature_importance:
        issues.append("feature_importance is missing or empty.")

    feature_names = explanation.get("feature_names")
    if feature_names is None and not explanation.get("feature_importance"):
        issues.append("No feature names available (feature_names or feature_importance required).")

    explainer = explanation.get("explainer") or explanation.get("explainer_type")
    if explainer is None:
        issues.append("Missing expected key: 'explainer' or 'explainer_type'.")

    status = explanation.get("status")
    if status and str(status).lower() not in ("ok", "success", "complete"):
        issues.append(f"Explanation status is not successful: {status!r}.")

    return {"valid": not issues, "issues": issues}


def explanation_summary(
    explanation: dict[str, Any],
    top_n: int = 10,
) -> dict[str, Any]:
    """Summarise an explanation result for a report.

    Args:
        explanation: Result dict produced by the explainability service.
        top_n: Number of top features to include.

    Returns:
        A dict with ``valid``, ``explainer``, ``n_features``, ``top_features``
        (list of ``{"feature", "importance", "rank"}``, best first), and
        ``status``.
    """
    validation = validate_explanation(explanation)
    importance: dict[str, Any] = explanation.get("feature_importance", {}) or {}
    feature_names = explanation.get("feature_names")
    if not feature_names:
        feature_names = list(importance.keys())

    ranked: list[tuple[float, str]] = []
    for name in feature_names:
        value = importance.get(name)
        if value is None:
            continue
        try:
            ranked.append((float(value), str(name)))
        except (TypeError, ValueError):
            continue
    ranked.sort(reverse=True)

    top_features = [
        {"feature": name, "importance": round(value, 6), "rank": i + 1}
        for i, (value, name) in enumerate(ranked[:top_n])
    ]

    return {
        "valid": validation["valid"],
        "issues": validation["issues"],
        "explainer": explanation.get("explainer") or explanation.get("explainer_type"),
        "status": explanation.get("status"),
        "n_features": len(feature_names),
        "n_features_with_importance": len(ranked),
        "top_features": top_features,
    }
