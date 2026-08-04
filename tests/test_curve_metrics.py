"""Tests for ROC / precision-recall curve metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from phronesisml.ml.evaluation.metrics import evaluate_model


def _make_classification_df(n: int = 200, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = (x1 + x2 + rng.normal(scale=0.5, size=n) > 0).astype(int)
    return pd.DataFrame({"x1": x1, "x2": x2, "y": y})


def test_classification_includes_pr_curve() -> None:
    df = _make_classification_df()
    model = LogisticRegression().fit(df[["x1", "x2"]], df["y"])
    result = evaluate_model(model, df, target_column="y", task_type="classification")

    metrics = result["metrics"]
    assert metrics["precision_recall_curve"] is not None
    curve = metrics["precision_recall_curve"]
    assert len(curve["precision"]) == len(curve["recall"])
    assert metrics["average_precision"] is not None
    assert metrics["roc_curve"] is not None
    assert metrics["roc_auc"] is not None


def test_classification_without_proba_no_crash() -> None:
    df = _make_classification_df()
    model = SVC(gamma="scale").fit(df[["x1", "x2"]], df["y"])
    result = evaluate_model(model, df, target_column="y", task_type="classification")

    metrics = result["metrics"]
    assert metrics["precision_recall_curve"] is None
    assert metrics["average_precision"] is None
    assert metrics["roc_auc"] is not None  # hard-label fallback
    assert metrics["accuracy"] > 0.0


def test_multiclass_skips_curves() -> None:
    rng = np.random.default_rng(0)
    n = 150
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = np.digitize(x1 + x2, bins=[-0.5, 0.5])
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})

    model = LogisticRegression(max_iter=1000).fit(df[["x1", "x2"]], df["y"])
    result = evaluate_model(model, df, target_column="y", task_type="classification")

    metrics = result["metrics"]
    assert metrics["precision_recall_curve"] is None
    assert metrics["confusion_matrix"] is not None
    assert metrics["f1_macro"] is not None


def test_curve_points_are_jsonable() -> None:
    df = _make_classification_df()
    model = LogisticRegression().fit(df[["x1", "x2"]], df["y"])
    result = evaluate_model(model, df, target_column="y", task_type="classification")

    curve = result["metrics"]["roc_curve"]
    assert all(isinstance(v, float) for v in curve["fpr"])
    assert all(isinstance(v, float) for v in curve["tpr"])
