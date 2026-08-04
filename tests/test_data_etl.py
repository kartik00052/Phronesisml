"""Tests for the ETL toolkit (``phronesisml.data.etl``)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from phronesisml.data import (
    add_id_column,
    convert_datetime,
    drop_columns,
    drop_duplicates,
    fill_missing_values,
    filter_rows,
    normalize_columns,
    one_hot_encode,
    remove_outliers,
    rename_columns,
    reset_index,
    sample_data,
    select_columns,
    set_index,
    sort_data,
    split_train_test,
    standardize_columns,
    stratify_split,
)
from phronesisml.exceptions import DataTransformError


@pytest.fixture()
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": np.arange(20),
            "age": np.random.default_rng(0).integers(18, 80, 20).astype("int64"),
            "score": np.random.default_rng(1).normal(50, 10, 20),
            "category": ["A", "B", "C"] * 6 + ["A", "B"],
            "joined": ["2020-01-01"] * 20,
        }
    )


def test_drop_columns(df: pd.DataFrame) -> None:
    result, log = drop_columns(df, ["id"])
    assert "id" not in result.columns
    assert log["columns_dropped"] == ["id"]
    assert "id" in df.columns  # input untouched


def test_drop_columns_missing_raises(df: pd.DataFrame) -> None:
    with pytest.raises(DataTransformError):
        drop_columns(df, ["nope"])


def test_select_columns(df: pd.DataFrame) -> None:
    result, log = select_columns(df, ["id", "age"])
    assert list(result.columns) == ["id", "age"]
    assert log["columns_kept"] == ["id", "age"]


def test_rename_columns(df: pd.DataFrame) -> None:
    result, log = rename_columns(df, {"age": "years"})
    assert "years" in result.columns
    assert "age" not in result.columns
    assert log["renames"] == {"age": "years"}


def test_filter_rows(df: pd.DataFrame) -> None:
    result, log = filter_rows(df, lambda d: d["age"] >= 30)
    assert (result["age"] >= 30).all()
    assert log["rows_removed"] == int((df["age"] < 30).sum())


def test_sort_data(df: pd.DataFrame) -> None:
    result, log = sort_data(df, by="age")
    assert list(result["age"]) == sorted(df["age"])
    assert log["by"] == ["age"]


def test_drop_duplicates(df: pd.DataFrame) -> None:
    dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    result, log = drop_duplicates(dup)
    assert result.shape[0] == df.shape[0]
    assert log["duplicates_removed"] == 1


def test_remove_outliers(df: pd.DataFrame) -> None:
    skewed = df.copy()
    skewed.loc[0, "age"] = 10_000
    result, log = remove_outliers(skewed, columns=["age"])
    assert log["outliers_detected"] >= 1
    assert result.shape[0] < skewed.shape[0]


def test_remove_outliers_clip(df: pd.DataFrame) -> None:
    skewed = df.copy()
    skewed.loc[0, "age"] = 10_000
    result, log = remove_outliers(skewed, columns=["age"], keep="clip")
    assert log["outliers_detected"] >= 1
    assert result.shape[0] == skewed.shape[0]
    assert result["age"].max() <= 10_000


def test_normalize_columns_minmax(df: pd.DataFrame) -> None:
    result, log = normalize_columns(df, columns=["age", "score"])
    assert result["age"].min() == pytest.approx(0.0)
    assert result["age"].max() == pytest.approx(1.0)
    assert log["columns_normalized"] == ["age", "score"]


def test_normalize_columns_standard(df: pd.DataFrame) -> None:
    result, log = normalize_columns(df, columns=["score"], method="standard")
    assert result["score"].mean() == pytest.approx(0.0, abs=1e-9)
    assert result["score"].std() == pytest.approx(1.0, abs=1e-9)


def test_standardize_columns(df: pd.DataFrame) -> None:
    result, log = standardize_columns(df, columns=["score"])
    assert log["method"] == "standard"
    assert result["score"].mean() == pytest.approx(0.0, abs=1e-9)


def test_one_hot_encode(df: pd.DataFrame) -> None:
    result, log = one_hot_encode(df, columns=["category"])
    assert "category" not in result.columns
    assert "category_A" in result.columns
    assert "category_B" in result.columns
    assert log["columns_encoded"] == ["category"]


def test_convert_datetime(df: pd.DataFrame) -> None:
    result, log = convert_datetime(df, columns=["joined"])
    assert pd.api.types.is_datetime64_any_dtype(result["joined"])
    assert log["columns_converted"] == ["joined"]


@pytest.mark.filterwarnings("ignore:Could not infer format")
def test_convert_datetime_fails(df: pd.DataFrame) -> None:
    bad = df.copy()
    bad["joined"] = "not-a-date"
    with pytest.raises(DataTransformError):
        convert_datetime(bad, columns=["joined"])


def test_add_id_column(df: pd.DataFrame) -> None:
    result, log = add_id_column(df, name="row_id", start=1)
    assert list(result["row_id"]) == list(range(1, 21))
    with pytest.raises(DataTransformError):
        add_id_column(result, name="row_id")


def test_set_index(df: pd.DataFrame) -> None:
    result, log = set_index(df, "id")
    assert result.index.name == "id"
    assert "id" not in result.columns


def test_reset_index(df: pd.DataFrame) -> None:
    indexed = df.set_index("id")
    result, log = reset_index(indexed)
    assert list(result.columns) == list(df.columns)


def test_fill_missing_values(df: pd.DataFrame) -> None:
    df.loc[0, "score"] = np.nan
    result, log = fill_missing_values(df, fill_value=0.0)
    assert result["score"].isnull().sum() == 0
    assert log["action"] == "handle_nulls"


def test_split_train_test(df: pd.DataFrame) -> None:
    train, test = split_train_test(df, test_size=0.2, random_state=1)
    assert train.shape[0] == 16
    assert test.shape[0] == 4


def test_split_train_test_stratified(df: pd.DataFrame) -> None:
    train, test = split_train_test(df, target_column="category", test_size=0.5, random_state=1)
    assert train.shape[0] == 10
    assert test.shape[0] == 10


def test_stratify_split(df: pd.DataFrame) -> None:
    parts = stratify_split(df, target_column="category", fractions=[0.5, 0.3, 0.2], random_state=1)
    assert len(parts) == 3
    assert sum(p.shape[0] for p in parts) == df.shape[0]


def test_stratify_split_bad_fractions(df: pd.DataFrame) -> None:
    with pytest.raises(DataTransformError):
        stratify_split(df, target_column="category", fractions=[0.5, 0.2])


def test_sample_data(df: pd.DataFrame) -> None:
    result, log = sample_data(df, n=5, random_state=0)
    assert result.shape[0] == 5
    assert log["n"] == 5


def test_sample_data_fraction(df: pd.DataFrame) -> None:
    result, _ = sample_data(df, fraction=0.5, random_state=0)
    assert result.shape[0] == 10
