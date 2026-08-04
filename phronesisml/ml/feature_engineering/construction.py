"""Feature construction toolkit — engine-light feature builders.

Complementary to ``ml.feature_engineering.engineer.engineer_features``
(the full engine-coupled pipeline).  These are pure, deterministic,
offline builders you can apply individually:

- ``create_interaction_features``: pairwise product columns
- ``create_polynomial_features``: squared / cubed numeric columns
- ``bin_continuous_features``: quantile / equal-width bins
- ``extract_date_features``: year / month / weekday / … from datetimes
- ``variance_threshold_filter``: drop low-variance features
- ``correlation_feature_selector``: keep features correlated with target
- ``feature_importance_report``: ranking by variance + correlation

Every function returns ``(result_df, log_dict)`` and never mutates its
input.  Hard failures raise ``DataTransformError``.
"""

from __future__ import annotations

import itertools
import logging
import warnings
from typing import Any

import pandas as pd

from phronesisml.exceptions import DataTransformError

logger = logging.getLogger(__name__)


def _ensure_numeric(df: pd.DataFrame, columns: list[str]) -> list[str]:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        msg = f"Column(s) not found in DataFrame: {missing}"
        raise DataTransformError(msg)
    numeric = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        msg = "No numeric columns available for the requested transform."
        raise DataTransformError(msg)
    return numeric


def create_interaction_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create pairwise product (interaction) features for numeric columns.

    Args:
        df: Input DataFrame.
        columns: Numeric columns to combine; ``None`` uses all numeric.

    Returns:
        A tuple of (result DataFrame, log dict).  New columns are named
        ``{col_a}__{col_b}``.
    """
    numeric = _ensure_numeric(df, columns if columns is not None else list(df.columns))
    result = df.copy()
    created: list[str] = []
    for a, b in itertools.combinations(numeric, 2):
        name = f"{a}__{b}"
        result[name] = result[a] * result[b]
        created.append(name)

    return result, {
        "action": "create_interaction_features",
        "columns_created": created,
        "n_features_created": len(created),
    }


def create_polynomial_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    degree: int = 2,
    include_bias: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create polynomial (power) features for numeric columns.

    Args:
        df: Input DataFrame.
        columns: Numeric columns to expand; ``None`` uses all numeric.
        degree: Maximum polynomial degree (>= 2).
        include_bias: If ``True``, add a constant ``bias`` column of 1s.

    Returns:
        A tuple of (result DataFrame, log dict).  New columns are named
        ``{col}_p{d}`` for degrees 2..degree.

    Raises:
        DataTransformError: If *degree* < 2.
    """
    if degree < 2:
        msg = f"degree must be >= 2, got {degree}."
        raise DataTransformError(msg)

    numeric = _ensure_numeric(df, columns if columns is not None else list(df.columns))
    result = df.copy()
    created: list[str] = []
    if include_bias:
        result["bias"] = 1
        created.append("bias")
    for col in numeric:
        for d in range(2, degree + 1):
            name = f"{col}_p{d}"
            result[name] = result[col] ** d
            created.append(name)

    return result, {
        "action": "create_polynomial_features",
        "degree": degree,
        "columns_created": created,
        "n_features_created": len(created),
    }


def bin_continuous_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    bins: int = 4,
    strategy: str = "quantile",
    labels: list[str] | None = None,
    suffix: str = "_bin",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Bin continuous numeric columns into categorical buckets.

    Args:
        df: Input DataFrame.
        columns: Numeric columns to bin; ``None`` uses all numeric.
        bins: Number of bins.
        strategy: ``"quantile"`` (equal-frequency) or ``"uniform"``
            (equal-width).
        labels: Optional bin labels (must match *bins* length).
        suffix: Suffix for the new binned columns.

    Returns:
        A tuple of (result DataFrame, log dict).  Original columns are
        kept; binned columns are added with the *suffix*.

    Raises:
        DataTransformError: If *strategy* is unknown or label count
            mismatches.
    """
    if strategy not in ("quantile", "uniform"):
        msg = f"Unknown binning strategy: {strategy!r}. Use 'quantile' or 'uniform'."
        raise DataTransformError(msg)
    if labels is not None and len(labels) != bins:
        msg = f"Expected {bins} labels for {bins} bins, got {len(labels)}."
        raise DataTransformError(msg)

    numeric = _ensure_numeric(df, columns if columns is not None else list(df.columns))
    result = df.copy()
    bin_map: dict[str, Any] = {}
    for col in numeric:
        new_col = f"{col}{suffix}"
        if strategy == "quantile":
            result[new_col] = pd.qcut(result[col], q=bins, labels=labels, duplicates="drop")
        else:
            result[new_col] = pd.cut(result[col], bins=bins, labels=labels)
        bin_map[col] = {"new_column": new_col, "n_bins": int(result[new_col].nunique())}

    return result, {
        "action": "bin_continuous_features",
        "strategy": strategy,
        "bins": bins,
        "bin_map": bin_map,
    }


def extract_date_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    features: tuple[str, ...] = ("year", "month", "day", "weekday"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Extract calendar features from datetime columns.

    Args:
        df: Input DataFrame.
        columns: Datetime columns to expand; ``None`` auto-detects
            datetime dtypes.
        features: Subset of ``"year"``, ``"month"``, ``"day"``,
            ``"weekday"``, ``"hour"``, ``"week"``, ``"dayofyear"``.

    Returns:
        A tuple of (result DataFrame, log dict).  New columns are named
        ``{col}_{feature}``.

    Raises:
        DataTransformError: If a named column is not datetime-like or a
            requested feature is unknown.
    """
    _EXTRACTORS = {
        "year": lambda s: s.dt.year,
        "month": lambda s: s.dt.month,
        "day": lambda s: s.dt.day,
        "weekday": lambda s: s.dt.weekday,
        "hour": lambda s: s.dt.hour,
        "week": lambda s: s.dt.isocalendar().week,
        "dayofyear": lambda s: s.dt.dayofyear,
    }
    unknown = [f for f in features if f not in _EXTRACTORS]
    if unknown:
        msg = f"Unknown date features: {unknown}. Valid: {sorted(_EXTRACTORS)}."
        raise DataTransformError(msg)

    if columns is None:
        columns = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if not columns:
        msg = "No datetime columns found to extract features from."
        raise DataTransformError(msg)

    result = df.copy()
    extracted: list[str] = []
    for col in columns:
        if not pd.api.types.is_datetime64_any_dtype(result[col]):
            try:
                result[col] = pd.to_datetime(result[col])
            except (ValueError, TypeError) as exc:
                msg = f"Column '{col}' is not datetime-like: {exc}"
                raise DataTransformError(msg) from exc
        for feat in features:
            new_col = f"{col}_{feat}"
            result[new_col] = _EXTRACTORS[feat](result[col])
            extracted.append(new_col)

    return result, {
        "action": "extract_date_features",
        "columns": columns,
        "features": list(features),
        "columns_created": extracted,
    }


