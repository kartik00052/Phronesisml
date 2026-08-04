"""Tests for the EDA toolkit (``phronesisml.data.eda``)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from phronesisml.data import (
    column_distribution,
    correlation_matrix,
    data_quality_report,
    missing_value_matrix,
    outlier_analysis,
    skewness_analysis,
    summary_statistics,
    target_distribution,
    type_report,
)


@pytest.fixture()
def df() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    return pd.DataFrame(
        {
            "age": rng.integers(18, 80, 40).astype("int64"),
            "height": rng.normal(170, 10, 40),
            "score": rng.normal(50, 15, 40),
            "category": ["A", "B"] * 20,
            "joined": pd.to_datetime(["2020-01-01"] * 40),
        }
    )


def test_summary_statistics(df: pd.DataFrame) -> None:
    stats = summary_statistics(df)
    assert set(stats) == set(df.columns)
    assert stats["age"]["count"] == 40
    assert stats["age"]["null_count"] == 0
    assert "mean" in stats["height"]
    assert "top_values" in stats["category"]


def test_correlation_matrix(df: pd.DataFrame) -> None:
    corr = correlation_matrix(df)
    assert corr["method"] == "pearson"
    assert set(corr["columns"]) == {"age", "height", "score"}
    assert abs(corr["matrix"]["age"]["age"] - 1.0) < 1e-9


def test_missing_value_matrix(df: pd.DataFrame) -> None:
    df.loc[0, "age"] = np.nan
    report = missing_value_matrix(df)
    assert report["missing_cells"] == 1
    assert report["columns"]["age"]["count"] == 1
    assert report["overall_fraction"] == pytest.approx(1 / (40 * 5))


def test_column_distribution_numeric(df: pd.DataFrame) -> None:
    dist = column_distribution(df, "age")
    assert dist["cardinality"] > 1
    assert "numeric_bins" in dist
    assert dist["min"] <= dist["max"]


def test_column_distribution_categorical(df: pd.DataFrame) -> None:
    dist = column_distribution(df, "category")
    assert dist["value_counts"] == {"A": 20, "B": 20}
    assert dist["entropy"] == pytest.approx(1.0, abs=1e-4)


def test_target_distribution_categorical(df: pd.DataFrame) -> None:
    dist = target_distribution(df, "category")
    assert dist["kind"] == "categorical"
    assert dist["n_classes"] == 2
    assert dist["class_counts"] == {"A": 20, "B": 20}


def test_target_distribution_numeric(df: pd.DataFrame) -> None:
    dist = target_distribution(df, "age")
    assert dist["kind"] == "numeric"
    assert "mean" in dist


def test_outlier_analysis_iqr(df: pd.DataFrame) -> None:
    skewed = df.copy()
    skewed.loc[0, "height"] = 1000
    report = outlier_analysis(skewed, columns=["height"], method="iqr")
    assert report["method"] == "iqr"
    assert report["columns"]["height"]["outliers"] >= 1


def test_outlier_analysis_zscore(df: pd.DataFrame) -> None:
    skewed = df.copy()
    skewed.loc[0, "height"] = 1000
    report = outlier_analysis(skewed, columns=["height"], method="zscore")
    assert report["columns"]["height"]["outliers"] >= 1


def test_outlier_analysis_bad_method(df: pd.DataFrame) -> None:
    with pytest.raises(ValueError):
        outlier_analysis(df, method="bogus")


def test_skewness_analysis(df: pd.DataFrame) -> None:
    skewed = df.copy()
    skewed["age"] = np.concatenate([np.ones(35) * 18, np.arange(19, 24)])
    report = skewness_analysis(skewed, columns=["age"])
    assert "skewness" in report["age"]
    assert report["age"]["skewness"] > 0


def test_type_report(df: pd.DataFrame) -> None:
    report = type_report(df)
    assert report["numeric"] == ["age", "height", "score"]
    assert report["categorical"] == ["category"]
    assert report["datetime"] == ["joined"]
    assert report["families"]["joined"] == "datetime"


def test_data_quality_report(df: pd.DataFrame) -> None:
    df.loc[0, "age"] = np.nan
    report = data_quality_report(df)
    assert report["shape"] == {"rows": 40, "columns": 5}
    assert report["columns"]["age"]["completeness"] == pytest.approx(0.975, abs=0.01)
    assert report["duplicate_rows"] == 0
