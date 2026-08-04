"""Target analysis — engine-light quality and balance reports.

Complementary to the heuristic detectors (``detector.detect_target``,
``task_detection.detector.detect_task``): these functions inspect a
*known* target column and produce actionable reports.  They are pure,
deterministic, offline, and return JSON-able dicts.

- ``class_balance_report``: classification class counts / imbalance
- ``target_quality_report``: combined validation + distribution +
  balance + handling recommendations for a known target
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from phronesisml.data.validation import (
    validate_missing_values,
    validate_target_column,
)
from phronesisml.ml.automl.auto_selector import MAX_CLASSIFICATION_UNIQUE_VALUES
from phronesisml.utils.dtypes import NUMERIC_DTYPES

logger = logging.getLogger(__name__)

# Minority-class ratio below this is flagged as "severe" imbalance.
_SEVERE_IMBALANCE_RATIO = 0.01

# Minority-class ratio below this is flagged as "moderate" imbalance.
_MODERATE_IMBALANCE_RATIO = 0.05

# Recommended minimum samples per class for reliable classification.
_MIN_SAMPLES_PER_CLASS = 30


def class_balance_report(
    df: pd.DataFrame,
    target_column: str,
) -> dict[str, Any]:
    """Analyse class balance for a classification target.

    Args:
        df: Input DataFrame.
        target_column: Categorical target column.

    Returns:
        A dict with ``kind`` (``"categorical"``/``"numeric"``),
        ``n_classes``, ``class_counts``, ``class_fractions``,
        ``majority_ratio``, ``minority_ratio``, and ``severity``
        (``"balanced"`` / ``"moderate_imbalance"`` /
        ``"severe_imbalance"`` / ``"n/a"``).
    """
    series = df[target_column].dropna()
    if not len(series):
        return {
            "kind": "n/a",
            "severity": "n/a",
            "reason": f"Target column '{target_column}' is empty.",
        }

    if pd.api.types.is_numeric_dtype(series):
        counts = series.value_counts()
        if len(counts) > 100:
            return {
                "kind": "numeric",
                "severity": "n/a",
                "reason": "High-cardinality numeric target — balance analysis is not meaningful.",
            }
        kind = "numeric"
    else:
        counts = series.value_counts()
        kind = "categorical"

    counts = counts.sort_values(ascending=False)
    class_counts = {str(k): int(v) for k, v in counts.items()}
    total = int(series.shape[0])
    fractions = {str(k): round(v / total, 4) for k, v in counts.items()}

    majority_ratio = fractions[class_counts and next(iter(class_counts))]
    minority_ratio = min(fractions.values())

    if minority_ratio <= _SEVERE_IMBALANCE_RATIO:
        severity = "severe_imbalance"
    elif minority_ratio <= _MODERATE_IMBALANCE_RATIO:
        severity = "moderate_imbalance"
    else:
        severity = "balanced"

    return {
        "kind": kind,
        "n_classes": int(len(counts)),
        "class_counts": class_counts,
        "class_fractions": fractions,
        "majority_ratio": round(majority_ratio, 4),
        "minority_ratio": round(minority_ratio, 4),
        "severity": severity,
        "min_samples_per_class": int(min(counts.values)),
        "below_min_samples": int((counts < _MIN_SAMPLES_PER_CLASS).sum()),
    }


def target_quality_report(
    df: pd.DataFrame,
    target_column: str,
    task_type: str | None = None,
) -> dict[str, Any]:
    """Produce a combined quality report for a known target column.

    Combines structural validation, missing-value stats, distribution,
    and (for classification) class-balance analysis into one report with
    actionable recommendations.

    Args:
        df: Input DataFrame.
        target_column: The target column to analyse.
        task_type: Optional task hint (``"classification"``,
            ``"regression"``).  When ``None``, inferred from the target
            column's dtype / cardinality.

    Returns:
        A dict with ``passed``, ``violations``, ``recommendations``,
        and per-aspect ``details``.
    """
    series = df[target_column]
    n_unique = int(series.nunique(dropna=True))
    is_numeric = str(series.dtype) in NUMERIC_DTYPES

    if task_type is None:
        task_type = (
            "regression"
            if is_numeric and n_unique > MAX_CLASSIFICATION_UNIQUE_VALUES
            else "classification"
        )

    validation = validate_target_column(df, target_column, task_type)
    missing = validate_missing_values(df, max_fraction=1.0, columns=[target_column])
    distribution: dict[str, Any] = {
        "dtype": str(series.dtype),
        "unique_values": n_unique,
        "null_count": int(series.isnull().sum()),
    }
    if is_numeric:
        distribution["min"] = float(series.min()) if series.notna().any() else None
        distribution["max"] = float(series.max()) if series.notna().any() else None
        distribution["mean"] = float(series.mean()) if series.notna().any() else None

    balance: dict[str, Any] | None = None
    if task_type == "classification":
        balance = class_balance_report(df, target_column)

    violations: list[str] = list(validation["violations"])
    recommendations: list[str] = []

    if task_type == "classification" and balance is not None:
        if balance["severity"] == "severe_imbalance":
            violations.append(
                f"Severe class imbalance: minority class is "
                f"{balance['minority_ratio']:.2%} of samples."
            )
            recommendations.append(
                "Consider class_weight='balanced', SMOTE-style resampling, "
                "or a minority-aware metric (precision/recall/F1) for evaluation."
            )
        elif balance["severity"] == "moderate_imbalance":
            recommendations.append(
                "Moderate class imbalance detected — prefer evaluation metrics "
                "that are not accuracy-only (F1 / ROC-AUC)."
            )
        if balance["below_min_samples"] > 0:
            recommendations.append(
                f"{balance['below_min_samples']} class(es) have fewer than "
                f"{_MIN_SAMPLES_PER_CLASS} samples; consider collecting more "
                "data or reducing class count."
            )

    if missing["missing_fraction"][target_column] > 0:
        recommendations.append(
            "Target contains missing values — decide whether to drop those rows "
            "or fill before training."
        )

    return {
        "target_column": target_column,
        "task_type": task_type,
        "passed": not violations,
        "violations": violations,
        "recommendations": recommendations,
        "details": {
            "validation": validation,
            "distribution": distribution,
            "class_balance": balance,
        },
    }
