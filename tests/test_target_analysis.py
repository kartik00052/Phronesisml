"""Tests for target analysis (``phronesisml.ml.target_detection.analysis``)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from phronesisml.ml.target_detection.analysis import (
    class_balance_report,
    target_quality_report,
)


@pytest.fixture()
def balanced_df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "age": rng.integers(18, 80, 200),
            "score": rng.normal(50, 10, 200),
            "label": ["A", "B"] * 100,
            "value": rng.normal(0, 1, 200),
        }
    )


def test_class_balance_balanced(balanced_df: pd.DataFrame) -> None:
    report = class_balance_report(balanced_df, "label")
    assert report["kind"] == "categorical"
    assert report["n_classes"] == 2
    assert report["severity"] == "balanced"
    assert report["class_counts"] == {"A": 100, "B": 100}


def test_class_balance_imbalanced() -> None:
    df = pd.DataFrame({"label": ["A"] * 190 + ["B"] * 10})
    report = class_balance_report(df, "label")
    assert report["severity"] == "moderate_imbalance"
    assert report["minority_ratio"] == pytest.approx(0.05, abs=0.001)


def test_class_balance_severe() -> None:
    df = pd.DataFrame({"label": ["A"] * 999 + ["B"]})
    report = class_balance_report(df, "label")
    assert report["severity"] == "severe_imbalance"
    assert report["min_samples_per_class"] == 1


def test_class_balance_numeric_high_cardinality(balanced_df: pd.DataFrame) -> None:
    report = class_balance_report(balanced_df, "score")
    assert report["kind"] == "numeric"
    assert report["severity"] == "n/a"


def test_target_quality_report_classification(balanced_df: pd.DataFrame) -> None:
    report = target_quality_report(balanced_df, "label", task_type="classification")
    assert report["passed"] is True
    assert report["task_type"] == "classification"
    assert report["details"]["class_balance"]["severity"] == "balanced"


def test_target_quality_report_regression(balanced_df: pd.DataFrame) -> None:
    report = target_quality_report(balanced_df, "value", task_type="regression")
    assert report["passed"] is True
    assert report["details"]["distribution"]["unique_values"] > 20


def test_target_quality_report_infers_task(balanced_df: pd.DataFrame) -> None:
    numeric = target_quality_report(balanced_df, "value")
    assert numeric["task_type"] == "regression"
    categorical = target_quality_report(balanced_df, "label")
    assert categorical["task_type"] == "classification"


def test_target_quality_report_imbalance_recommendation() -> None:
    df = pd.DataFrame({"label": ["A"] * 190 + ["B"] * 10})
    report = target_quality_report(df, "label", task_type="classification")
    assert report["passed"] is True
    assert any("imbalance" in r for r in report["recommendations"])


def test_target_quality_report_severe_imbalance_fails() -> None:
    df = pd.DataFrame({"label": ["A"] * 999 + ["B"]})
    report = target_quality_report(df, "label", task_type="classification")
    assert report["passed"] is False
    assert any("imbalance" in v for v in report["violations"])
