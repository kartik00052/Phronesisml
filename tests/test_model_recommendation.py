"""Tests for model recommendation report (``ml.automl.build_recommendation_report``)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from phronesisml.ml.automl import CandidateModel, build_recommendation_report, recommend_models


@pytest.fixture()
def df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "a": rng.normal(0, 1, 500),
            "b": rng.normal(0, 1, 500),
            "cat": ["x", "y"] * 250,
            "label": [0, 1] * 250,
        }
    )


def test_build_recommendation_report_classification(df: pd.DataFrame) -> None:
    report = build_recommendation_report(df, "classification", target_column="label")
    assert report["task_type"] == "classification"
    assert report["n_rows"] == 500
    assert report["n_features"] == 3
    assert report["n_numeric_features"] == 2
    assert report["n_categorical_features"] == 1
    assert report["cost"] in ("low", "medium", "high")
    assert report["candidates"][0]["name"] == "logistic_regression"


def test_build_recommendation_report_regression(df: pd.DataFrame) -> None:
    report = build_recommendation_report(df, "regression", target_column="label")
    assert report["candidates"][0]["name"] == "linear_regression"


def test_build_recommendation_report_serializable(df: pd.DataFrame) -> None:
    report = build_recommendation_report(df, "classification", target_column="label")
    import json

    dumped = json.dumps(report)
    assert '"logistic_regression"' in dumped


def test_recommend_models_returns_candidates(df: pd.DataFrame) -> None:
    candidates = recommend_models(
        task_type="classification",
        n_rows=500,
        n_features=3,
        n_numeric_features=2,
        n_categorical_features=1,
    )
    assert isinstance(candidates, list)
    assert all(isinstance(c, CandidateModel) for c in candidates)
    assert candidates[0].name == "logistic_regression"
