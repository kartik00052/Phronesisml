"""ETL toolkit — composable, immutable DataFrame transformations.

Pure, deterministic, offline functions that build on
``data.transformers.cleaning`` (null handling, dtype casting, label
encoding) with the common extract-transform-load operations:

- Column ops: ``drop_columns``, ``rename_columns``, ``select_columns``
- Row ops: ``filter_rows``, ``sort_data``, ``drop_duplicates``
- Outlier handling: ``remove_outliers``
- Numeric transforms: ``normalize_columns``, ``standardize_columns``
- Encoding: ``one_hot_encode``
- Datetime: ``convert_datetime``
- Index/identity: ``add_id_column``, ``set_index``, ``reset_index``
- Splitting: ``split_train_test``, ``stratify_split``, ``sample_data``
- Convenience: ``fill_missing_values``

Every transform returns a tuple ``(result_df, log_entry_dict)`` and
never mutates its input (immutable pattern, matching ``cleaning.py``).
Hard failures raise ``DataTransformError``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import pandas as pd

from phronesisml.data.transformers.cleaning import handle_nulls
from phronesisml.exceptions import DataTransformError

logger = logging.getLogger(__name__)


def _copy(df: pd.DataFrame) -> pd.DataFrame:
    return df.copy()


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        msg = f"Column(s) not found in DataFrame: {missing}"
        raise DataTransformError(msg)


def drop_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Drop columns from a DataFrame.

    Args:
        df: Input DataFrame.
        columns: Column names to drop.

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If a column does not exist.
    """
    _ensure_columns(df, columns)
    result = _copy(df).drop(columns=columns)
    return result, {
        "action": "drop_columns",
        "columns_dropped": columns,
        "rows": int(result.shape[0]),
        "columns_after": int(result.shape[1]),
    }


def select_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Keep only the specified columns.

    Args:
        df: Input DataFrame.
        columns: Column names to keep.

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If a column does not exist.
    """
    _ensure_columns(df, columns)
    result = _copy(df)[columns]
    return result, {
        "action": "select_columns",
        "columns_kept": columns,
        "rows": int(result.shape[0]),
        "columns_after": int(result.shape[1]),
    }


def rename_columns(
    df: pd.DataFrame,
    mapping: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Rename columns using a mapping.

    Args:
        df: Input DataFrame.
        mapping: Old column name → new column name.

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If a mapped column does not exist.
    """
    _ensure_columns(df, list(mapping))
    result = _copy(df).rename(columns=mapping)
    return result, {
        "action": "rename_columns",
        "renames": mapping,
        "columns_after": int(result.shape[1]),
    }


