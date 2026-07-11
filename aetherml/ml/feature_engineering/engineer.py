"""Feature engineering — transforming validated data into model-ready features.

All functions receive an engine-native DataFrame, a ``BaseEngine``
instance, and configuration parameters.  They use ``engine.collect()``
to materialise the data and ``engine.dtypes()`` for type-aware
operations.  No direct pandas or polars imports are used here — all
data access flows through the engine.

Distinction from ETL cleaning (``data.transformers.cleaning``):
- ETL runs *before* target detection and operates on ALL columns
  (drops nulls, label-encodes every categorical).  Its job is to
  produce a clean DataFrame.
- Feature Engineering runs *after* target detection.  It:
  1. Handles any *remaining* nulls (may use a different strategy than
     ETL — e.g. ETL dropped nulls but FE fills residuals).
  2. Encodes categoricals *excluding* the target column (the target
     must not be transformed by feature engineering).
  3. Scales numeric features (again excluding the target).
  4. Detects and flags outliers (flag by default, drop only if
     explicitly configured).
  5. Selects features via variance threshold and correlation-with-target
     (for supervised cases).

This two-stage design is intentional: ETL provides a clean base;
FE adds model-ready signal on top.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from aetherml.engines.base_engine import BaseEngine
from aetherml.exceptions import DataTransformError

logger = logging.getLogger(__name__)

# Dtypes that the engine reports as numeric
_NUMERIC_DTYPES = frozenset(
    {
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float16",
        "float32",
        "float64",
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "Float32",
        "Float64",
    }
)

# Variance threshold: features with variance below this are dropped.
_VARIANCE_THRESHOLD = 0.01

# Correlation threshold: features with absolute correlation to the
# target below this are dropped (supervised feature selection).
_CORRELATION_THRESHOLD = 0.05

# IQR multiplier for outlier detection.
_IQR_MULTIPLIER = 1.5


def engineer_features(
    df: Any,
    engine: BaseEngine,
    target_column: str | None = None,
    null_strategy: str = "fill",
    fill_value: Any = 0,
    scale_numeric: bool = True,
    detect_outliers: bool = True,
    drop_outlier_rows: bool = False,
    select_features: bool = True,
) -> tuple[Any, dict[str, Any]]:
    """Run the full feature engineering pipeline.

    Args:
        df: Engine-native DataFrame (validated data).
        engine: The active computation engine.
        target_column: Name of the target column (excluded from all
            transforms).  If ``None``, no column is excluded.
        null_strategy: How to handle remaining nulls (``"fill"``
            or ``"flag"``).  ``"drop"`` is not used here — ETL already
            dropped nulls; FE fills any residuals.
        fill_value: Value to use when ``null_strategy="fill"``.
        scale_numeric: Whether to min-max scale numeric features.
        detect_outliers: Whether to flag outlier rows.
        drop_outlier_rows: If ``True``, drop outlier rows instead of
            flagging them.  Default ``False`` (flag only).
        select_features: Whether to apply variance-threshold and
            correlation-based feature selection.

    Returns:
        A tuple of ``(transformed_df, log_entry_dict)``.

    """
    collected = engine.collect(df)
    dtypes = engine.dtypes(df)
    columns = engine.columns(df)

    transform_log: list[dict[str, Any]] = []
    result = collected.copy()

    # Determine feature columns (exclude target)
    feature_cols = [c for c in columns if c != target_column]
    numeric_cols = [c for c in feature_cols if dtypes.get(c, "") in _NUMERIC_DTYPES]
    categorical_cols = [c for c in feature_cols if c not in numeric_cols]

    # ── Step 1: Handle remaining nulls ───────────────────────────────
    result, null_log = _handle_remaining_nulls(
        result,
        feature_cols,
        null_strategy,
        fill_value,
    )
    transform_log.append(null_log)

    # ── Step 2: Encode categoricals (excluding target) ───────────────
    if categorical_cols:
        result, encode_log = _encode_features(result, categorical_cols)
        transform_log.append(encode_log)

    # ── Step 3: Scale numeric features (excluding target) ────────────
    if scale_numeric and numeric_cols:
        result, scale_log = _scale_numeric(result, numeric_cols)
        transform_log.append(scale_log)

    # ── Step 4: Outlier detection ────────────────────────────────────
    if detect_outliers:
        result, outlier_log = _detect_outliers(
            result,
            numeric_cols,
            drop_outlier_rows,
        )
        transform_log.append(outlier_log)

    # ── Step 5: Feature selection ────────────────────────────────────
    if select_features and target_column is not None:
        result, select_log = _select_features(
            result,
            feature_cols,
            target_column,
        )
        transform_log.append(select_log)

    # Collect the final feature names (exclude target from result)
    if target_column is not None and target_column in result.columns:
        result = result.drop(columns=[target_column])
    final_cols = list(result.columns)

    logger.info(
        "Feature engineering complete: %d rows, %d features (from %d columns).",
        len(result),
        len(final_cols),
        len(feature_cols),
    )

    log_entry: dict[str, Any] = {
        "action": "engineer_features",
        "steps": transform_log,
        "original_columns": columns,
        "feature_columns": final_cols,
        "target_excluded": target_column,
    }
    return result, log_entry


def _handle_remaining_nulls(
    df: Any,
    feature_cols: list[str],
    strategy: str,
    fill_value: Any,
) -> tuple[Any, dict[str, Any]]:
    """Fill or flag any nulls remaining after ETL."""
    target_cols = [c for c in feature_cols if df[c].isnull().any()]

    if not target_cols:
        return df, {"action": "fill_nulls", "columns_affected": 0}

    if strategy == "fill":
        import pandas as pd

        with pd.option_context("future.no_silent_downcasting", True):
            df[target_cols] = df[target_cols].fillna(fill_value).infer_objects(copy=False)
    elif strategy == "flag":
        for col in target_cols:
            df[f"{col}_is_null"] = df[col].isnull().astype(int)
    else:
        msg = f"Unknown null strategy for FE: {strategy!r}. Use 'fill' or 'flag'."
        raise DataTransformError(msg)

    return df, {
        "action": "fill_nulls",
        "strategy": strategy,
        "columns_affected": len(target_cols),
    }


def _encode_features(
    df: Any,
    categorical_cols: list[str],
) -> tuple[Any, dict[str, Any]]:
    """Label-encode categorical feature columns (excluding target)."""
    import pandas as pd

    encoding_maps: dict[str, dict[Any, int]] = {}

    for col in categorical_cols:
        if df[col].dtype == "object":
            codes, uniques = pd.factorize(df[col])
            df[col] = codes
            encoding_maps[col] = {v: int(i) for i, v in enumerate(uniques)}

    return df, {
        "action": "encode_features",
        "columns_encoded": list(encoding_maps.keys()),
        "encoding_maps": encoding_maps,
    }


def _scale_numeric(
    df: Any,
    numeric_cols: list[str],
) -> tuple[Any, dict[str, Any]]:
    """Min-max scale numeric feature columns."""
    scaling_params: dict[str, dict[str, float]] = {}

    for col in numeric_cols:
        col_min = float(df[col].min())
        col_max = float(df[col].max())
        col_range = col_max - col_min

        if col_range == 0:
            df[col] = 0.0
        else:
            df[col] = (df[col] - col_min) / col_range

        scaling_params[col] = {"min": col_min, "max": col_max}

    return df, {
        "action": "scale_numeric",
        "columns_scaled": numeric_cols,
        "scaling_params": scaling_params,
    }


def _detect_outliers(
    df: Any,
    numeric_cols: list[str],
    drop: bool,
) -> tuple[Any, dict[str, Any]]:
    """Flag (or drop) rows with outliers based on IQR.

    Outliers are defined as values outside
    ``[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`` for any numeric column.
    """
    if not numeric_cols:
        return df, {"action": "detect_outliers", "outliers_flagged": 0, "rows_dropped": 0}

    outlier_mask = df[numeric_cols].apply(_is_outlier_iqr)
    outlier_rows = outlier_mask.any(axis=1)
    n_outliers = int(outlier_rows.sum())

    if drop and n_outliers > 0:
        df = df[~outlier_rows]
        return df, {
            "action": "detect_outliers",
            "method": "iqr",
            "outliers_detected": n_outliers,
            "rows_dropped": n_outliers,
        }

    # Flag outliers
    if n_outliers > 0:
        df["outlier_flag"] = outlier_rows.astype(int)

    return df, {
        "action": "detect_outliers",
        "method": "iqr",
        "outliers_detected": n_outliers,
        "rows_dropped": 0,
    }


def _is_outlier_iqr(series: Any) -> Any:
    """Return a boolean mask for IQR-based outliers in a single column."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - _IQR_MULTIPLIER * iqr
    upper = q3 + _IQR_MULTIPLIER * iqr
    return (series < lower) | (series > upper)


def _select_features(
    df: Any,
    feature_cols: list[str],
    target_column: str,
) -> tuple[Any, dict[str, Any]]:
    """Select features via variance threshold and correlation with target.

    Drops features with variance below ``_VARIANCE_THRESHOLD`` or
    absolute correlation with the target below ``_CORRELATION_THRESHOLD``.
    """
    numeric_features = [
        c
        for c in feature_cols
        if c in df.columns and df[c].dtype in ("float64", "int64", "float32", "int32")
    ]

    if not numeric_features or target_column not in df.columns:
        return df, {"action": "select_features", "features_dropped": []}

    # Variance threshold
    variances = df[numeric_features].var()
    low_var = [c for c in numeric_features if variances.get(c, 0) < _VARIANCE_THRESHOLD]

    # Correlation with target — only if target is numeric
    low_corr: list[str] = []
    target_col_obj = df[target_column]
    target_is_numeric = target_col_obj.dtype in ("float64", "int64", "float32", "int32", "float16")
    if target_is_numeric:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            correlations = df[numeric_features].corrwith(target_col_obj).abs()
        low_corr = [c for c in numeric_features if correlations.get(c, 0) < _CORRELATION_THRESHOLD]

    # Union of features to drop
    to_drop = list(set(low_var + low_corr))

    if not to_drop:
        return df, {"action": "select_features", "features_dropped": []}

    result = df.drop(columns=to_drop)
    return result, {
        "action": "select_features",
        "features_dropped": to_drop,
        "low_variance": low_var,
        "low_correlation": low_corr,
    }
