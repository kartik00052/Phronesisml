"""Data transformers — cleaning and transformation operations.

This module provides composable data transformation functions used by
the ETL agent.  Each function takes a DataFrame and returns a
transformed DataFrame (immutable pattern — no in-place mutation).

Transform categories:
- **Null handling**: drop, fill, or flag missing values.
- **Type casting**: coerce columns to target dtypes.
- **Encoding**: label-encode categorical columns.

All transformations log their actions via ``transform_log`` entries so
the ETL agent can record what happened to the data.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from phronesisml.exceptions import DataTransformError

logger = logging.getLogger(__name__)


def handle_nulls(
    df: pd.DataFrame,
    strategy: str = "drop",
    fill_value: Any = None,
    columns: list[str] | None = None,
    *,
    copy: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Handle missing values in the DataFrame.

    Args:
        df: Input DataFrame.
        strategy: One of ``"drop"`` (remove rows with nulls),
            ``"fill"`` (replace with *fill_value*), or ``"flag"``
            (add boolean indicator columns).
        fill_value: Value to use when ``strategy="fill"``.
        columns: Specific columns to operate on.  If ``None``, all
            columns with nulls are processed.
        copy: If ``True`` (default), copy the DataFrame before mutating.
            Pass ``False`` when the caller already owns a copy.

    Returns:
        A tuple of (transformed DataFrame, log entry dict).

    """
    if strategy not in ("drop", "fill", "flag"):
        msg = f"Unknown null strategy: {strategy!r}. Use 'drop', 'fill', or 'flag'."
        raise DataTransformError(msg)

    null_counts = df.isnull().sum()
    cols_with_nulls = [c for c in df.columns if null_counts[c] > 0]
    target_cols = columns if columns is not None else cols_with_nulls

    if not target_cols:
        logger.info("No null values found — skipping null handling.")
        return df, {"action": "handle_nulls", "strategy": strategy, "columns_affected": 0}

    before_rows = len(df)

    if strategy == "drop":
        result = df.dropna(subset=target_cols)
    elif strategy == "fill":
        result = df.copy() if copy else df
        result[target_cols] = result[target_cols].fillna(fill_value)
    elif strategy == "flag":
        result = df.copy() if copy else df
        for col in target_cols:
            result[f"{col}_is_null"] = result[col].isnull().astype(int)

    after_rows = len(result)
    log_entry: dict[str, Any] = {
        "action": "handle_nulls",
        "strategy": strategy,
        "columns_affected": len(target_cols),
        "rows_before": before_rows,
        "rows_after": after_rows,
    }
    logger.info("Null handling (%s): %d rows -> %d rows", strategy, before_rows, after_rows)
    return result, log_entry


def cast_dtypes(
    df: pd.DataFrame,
    type_map: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Cast columns to the specified dtypes.

    Args:
        df: Input DataFrame.
        type_map: Mapping of column name → target dtype string
            (e.g. ``{"age": "int64", "price": "float64"}``).

    Returns:
        A tuple of (transformed DataFrame, log entry dict).

    Raises:
        DataTransformError: If a column does not exist or casting fails.

    """
    result = df.copy()
    casted: list[str] = []
    for col, dtype in type_map.items():
        if col not in result.columns:
            msg = f"Column '{col}' not found in DataFrame."
            raise DataTransformError(msg)
        try:
            result[col] = result[col].astype(dtype)
            casted.append(col)
        except (ValueError, TypeError) as exc:
            msg = f"Failed to cast column '{col}' to {dtype}: {exc}"
            raise DataTransformError(msg) from exc

    log_entry: dict[str, Any] = {
        "action": "cast_dtypes",
        "columns_cast": casted,
        "type_map": type_map,
    }
    logger.info("Cast %d columns to specified dtypes.", len(casted))
    return result, log_entry


def encode_categoricals(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    strategy: str = "label",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Encode categorical columns as numeric values.

    Args:
        df: Input DataFrame.
        columns: Columns to encode.  If ``None``, all object/string
            columns are encoded.
        strategy: Encoding strategy — currently only ``"label"`` is
            supported (label encoding via ``pd.factorize``).

    Returns:
        A tuple of (transformed DataFrame, log entry dict).

    Raises:
        DataTransformError: If an unsupported strategy is provided.

    """
    if strategy != "label":
        msg = f"Unsupported encoding strategy: {strategy!r}. Only 'label' is supported."
        raise DataTransformError(msg)

    if columns is None:
        columns = [c for c in df.columns if df[c].dtype == "object"]

    if not columns:
        logger.info("No categorical columns found — skipping encoding.")
        return df, {"action": "encode_categoricals", "columns_encoded": 0}

    result = df.copy()
    encoding_maps: dict[str, dict[Any, int]] = {}
    for col in columns:
        codes, uniques = pd.factorize(result[col])
        result[col] = codes
        encoding_maps[col] = {v: int(i) for i, v in enumerate(uniques)}

    log_entry: dict[str, Any] = {
        "action": "encode_categoricals",
        "strategy": strategy,
        "columns_encoded": columns,
        "encoding_maps": encoding_maps,
    }
    logger.info("Label-encoded %d categorical columns.", len(columns))
    return result, log_entry