def filter_rows(
    df: pd.DataFrame,
    condition: Callable[[pd.DataFrame], Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Keep rows that satisfy a callable boolean condition.

    Args:
        df: Input DataFrame.
        condition: Callable that receives the DataFrame and returns a
            boolean mask (Series/array) of row-wise pass/fail.

    Returns:
        A tuple of (result DataFrame, log entry dict).
    """
    mask = condition(df)
    result = _copy(df)[mask]
    return result, {
        "action": "filter_rows",
        "rows_before": int(df.shape[0]),
        "rows_after": int(result.shape[0]),
        "rows_removed": int(df.shape[0] - result.shape[0]),
    }


def sort_data(
    df: pd.DataFrame,
    by: str | list[str],
    ascending: bool | list[bool] = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Sort rows by one or more columns.

    Args:
        df: Input DataFrame.
        by: Column name or list of column names to sort by.
        ascending: Sort order (single bool or per-column list).

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If a sort column does not exist.
    """
    cols = [by] if isinstance(by, str) else list(by)
    _ensure_columns(df, cols)
    result = _copy(df).sort_values(by=by, ascending=ascending, ignore_index=True)
    return result, {
        "action": "sort_data",
        "by": cols,
        "ascending": ascending,
        "rows": int(result.shape[0]),
    }


def drop_duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Remove duplicate rows.

    Args:
        df: Input DataFrame.
        subset: Columns to consider for duplication; ``None`` uses all.

    Returns:
        A tuple of (result DataFrame, log entry dict).
    """
    if subset is not None:
        _ensure_columns(df, subset)
    result = _copy(df).drop_duplicates(subset=subset, keep="first", ignore_index=True)
    return result, {
        "action": "drop_duplicates",
        "rows_before": int(df.shape[0]),
        "rows_after": int(result.shape[0]),
        "duplicates_removed": int(df.shape[0] - result.shape[0]),
    }


def remove_outliers(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "iqr",
    factor: float = 1.5,
    keep: str = "remove",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Remove or clip rows with outliers in numeric columns.

    Args:
        df: Input DataFrame.
        columns: Numeric columns to evaluate.  ``None`` uses all numeric
            columns.
        method: Outlier rule — currently ``"iqr"`` only.
        factor: IQR multiplier for the outlier bounds.
        keep: ``"remove"`` drops outlier rows; ``"clip"`` caps the values
            at the Tukey fences instead of dropping rows.

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If *keep* is unknown or no numeric columns
            are available.
    """
    if method != "iqr":
        msg = f"Unknown outlier method: {method!r}. Only 'iqr' is supported."
        raise DataTransformError(msg)
    if keep not in ("remove", "clip"):
        msg = f"Unknown keep mode: {keep!r}. Use 'remove' or 'clip'."
        raise DataTransformError(msg)

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    target_cols = columns if columns is not None else numeric_cols
    _ensure_columns(df, target_cols)
    target_cols = [c for c in target_cols if pd.api.types.is_numeric_dtype(df[c])]
    if not target_cols:
        msg = "No numeric columns available for outlier detection."
        raise DataTransformError(msg)

    bounds: dict[str, tuple[float, float]] = {}
    outlier_mask = pd.Series(False, index=df.index)
    for col in target_cols:
        series = df[col].dropna()
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = float(q1 - factor * iqr)
        upper = float(q3 + factor * iqr)
        bounds[col] = (lower, upper)
        outlier_mask |= (df[col] < lower) | (df[col] > upper)

    n_outliers = int(outlier_mask.sum())
    if keep == "remove":
        result = _copy(df)[~outlier_mask].reset_index(drop=True)
        rows_removed = int(df.shape[0] - result.shape[0])
    else:
        result = _copy(df)
        for col, (lower, upper) in bounds.items():
            result[col] = result[col].clip(lower, upper)
        rows_removed = 0

    return result, {
        "action": "remove_outliers",
        "method": method,
        "columns": target_cols,
        "outliers_detected": n_outliers,
        "rows_removed": rows_removed,
        "bounds": bounds,
    }


def normalize_columns(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "minmax",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Normalize numeric columns to a bounded range.

    Args:
        df: Input DataFrame.
        columns: Columns to normalize; ``None`` uses all numeric columns.
        method: ``"minmax"`` (scale to [0, 1]) or ``"standard"``
            (z-score, mean 0 / std 1).

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If *method* is unknown.
    """
    if method not in ("minmax", "standard"):
        msg = f"Unknown normalization method: {method!r}. Use 'minmax' or 'standard'."
        raise DataTransformError(msg)

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    target_cols = columns if columns is not None else numeric_cols
    _ensure_columns(df, target_cols)
    target_cols = [c for c in target_cols if pd.api.types.is_numeric_dtype(df[c])]
    if not target_cols:
        msg = "No numeric columns available for normalization."
        raise DataTransformError(msg)

    result = _copy(df)
    params: dict[str, dict[str, float]] = {}
    for col in target_cols:
        col_min = float(result[col].min())
        col_max = float(result[col].max())
        if method == "minmax":
            rng = col_max - col_min
            result[col] = 0.0 if rng == 0 else (result[col] - col_min) / rng
            params[col] = {"method": "minmax", "min": col_min, "max": col_max}
        else:
            mean = float(result[col].mean())
            std = float(result[col].std())
            result[col] = 0.0 if std == 0 else (result[col] - mean) / std
            params[col] = {"method": "standard", "mean": mean, "std": std}

    return result, {
        "action": "normalize_columns",
        "method": method,
        "columns_normalized": target_cols,
        "params": params,
    }


def standardize_columns(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Standardize (z-score) numeric columns.

    Thin wrapper over ``normalize_columns`` with ``method="standard"``.

    Args:
        df: Input DataFrame.
        columns: Columns to standardize; ``None`` uses all numeric.

    Returns:
        A tuple of (result DataFrame, log entry dict).
    """
    return normalize_columns(df, columns=columns, method="standard")


def one_hot_encode(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    drop_first: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """One-hot encode categorical columns.

    Args:
        df: Input DataFrame.
        columns: Categorical columns to encode; ``None`` uses all
            non-numeric columns.
        drop_first: Drop the first category per column to avoid
            collinearity.

    Returns:
        A tuple of (result DataFrame, log entry dict).
    """
    categorical_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    target_cols = columns if columns is not None else categorical_cols
    _ensure_columns(df, target_cols)
    target_cols = [c for c in target_cols if not pd.api.types.is_numeric_dtype(df[c])]

    if not target_cols:
        return _copy(df), {"action": "one_hot_encode", "columns_encoded": []}

    result = _copy(df)
    for col in target_cols:
        encoded = pd.get_dummies(result[col], prefix=col, drop_first=drop_first, dtype=int)
        result = pd.concat([result, encoded], axis=1)
        result = result.drop(columns=[col])

    return result, {
        "action": "one_hot_encode",
        "columns_encoded": target_cols,
        "drop_first": drop_first,
        "columns_after": int(result.shape[1]),
    }


def convert_datetime(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    format: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Convert columns to datetime dtype.

    Args:
        df: Input DataFrame.
        columns: Columns to convert; ``None`` attempts auto-detection on
            object columns.
        format: Optional strftime format hint passed to
            ``pandas.to_datetime``.

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If a column fails to parse as datetime.
    """
    candidates = (
        columns if columns is not None else [c for c in df.columns if df[c].dtype == "object"]
    )
    _ensure_columns(df, candidates)

    result = _copy(df)
    converted: list[str] = []
    for col in candidates:
        try:
            result[col] = pd.to_datetime(result[col], format=format, errors="raise")
            converted.append(col)
        except (ValueError, TypeError) as exc:
            msg = f"Failed to convert column '{col}' to datetime: {exc}"
            raise DataTransformError(msg) from exc

    return result, {
        "action": "convert_datetime",
        "columns_converted": converted,
        "format": format,
    }


def add_id_column(
    df: pd.DataFrame,
    name: str = "row_id",
    start: int = 0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Add a sequential integer id column.

    Args:
        df: Input DataFrame.
        name: Name of the id column.
        start: First id value.

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If the id column already exists.
    """
    if name in df.columns:
        msg = f"Column '{name}' already exists in DataFrame."
        raise DataTransformError(msg)
    result = _copy(df)
    result.insert(0, name, range(start, start + int(result.shape[0])))
    return result, {
        "action": "add_id_column",
        "name": name,
        "start": start,
        "rows": int(result.shape[0]),
    }


def set_index(
    df: pd.DataFrame,
    column: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Set a column as the DataFrame index.

    Args:
        df: Input DataFrame.
        column: Column to use as the index.

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If the column does not exist.
    """
    _ensure_columns(df, [column])
    result = _copy(df).set_index(column)
    return result, {
        "action": "set_index",
        "index_column": column,
        "rows": int(result.shape[0]),
        "columns_after": int(result.shape[1]),
    }


def reset_index(
    df: pd.DataFrame,
    drop: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reset the index to a default RangeIndex.

    Args:
        df: Input DataFrame.
        drop: If ``True``, discard the old index instead of promoting it
            to a column.

    Returns:
        A tuple of (result DataFrame, log entry dict).
    """
    result = _copy(df).reset_index(drop=drop)
    return result, {
        "action": "reset_index",
        "drop": drop,
        "rows": int(result.shape[0]),
        "columns_after": int(result.shape[1]),
    }


def fill_missing_values(
    df: pd.DataFrame,
    fill_value: Any = 0,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fill missing values with a constant.

    Convenience wrapper over ``handle_nulls(..., strategy="fill")``.

    Args:
        df: Input DataFrame.
        fill_value: Constant value for null cells.
        columns: Columns to fill; ``None`` fills every column with nulls.

    Returns:
        A tuple of (result DataFrame, log entry dict).
    """
    return handle_nulls(df, strategy="fill", fill_value=fill_value, columns=columns)


def split_train_test(
    df: pd.DataFrame,
    target_column: str | None = None,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a DataFrame into train and test subsets.

    When *target_column* is given and categorical, the split is
    stratified on the target.  Otherwise the split is random.

    Args:
        df: Input DataFrame.
        target_column: Optional target column for stratification.
        test_size: Fraction of rows in the test set (0..1).
        random_state: Seed for reproducible splits.

    Returns:
        A tuple of (train DataFrame, test DataFrame).
    """
    if not 0 < test_size < 1:
        msg = f"test_size must be between 0 and 1, got {test_size}."
        raise DataTransformError(msg)

    from sklearn.model_selection import train_test_split

    if target_column is not None and not pd.api.types.is_numeric_dtype(df[target_column]):
        stratify = df[target_column]
    else:
        stratify = None

    train, test = train_test_split(
        df, test_size=test_size, random_state=random_state, stratify=stratify
    )
    return train, test


def stratify_split(
    df: pd.DataFrame,
    target_column: str,
    fractions: list[float],
    random_state: int = 42,
) -> list[pd.DataFrame]:
    """Split a DataFrame into multiple stratified subsets.

    Args:
        df: Input DataFrame.
        target_column: Categorical column to stratify on.
        fractions: Fractions of rows for each subset (must sum to 1).
        random_state: Seed for reproducible splits.

    Returns:
        A list of DataFrames, one per fraction.

    Raises:
        DataTransformError: If fractions do not sum to 1.
    """
    _ensure_columns(df, [target_column])
    total = sum(fractions)
    if abs(total - 1.0) > 1e-6:
        msg = f"Fractions must sum to 1.0, got {sum(fractions)}."
        raise DataTransformError(msg)

    from sklearn.model_selection import train_test_split

    remaining = df
    result: list[pd.DataFrame] = []
    for i, frac in enumerate(fractions[:-1]):
        share = frac / sum(fractions[i:])
        part, remaining = train_test_split(
            remaining,
            test_size=1 - share,
            random_state=random_state,
            stratify=remaining[target_column],
        )
        result.append(part)
    result.append(remaining)
    return result


def sample_data(
    df: pd.DataFrame,
    n: int | None = None,
    fraction: float | None = None,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Sample rows from a DataFrame.

    Args:
        df: Input DataFrame.
        n: Exact number of rows to sample.
        fraction: Fraction of rows to sample (mutually exclusive with *n*).
        random_state: Seed for reproducibility.

    Returns:
        A tuple of (result DataFrame, log entry dict).

    Raises:
        DataTransformError: If both *n* and *fraction* are given.
    """
    if n is not None and fraction is not None:
        msg = "Provide either n or fraction, not both."
        raise DataTransformError(msg)
    if n is None and fraction is None:
        msg = "Provide either n or fraction."
        raise DataTransformError(msg)

    if fraction is not None:
        n = max(1, int(round(df.shape[0] * fraction)))
    if n is None:
        msg = "n resolved to None; provide a valid sample size."
        raise DataTransformError(msg)
    n = min(int(n), int(df.shape[0]))

    result = df.sample(n=n, random_state=random_state).reset_index(drop=True)
    return result, {
        "action": "sample_data",
        "n": n,
        "random_state": random_state,
        "rows_before": int(df.shape[0]),
        "rows_after": int(result.shape[0]),
    }
