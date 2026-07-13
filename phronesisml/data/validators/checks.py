"""Data validation checks — schema, type, and quality inspection.

All functions receive an engine-native DataFrame and a ``BaseEngine``
instance.  They use ``engine.collect()`` to materialise the data into
the universal Pandas format for introspection, and ``engine.dtypes()``
/ ``engine.shape()`` for schema checks.  No direct pandas or polars
imports are used here — all data access flows through the engine.

Design:
- Functions are pure (no side effects beyond raising exceptions).
- Each check returns a structured dict suitable for inclusion in a
  ``validation_report``.
- Genuinely invalid data (empty DataFrame, zero columns) raises
  ``DataValidationError`` immediately — these are hard failures, not
  soft warnings.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.engines.base_engine import BaseEngine
from phronesisml.exceptions import DataValidationError

logger = logging.getLogger(__name__)


def validate_dataframe(
    df: Any,
    engine: BaseEngine,
) -> tuple[Any, dict[str, Any]]:
    """Run all validation checks on *df* and return a structured report.

    Args:
        df: Engine-native DataFrame to validate.
        engine: The active computation engine.

    Returns:
        A tuple of ``(df, report)`` where *report* is a dict containing
        individual check results.

    Raises:
        DataValidationError: If the DataFrame is empty or has zero columns.

    """
    report: dict[str, Any] = {}

    # ── Hard failures ────────────────────────────────────────────────
    n_rows, n_cols = engine.shape(df)
    report["shape"] = {"rows": n_rows, "columns": n_cols}

    if n_cols == 0:
        msg = "Validation failed: DataFrame has zero columns."
        raise DataValidationError(msg)

    if n_rows == 0:
        msg = "Validation failed: DataFrame has zero rows (empty)."
        raise DataValidationError(msg)

    # ── Schema inspection ────────────────────────────────────────────
    report["dtypes"] = engine.dtypes(df)
    report["column_names"] = engine.columns(df)

    # ── Null analysis ────────────────────────────────────────────────
    collected = engine.cached_collect(df)
    report["null_counts"] = _count_nulls(collected)
    report["null_columns"] = [col for col, count in report["null_counts"].items() if count > 0]

    # ── Fully-empty columns ──────────────────────────────────────────
    report["empty_columns"] = [
        col for col, count in report["null_counts"].items() if count == n_rows
    ]

    # ── Duplicate rows ───────────────────────────────────────────────
    report["duplicate_rows"] = _count_duplicates(collected)

    # ── Summary ──────────────────────────────────────────────────────
    report["passed"] = True
    logger.info(
        "Validation complete: %d rows, %d columns, %d null columns, %d duplicates.",
        n_rows,
        n_cols,
        len(report["null_columns"]),
        report["duplicate_rows"],
    )
    return df, report


def _count_nulls(collected_df: Any) -> dict[str, int]:
    """Count null values per column from a collected (pandas) DataFrame.

    Uses ``.isnull().sum()`` on the collected result — no pandas import
    needed at call site since the object is already a pandas DataFrame
    returned by ``engine.collect()``.
    """
    null_series = collected_df.isnull().sum()
    return {col: int(count) for col, count in null_series.items()}


def _count_duplicates(collected_df: Any) -> int:
    """Count fully-duplicate rows from a collected (pandas) DataFrame."""
    return int(collected_df.duplicated().sum())
