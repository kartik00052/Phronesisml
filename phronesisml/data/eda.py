"""EDA toolkit — engine-light analytical functions.

Pure, deterministic, offline functions that return structured dicts for
exploratory data analysis.  They complement the engine-coupled
``data.profilers.stats.profile_dataset`` by exposing targeted, reusable
analyses:

- ``summary_statistics``: descriptive stats per column
- ``correlation_matrix``: numeric correlation table
- ``missing_value_matrix``: null counts / fractions per column
- ``column_distribution``: value counts + entropy for one column
- ``target_distribution``: target class / numeric distribution
- ``outlier_analysis``: IQR and z-score outlier counts
- ``skewness_analysis``: skew / kurtosis per numeric column
- ``type_report``: dtype families per column
- ``data_quality_report``: combined quality overview

No plotting or network dependencies; every function returns JSON-able
dicts (or a pandas correlation frame) so reports can serialize them.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from phronesisml.utils.dtypes import NUMERIC_DTYPES

logger = logging.getLogger(__name__)


def _numeric_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def summary_statistics(df: pd.DataFrame) -> dict[str, Any]:
    """Compute descriptive statistics for every column.

    Args:
        df: Input DataFrame.

    Returns:
        A dict mapping column → stats dict (count, null count, unique,
        and numeric describe fields where applicable).
    """
    result: dict[str, Any] = {}
    for col in df.columns:
        series = df[col]
        stats: dict[str, Any] = {
            "count": int(series.count()),
            "null_count": int(series.isnull().sum()),
            "unique": int(series.nunique()),
        }
        if pd.api.types.is_numeric_dtype(series):
            for key in ("mean", "std", "min", "25%", "50%", "75%", "max"):
                if key in series.describe():
                    val = series.describe()[key]
                    stats[key] = float(val) if pd.notna(val) else None
        else:
            top = series.value_counts().head(5)
            stats["top_values"] = {str(k): int(v) for k, v in top.items()}
        result[col] = stats
    return result


def correlation_matrix(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "pearson",
) -> dict[str, Any]:
    """Compute a numeric correlation matrix.

    Args:
        df: Input DataFrame.
        columns: Numeric columns to correlate; ``None`` uses all numeric.
        method: ``"pearson"``, ``"spearman"``, or ``"kendall"``.

    Returns:
        A dict with ``columns`` (list), ``matrix`` (dict of column →
        dict of correlation values), and ``method``.
    """
    numeric_cols = _numeric_cols(df)
    target_cols = columns if columns is not None else numeric_cols
    target_cols = [c for c in target_cols if pd.api.types.is_numeric_dtype(df[c])]

    corr = df[target_cols].corr(method=method)
    matrix: dict[str, dict[str, float | None]] = {}
    for col in target_cols:
        matrix[col] = {
            other: (float(corr.loc[col, other]) if pd.notna(corr.loc[col, other]) else None)
            for other in target_cols
        }
    return {"columns": target_cols, "matrix": matrix, "method": method}


def missing_value_matrix(df: pd.DataFrame) -> dict[str, Any]:
    """Analyse missing values across the DataFrame.

    Args:
        df: Input DataFrame.

    Returns:
        A dict with ``total_cells``, ``missing_cells``,
        ``overall_fraction``, and per-column ``count`` / ``fraction``.
    """
    missing = df.isnull()
    per_column = {
        col: {
            "count": int(missing[col].sum()),
            "fraction": round(float(missing[col].mean()), 6),
        }
        for col in df.columns
    }
    total_cells = int(df.shape[0] * df.shape[1])
    missing_cells = int(missing.sum().sum())
    return {
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "overall_fraction": round(missing_cells / total_cells, 6) if total_cells else 0.0,
        "columns": per_column,
    }


def column_distribution(df: pd.DataFrame, column: str) -> dict[str, Any]:
    """Describe the distribution of a single column.

    Args:
        df: Input DataFrame.
        column: Column name.

    Returns:
        A dict with ``column``, ``dtype``, ``null_count``,
        ``cardinality``, ``entropy`` (for categorical), and
        ``value_counts`` (top 10) or ``numeric_bins`` (histogram of the
        value range).
    """
    series = df[column]
    base: dict[str, Any] = {
        "column": column,
        "dtype": str(series.dtype),
        "null_count": int(series.isnull().sum()),
        "cardinality": int(series.nunique()),
    }
    if pd.api.types.is_numeric_dtype(series):
        clean = series.dropna()
        if clean.empty:
            base["numeric_bins"] = []
            return base
        counts, edges = np.histogram(clean, bins=10)
        base["numeric_bins"] = [
            {
                "lower": round(float(edges[i]), 4),
                "upper": round(float(edges[i + 1]), 4),
                "count": int(c),
            }
            for i, c in enumerate(counts)
        ]
        base["min"] = float(clean.min())
        base["max"] = float(clean.max())
        base["mean"] = float(clean.mean())
    else:
        counts = series.value_counts(dropna=True)
        probs = counts / counts.sum()
        entropy = -float((probs * np.log2(probs)).sum()) if len(probs) > 0 else 0.0
        base["entropy"] = round(entropy, 4)
        base["value_counts"] = {str(k): int(v) for k, v in counts.head(10).items()}
    return base


def target_distribution(
    df: pd.DataFrame,
    target_column: str,
) -> dict[str, Any]:
    """Analyse the target column distribution.

    Args:
        df: Input DataFrame.
        target_column: Target column name.

    Returns:
        A dict describing whether the target is numeric or categorical,
        plus class counts (categorical) or distribution stats (numeric).
    """
    series = df[target_column]
    base: dict[str, Any] = {
        "target_column": target_column,
        "dtype": str(series.dtype),
        "null_count": int(series.isnull().sum()),
    }
    if pd.api.types.is_numeric_dtype(series):
        base["kind"] = "numeric"
        base.update(summary_statistics(df[[target_column]])[target_column])
    else:
        counts = series.value_counts(dropna=True)
        base["kind"] = "categorical"
        base["n_classes"] = int(series.nunique())
        base["class_counts"] = {str(k): int(v) for k, v in counts.items()}
        base["class_fractions"] = {
            str(k): round(float(v / len(series)), 4) for k, v in counts.items()
        }
    return base


def outlier_analysis(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "iqr",
    factor: float = 1.5,
) -> dict[str, Any]:
    """Count outliers per numeric column.

    Args:
        df: Input DataFrame.
        columns: Numeric columns to analyse; ``None`` uses all numeric.
        method: ``"iqr"`` (Tukey fences) or ``"zscore"`` (|z| > 3).
        factor: IQR multiplier for the ``"iqr"`` method.

    Returns:
        A dict with ``method`` and per-column outlier counts / bounds.
    """
    target_cols = columns if columns is not None else _numeric_cols(df)
    target_cols = [c for c in target_cols if pd.api.types.is_numeric_dtype(df[c])]

    per_column: dict[str, Any] = {}
    for col in target_cols:
        series = df[col].dropna()
        n_outliers = 0
        bounds: dict[str, float] | None = None
        if method == "iqr":
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - factor * iqr
            upper = q3 + factor * iqr
            bounds = {"lower": round(float(lower), 6), "upper": round(float(upper), 6)}
            n_outliers = int(((series < lower) | (series > upper)).sum())
        elif method == "zscore":
            mean = series.mean()
            std = series.std()
            if std > 0:
                z = ((series - mean) / std).abs()
                n_outliers = int((z > 3).sum())
        else:
            msg = f"Unknown outlier method: {method!r}. Use 'iqr' or 'zscore'."
            raise ValueError(msg)
        per_column[col] = {"outliers": n_outliers, "total": int(len(series)), "bounds": bounds}

    return {"method": method, "columns": per_column}


def skewness_analysis(df: pd.DataFrame, columns: list[str] | None = None) -> dict[str, Any]:
    """Report skewness and kurtosis for numeric columns.

    Args:
        df: Input DataFrame.
        columns: Numeric columns; ``None`` uses all numeric.

    Returns:
        A dict mapping column → ``{"skewness", "kurtosis"}``.
    """
    target_cols = columns if columns is not None else _numeric_cols(df)
    result: dict[str, Any] = {}
    for col in target_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        clean = df[col].dropna()
        if len(clean) < 2:
            result[col] = {"skewness": None, "kurtosis": None}
            continue
        result[col] = {
            "skewness": round(float(clean.skew()), 4),
            "kurtosis": round(float(clean.kurtosis()), 4),
        }
    return result


def type_report(df: pd.DataFrame) -> dict[str, Any]:
    """Report dtype families for every column.

    Args:
        df: Input DataFrame.

    Returns:
        A dict with ``columns`` (list), ``numeric``, ``categorical``,
        ``datetime`` lists, and per-column ``dtypes`` + ``families``.
    """
    families: dict[str, str] = {}
    numeric: list[str] = []
    categorical: list[str] = []
    datetime: list[str] = []
    dtypes: dict[str, str] = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        dtypes[col] = dtype
        if dtype in NUMERIC_DTYPES:
            family = "numeric"
            numeric.append(col)
        elif dtype.startswith("datetime") or pd.api.types.is_datetime64_any_dtype(df[col]):
            family = "datetime"
            datetime.append(col)
        else:
            family = "categorical"
            categorical.append(col)
        families[col] = family
    return {
        "columns": list(df.columns),
        "dtypes": dtypes,
        "families": families,
        "numeric": numeric,
        "categorical": categorical,
        "datetime": datetime,
    }


def data_quality_report(df: pd.DataFrame) -> dict[str, Any]:
    """Produce a combined data-quality overview.

    Args:
        df: Input DataFrame.

    Returns:
        A dict with shape, type report, missing-value matrix, duplicate
        counts, and a per-column quality score.
    """
    missing = missing_value_matrix(df)
    dtypes = type_report(df)

    per_column: dict[str, Any] = {}
    for col in df.columns:
        n_null = missing["columns"][col]["count"]
        n_rows = df.shape[0]
        completeness = round(1.0 - (n_null / n_rows if n_rows else 0.0), 4)
        per_column[col] = {
            "dtype": dtypes["dtypes"][col],
            "family": dtypes["families"][col],
            "cardinality": int(df[col].nunique()),
            "null_count": n_null,
            "completeness": completeness,
        }

    return {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "duplicate_rows": int(df.duplicated().sum()),
        "overall_missing_fraction": missing["overall_fraction"],
        "columns": per_column,
    }
