"""Tests for the data validation toolkit (``phronesisml.data.validation``)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from phronesisml.data import (
    generate_validation_report,
    infer_schema,
    validate_categorical_columns,
    validate_column_types,
    validate_constraints,
    validate_dataset,
    validate_datetime_columns,
    validate_duplicate_rows,
    validate_feature_columns,
    validate_missing_values,
    validate_numeric_columns,
    validate_schema,
    validate_target_column,
    validate_unique_constraints,
)
from phronesisml.exceptions import DataValidationError


@pytest.fixture()
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": np.arange(20),
            "age": np.random.default_rng(0).integers(18, 80, 20).astype("int64"),
            "score": np.random.default_rng(1).normal(50, 10, 20),
            "category": ["A", "B"] * 10,
            "joined": pd.to_datetime(["2020-01-01"] * 20),
            "is_active": [True, False] * 10,
        }
    )


def test_validate_missing_values_pass(df: pd.DataFrame) -> None:
    result = validate_missing_values(df, max_fraction=0.1)
    assert result["passed"] is True


def test_validate_missing_values_fail(df: pd.DataFrame) -> None:
    df.loc[:2, "age"] = np.nan
    result = validate_missing_values(df, max_fraction=0.05)
    assert result["passed"] is False
    assert result["missing_fraction"]["age"] == pytest.approx(0.15, abs=0.01)


def test_validate_duplicate_rows(df: pd.DataFrame) -> None:
    assert validate_duplicate_rows(df)["passed"] is True
    df.loc[1] = df.loc[0]
    assert validate_duplicate_rows(df)["duplicate_rows"] == 1


def test_validate_unique_constraints(df: pd.DataFrame) -> None:
    assert validate_unique_constraints(df, columns=["id"])["passed"] is True
    df.loc[1, "id"] = df.loc[0, "id"]
    assert validate_unique_constraints(df, columns=["id"])["passed"] is False


def test_validate_numeric_columns(df: pd.DataFrame) -> None:
    result = validate_numeric_columns(df, columns=["age", "score", "category"])
    assert result["is_numeric"]["age"] is True
    assert result["is_numeric"]["category"] is False


def test_validate_datetime_columns(df: pd.DataFrame) -> None:
    assert validate_datetime_columns(df, columns=["joined"])["passed"] is True
    assert validate_datetime_columns(df, columns=["id"])["passed"] is False


def test_validate_categorical_columns(df: pd.DataFrame) -> None:
    assert validate_categorical_columns(df, columns=["category", "is_active"])["passed"] is True


def test_validate_constraints(df: pd.DataFrame) -> None:
    result = validate_constraints(df, {"age": {"min": 0, "max": 120}})
    assert result["passed"] is True
    df.loc[0, "age"] = -5
    assert validate_constraints(df, {"age": {"min": 0}})["passed"] is False


def test_validate_constraints_missing_col_raises(df: pd.DataFrame) -> None:
    with pytest.raises(DataValidationError):
        validate_constraints(df, {"nope": {"min": 0}})


def test_validate_constraints_allowed_values(df: pd.DataFrame) -> None:
    assert validate_constraints(df, {"category": {"allowed": ["A", "B"]}})["passed"] is True
    assert validate_constraints(df, {"category": {"allowed": ["A"]}})["passed"] is False


def test_validate_constraints_unique(df: pd.DataFrame) -> None:
    assert validate_constraints(df, {"id": {"unique": True}})["passed"] is True


def test_validate_schema(df: pd.DataFrame) -> None:
    assert validate_schema(df, {"age": "int64", "score": "numeric"})["passed"] is True
    result = validate_schema(df, {"age": "float64"})
    assert result["passed"] is False
    assert "age" in result["dtype_mismatches"]


def test_infer_schema(df: pd.DataFrame) -> None:
    info = infer_schema(df)
    assert info["n_columns"] == 6
    assert info["schema"]["age"]["family"] == "numeric"
    assert info["schema"]["joined"]["family"] == "datetime"


def test_validate_target_column_classification(df: pd.DataFrame) -> None:
    assert validate_target_column(df, "is_active", "classification")["passed"] is True
    bad = df.copy()
    bad["constant"] = 1
    assert validate_target_column(bad, "constant", "classification")["passed"] is False


def test_validate_target_column_regression(df: pd.DataFrame) -> None:
    assert validate_target_column(df, "age", "regression")["passed"] is True
    assert validate_target_column(df, "category", "regression")["passed"] is False


def test_validate_target_column_missing_raises(df: pd.DataFrame) -> None:
    with pytest.raises(DataValidationError):
        validate_target_column(df, "nope")


def test_validate_feature_columns(df: pd.DataFrame) -> None:
    result = validate_feature_columns(df, ["age", "score", "category"], target_column="is_active")
    assert result["passed"] is True
    assert result["feature_columns"] == ["age", "score", "category"]


def test_validate_feature_columns_target_in_features(df: pd.DataFrame) -> None:
    result = validate_feature_columns(df, ["age", "category"], target_column="category")
    assert result["passed"] is False
    assert "category" not in result["feature_columns"]


def test_validate_feature_columns_missing_raises(df: pd.DataFrame) -> None:
    with pytest.raises(DataValidationError):
        validate_feature_columns(df, ["age", "nope"])


def test_validate_column_types(df: pd.DataFrame) -> None:
    result = validate_column_types(df, {"age": "int64", "score": "numeric"})
    assert result["passed"] is True
    assert validate_column_types(df, {"age": "object"})["passed"] is False


def test_validate_dataset(df: pd.DataFrame) -> None:
    result = validate_dataset(df, schema={"age": "int64"}, target_column="is_active")
    assert result["passed"] is True
    assert result["n_checks"] == 4


def test_validate_dataset_errors_on_empty() -> None:
    with pytest.raises(DataValidationError):
        validate_dataset(pd.DataFrame({"a": []}))
    with pytest.raises(DataValidationError):
        validate_dataset(pd.DataFrame())


def test_generate_validation_report(df: pd.DataFrame) -> None:
    report = generate_validation_report(df, schema={"age": "int64"}, target_column="is_active")
    assert report["passed"] is True
    assert report["summary"]["rows"] == 20
    assert "missing_values" in report["details"]
    assert "target" in report["details"]
    assert "inferred_schema" in report["details"]


def test_generate_validation_report_detects_problems(df: pd.DataFrame) -> None:
    df.loc[0, "age"] = np.nan
    df.loc[1] = df.loc[0]
    report = generate_validation_report(df)
    assert report["n_violations"] >= 1
    assert report["passed"] is False
