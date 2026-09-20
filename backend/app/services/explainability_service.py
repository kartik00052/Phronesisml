"""Explainability service — SHAP summary served purely from the shap.json artifact.

Beeswarm coordinates and per-row samples are intentionally NOT fabricated:
when they are absent from the artifact they are omitted, and the frontend
renders the honest empty state.  DTO follows ``frontend/src/types/explainability.ts``.
"""

from __future__ import annotations

from typing import Any

from backend.app.db import repositories
from backend.app.services.artifact_service import read_artifact_text


def get(run_id: str) -> dict[str, Any] | None:
    if repositories.get_run(run_id) is None:
        return None
    shap = read_artifact_text(run_id, "shap.json")
    if shap is None:
        return None

    status = str(shap.get("status") or "available")
    if status == "unavailable":
        return None

    report_raw = shap.get("explanation_report") or shap.get("summary") or shap
    feature_importance = report_raw.get("feature_importance") or {}
    if isinstance(feature_importance, dict):
        importance_items = [
            {"feature": str(k), "value": _float(v)}
            for k, v in feature_importance.items()
            if _float(v) is not None
        ]
    else:
        importance_items = [
            {"feature": str(row[0]), "value": _float(row[1])}
            for row in feature_importance
            if isinstance(row, (list, tuple)) and len(row) == 2 and _float(row[1]) is not None
        ]
    importance_items.sort(key=lambda item: item["value"], reverse=True)

    writer_opts = report_raw.get("writer_options") or shap.get("writer_options") or {}
    base_value = writer_opts.get("expected_value")
    if base_value is None:
        base_value = shap.get("expected_value")
    n_samples = report_raw.get("n_samples") or writer_opts.get("n_samples")
    n_features = report_raw.get("n_features") or writer_opts.get("n_features")

    report = {
        "feature_importance": {item["feature"]: item["value"] for item in importance_items},
        "explainer_type": report_raw.get("explainer_type") or shap.get("explainer_type") or "none",
        "sampled": bool(report_raw.get("sampled")),
        "n_samples_used": _int(report_raw.get("n_samples_used")) or n_samples or 0,
        "n_features_used": _int(report_raw.get("n_features_used")) or n_features or 0,
        "max_samples": _int(report_raw.get("max_samples")) or 0,
    }

    return {
        "report": report,
        "importance": importance_items,
        "beeswarm": [],
        "baseValue": _float(base_value) or 0.0,
        "prediction": None,
        "predictionLabel": None,
        "sampleId": 0,
        "samples": None,
    }


def _float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
