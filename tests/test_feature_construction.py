"""Tests for the feature construction toolkit."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from phronesisml.exceptions import DataTransformError
from phronesisml.ml.feature_engineering.construction import (
    bin_continuous_features,
    correlation_feature_selector,
    create_interaction_features,
    create_polynomial_features,
    extract_date_features,
    feature_importance_report,
    variance_threshold_filter,
)


@pytest.fixture()
def df() -> pd.DataFrame:
    rng = np.random.default_rng(4)
    return pd.DataFrame(
        {
            "a": rng.normal(0, 1, 50),
            "b": rng.normal(5, 2, 50),
            "const": np.ones(50),
            "target": rng.normal(0, 1, 50) + rng.normal(0, 1, 50),
            "joined": pd.to_datetime(["2021-06-15"] * 50),
        }
    )


def test_create_interaction_features(df: pd.DataFrame) -> None:
    result, log = create_interaction_features(df, columns=["a", "b"])
    assert "a__b" in result.columns
    assert log["columns_created"] == ["a__b"]
    assert "a" in df.columns  # input untouched


def test_create_interaction_features_all_numeric(df: pd.DataFrame) -> None:
    result, log = create_interaction_features(df)
    assert len(log["columns_created"]) > 1


def test_create_polynomial_features(df: pd.DataFrame) -> None:
    result, log = create_polynomial_features(df, columns=["a"], degree=3)
    assert "a_p2" in result.columns
    assert "a_p3" in result.columns
    assert log["n_features_created"] == 2


def test_create_polynomial_features_bad_degree(df: pd.DataFrame) -> None:
    with pytest.raises(DataTransformError):
        create_polynomial_features(df, columns=["a"], degree=1)


def test_create_polynomial_features_bias(df: pd.DataFrame) -> None:
    result, log = create_polynomial_features(df, columns=["a"], include_bias=True)
    assert "bias" in result.columns
    assert (result["bias"] == 1).all()


def test_bin_continuous_features_quantile(df: pd.DataFrame) -> None:
    result, log = bin_continuous_features(df, columns=["a"], bins=4, strategy="quantile")
    assert "a_bin" in result.columns
    assert result["a_bin"].nunique() == 4
    assert "a" in result.columns  # original kept


def test_bin_continuous_features_uniform(df: pd.DataFrame) -> None:
    result, _ = bin_continuous_features(df, columns=["b"], bins=3, strategy="uniform")
    assert result["b_bin"].nunique() == 3


def test_bin_continuous_features_bad_strategy(df: pd.DataFrame) -> None:
    with pytest.raises(DataTransformError):
        bin_continuous_features(df, columns=["a"], strategy="bogus")


def test_extract_date_features(df: pd.DataFrame) -> None:
    result, log = extract_date_features(df, columns=["joined"])
    for feat in ("year", "month", "day", "weekday"):
        assert f"joined_{feat}" in result.columns
    assert log["columns_created"] == [
        "joined_year",
        "joined_month",
        "joined_day",
        "joined_weekday",
    ]


def test_extract_date_features_auto_detect(df: pd.DataFrame) -> None:
    result, _ = extract_date_features(df)
    assert "joined_year" in result.columns


def test_extract_date_features_unknown(df: pd.DataFrame) -> None:
    with pytest.raises(DataTransformError):
        extract_date_features(df, columns=["joined"], features=("fortnight",))


def test_variance_threshold_filter(df: pd.DataFrame) -> None:
    result, log = variance_threshold_filter(df, threshold=0.1, columns=["a", "const"])
    assert "const" not in result.columns
    assert log["columns_dropped"] == ["const"]


def test_correlation_feature_selector(df: pd.DataFrame) -> None:
    strong = df.copy()
    strong["target"] = strong["a"] * 5 + 0.01 * strong["b"]
    result, log = correlation_feature_selector(strong, "target", threshold=0.5)
    assert "a" in result.columns
    assert log["features_kept"] == ["a"]


def test_correlation_feature_selector_bad_target(df: pd.DataFrame) -> None:
    with pytest.raises(DataTransformError):
        correlation_feature_selector(df, "joined")


def test_feature_importance_report(df: pd.DataFrame) -> None:
    report = feature_importance_report(df, target_column="target")
    assert report["n_features"] == 3
    assert report["ranking"][0]["score"] >= report["ranking"][-1]["score"]
    assert report["method"] == "variance_and_correlation"