def variance_threshold_filter(
    df: pd.DataFrame,
    threshold: float = 0.0,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Drop numeric columns with variance below a threshold.

    Args:
        df: Input DataFrame.
        threshold: Minimum variance to keep a column.
        columns: Numeric columns to evaluate; ``None`` uses all numeric.

    Returns:
        A tuple of (result DataFrame, log dict).
    """
    numeric = _ensure_numeric(df, columns if columns is not None else list(df.columns))
    variances = df[numeric].var()
    low_variance = [c for c in numeric if variances.get(c, 0.0) < threshold]

    if not low_variance:
        return df.copy(), {
            "action": "variance_threshold_filter",
            "threshold": threshold,
            "columns_dropped": [],
        }

    result = df.drop(columns=low_variance)
    return result, {
        "action": "variance_threshold_filter",
        "threshold": threshold,
        "columns_dropped": low_variance,
        "variances": {c: round(float(variances[c]), 6) for c in low_variance},
    }


def correlation_feature_selector(
    df: pd.DataFrame,
    target_column: str,
    threshold: float = 0.05,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Keep numeric features whose absolute correlation with the target
    is at least *threshold*.

    Args:
        df: Input DataFrame.
        target_column: Numeric target column.
        threshold: Minimum absolute correlation to retain a feature.
        columns: Candidate numeric features; ``None`` uses all numeric
            except the target.

    Returns:
        A tuple of (result DataFrame, log dict).

    Raises:
        DataTransformError: If the target is not numeric.
    """
    if target_column not in df.columns or not pd.api.types.is_numeric_dtype(df[target_column]):
        msg = f"Target column '{target_column}' must be a numeric column."
        raise DataTransformError(msg)

    candidates = (
        columns
        if columns is not None
        else [c for c in df.columns if c != target_column and pd.api.types.is_numeric_dtype(df[c])]
    )
    numeric = _ensure_numeric(df, candidates)
    numeric = [c for c in numeric if c != target_column]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        correlations = df[numeric].corrwith(df[target_column]).abs()
    keep = [c for c in numeric if correlations.get(c, 0.0) >= threshold]
    drop = [c for c in numeric if c not in keep]

    result = df.copy()
    if drop:
        result = result.drop(columns=drop)

    return result, {
        "action": "correlation_feature_selector",
        "threshold": threshold,
        "features_kept": keep,
        "features_dropped": drop,
        "correlations": {c: round(float(correlations[c]), 6) for c in numeric},
    }


def feature_importance_report(
    df: pd.DataFrame,
    target_column: str | None = None,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Rank features by variance and (optionally) correlation with target.

    A lightweight, deterministic importance proxy that does not train a
    model.

    Args:
        df: Input DataFrame.
        target_column: Optional numeric target for correlation ranking.
        columns: Candidate features; ``None`` uses all numeric.

    Returns:
        A dict with ``ranking`` (list of per-feature dicts, best first),
        ``method``, and ``n_features``.
    """
    numeric = _ensure_numeric(df, columns if columns is not None else list(df.columns))
    if target_column is not None and target_column in numeric:
        numeric = [c for c in numeric if c != target_column]

    ranking: list[dict[str, Any]] = []
    variances = df[numeric].var()
    if target_column is not None and pd.api.types.is_numeric_dtype(df[target_column]):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            correlations = df[numeric].corrwith(df[target_column]).abs()
    else:
        correlations = pd.Series(0.0, index=numeric)

    for col in numeric:
        variance = float(variances.get(col, 0.0))
        corr = float(correlations.get(col, 0.0))
        if pd.isna(variance):
            variance = 0.0
        if pd.isna(corr):
            corr = 0.0
        ranking.append(
            {
                "feature": col,
                "variance": round(variance, 6),
                "correlation": round(corr, 6),
                "score": round(variance + corr, 6),
            }
        )

    ranking.sort(key=lambda r: r["score"], reverse=True)
    return {
        "method": "variance_and_correlation",
        "target_column": target_column,
        "n_features": len(ranking),
        "ranking": ranking,
    }
