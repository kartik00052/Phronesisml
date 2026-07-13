"""Shared test fixtures for Phronesis tests."""

from __future__ import annotations

import importlib

import pandas as pd
import pytest

from phronesisml.engines.pandas_engine import PandasEngine

collect_ignore: list[str] = []
if not importlib.util.find_spec("fastapi"):
    collect_ignore.append("test_api.py")
if not importlib.util.find_spec("typer"):
    collect_ignore.append("test_cli_app.py")


@pytest.fixture
def pandas_engine() -> PandasEngine:
    """Return a PandasEngine instance for testing."""
    return PandasEngine()


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Return a sample DataFrame with mixed types and some nulls."""
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "age": [30, 25, 35, 28, 32],
            "salary": [75000.0, 65000.0, 85000.0, 70000.0, 90000.0],
            "department": ["Engineering", "Marketing", "Engineering", "Marketing", "Engineering"],
        }
    )


@pytest.fixture
def empty_df() -> pd.DataFrame:
    """Return an empty DataFrame (zero rows)."""
    return pd.DataFrame(columns=["name", "age", "salary"])


@pytest.fixture
def zero_columns_df() -> pd.DataFrame:
    """Return a DataFrame with zero columns but some rows."""
    return pd.DataFrame(index=range(5))


@pytest.fixture
def all_null_column_df() -> pd.DataFrame:
    """Return a DataFrame where one column is entirely null."""
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [30, 25, 35],
            "empty_col": [None, None, None],
        }
    )


@pytest.fixture
def single_row_df() -> pd.DataFrame:
    """Return a DataFrame with a single row."""
    return pd.DataFrame(
        {
            "name": ["Alice"],
            "age": [30],
            "salary": [75000.0],
        }
    )


@pytest.fixture
def duplicate_rows_df() -> pd.DataFrame:
    """Return a DataFrame with duplicate rows."""
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Alice", "Charlie"],
            "age": [30, 25, 30, 35],
        }
    )


@pytest.fixture
def classification_df() -> pd.DataFrame:
    """Return a DataFrame with a clear classification target."""
    return pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "feature_b": [10, 20, 30, 40, 50, 60, 70, 80],
            "label": ["A", "B", "A", "B", "A", "B", "A", "B"],
        }
    )


@pytest.fixture
def regression_df() -> pd.DataFrame:
    """Return a DataFrame with a clear regression target."""
    return pd.DataFrame(
        {
            "feature_a": list(range(1, 11)),
            "feature_b": [x * 10 for x in range(1, 11)],
            "target": [x * 10.5 for x in range(1, 11)],
        }
    )


@pytest.fixture
def ambiguous_target_df() -> pd.DataFrame:
    """Return a DataFrame with an ambiguous numeric target (2-5 unique values).

    The 'grade' column is numeric with only 3 unique values (1, 2, 3),
    making it ambiguous between classification and regression.
    Feature columns are constant (1 unique value each) so they get
    zero confidence and 'grade' is the only candidate.
    """
    return pd.DataFrame(
        {
            "feature_a": [1.0] * 10,
            "feature_b": [10] * 10,
            "grade": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
        }
    )


@pytest.fixture
def features_only_df() -> pd.DataFrame:
    """Return a DataFrame with only feature columns (no target)."""
    return pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "feature_b": [10, 20, 30, 40, 50],
            "feature_c": ["A", "B", "A", "B", "A"],
        }
    )
