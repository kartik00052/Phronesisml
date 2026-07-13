"""Data profiling — descriptive statistics and distribution analysis.

All functions receive an engine-native DataFrame and a ``BaseEngine``
instance.  They use ``engine.collect()`` to materialise the data into
the universal Pandas format for computation, and ``engine.dtypes()``
for type-aware profiling.  No direct pandas or polars imports are used
here — all data access flows through the engine.

Design:
- Functions are pure (no side effects).
- Returns structured dicts suitable for inclusion in a ``data_profile``
  or ``eda_report``.
- Numeric and categorical columns are profiled separately based on
  the dtype reported by the engine.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.engines.base_engine import NUMERIC_DTYPES, BaseEngine

logger = logging.getLogger(__name__)


def profile_dataset(
    df: Any,
    engine: BaseEngine,
) -> dict[str, Any]:
    """Compute a full statistical profile of the dataset.

    Args:
        df: Engine-native DataFrame to profile.
        engine: The active computation engine.

    Returns:
        A dict with keys ``columns``, ``numeric_summary``,
        ``categorical_summary``, ``shape``, and ``memory_bytes``.

    """
    collected = engine.cached_collect(df)
    dtypes = engine.dtypes(df)
    n_rows, n_cols = engine.shape(df)

    numeric_cols: list[str] = []
    categorical_cols: list[str] = []

    for col, dtype_str in dtypes.items():
        if dtype_str in NUMERIC_DTYPES:
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    profile: dict[str, Any] = {
        "shape": {"rows": n_rows, "columns": n_cols},
        "column_names": engine.columns(df),
        "dtypes": dtypes,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "numeric_summary": _profile_numeric(collected, numeric_cols),
        "categorical_summary": _profile_categorical(collected, categorical_cols),
        "memory_bytes": engine.memory_usage(df),
    }

    logger.info(
        "Profiling complete: %d numeric, %d categorical columns.",
        len(numeric_cols),
        len(categorical_cols),
    )
    return profile


def _profile_numeric(collected_df: Any, columns: list[str]) -> dict[str, Any]:
    """Compute descriptive statistics for numeric columns.

    Uses ``.describe()`` on the collected (pandas) DataFrame and
    extracts min, max, mean, std, median, and null count per column.
    """
    if not columns:
        return {}

    result: dict[str, Any] = {}
    stats = collected_df[columns].describe()

    for col in columns:
        col_stats: dict[str, Any] = {}
        for stat_name in ("count", "mean", "std", "min", "25%", "50%", "75%", "max"):
            if stat_name in stats.index:
                val = stats.loc[stat_name, col]
                col_stats[stat_name] = float(val) if hasattr(val, "item") else val
        col_stats["null_count"] = int(collected_df[col].isnull().sum())
        result[col] = col_stats

    return result


def _profile_categorical(collected_df: Any, columns: list[str]) -> dict[str, Any]:
    """Compute distribution info for categorical columns.

    Reports cardinality (number of unique values), top values with
    their counts, and null count per column.
    """
    if not columns:
        return {}

    result: dict[str, Any] = {}

    for col in columns:
        series = collected_df[col]
        value_counts = series.value_counts()
        top_values = {str(val): int(count) for val, count in value_counts.head(10).items()}
        result[col] = {
            "cardinality": int(series.nunique()),
            "null_count": int(series.isnull().sum()),
            "top_values": top_values,
        }

    return result
