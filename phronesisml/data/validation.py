"""Data validation toolkit — schema, constraint, and quality checks.

Pure, deterministic, offline functions that validate a Pandas DataFrame
and return structured reports.  Every check returns a dict with at least
``passed`` (bool), ``violations`` (list[str]), and check-specific details,
so results compose into ``generate_validation_report``.

Hard errors (e.g. an empty DataFrame with zero columns) raise
``DataValidationError``; soft rule violations are reported, not raised.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from phronesisml.exceptions import DataValidationError
from phronesisml.utils.dtypes import NUMERIC_DTYPES

logger = logging.getLogger(__name__)


def _ensure_non_empty(df: pd.DataFrame) -> None:
    if df.shape[1] == 0:
        msg = "Validation failed: DataFrame has zero columns."
        raise DataValidationError(msg)
    if df.shape[0] == 0:
        msg = "Validation failed: DataFrame has zero rows."
        raise DataValidationError(msg)


def validate_missing_values(
    df: pd.DataFrame,
    max_fraction: float = 1.0,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Check missing-value fractions against a threshold.

    Args:
        df: Input DataFrame.
        max_fraction: Maximum allowed missing fraction per column (0..1).
        columns: Columns to check; ``None`` checks all columns.

    Returns:
        A dict with ``passed``, ``violations``, and per-column fractions.
    """
    cols = columns if columns is not None else list(df.columns)
    fractions = {c: round(float(df[c].isnull().mean()), 6) for c in cols}
    violations = [
        f"Column '{c}' has {f:.1%} missing values (max allowed {max_fraction:.1%})."
        for c, f in fractions.items()
        if f > max_fraction
    ]
    return {
        "passed": not violations,
        "violations": violations,
        "missing_fraction": fractions,
        "max_fraction": max_fraction,
    }


def validate_duplicate_rows(
    df: pd.DataFrame,
    subset: list[str] | None = None,
) -> dict[str, Any]:
    """Check for fully (or subset-wise) duplicate rows.

    Args:
        df: Input DataFrame.
        subset: Columns to consider; ``None`` checks full rows.

    Returns:
        A dict with ``passed``, ``violations``, and duplicate counts.
    """
    dup = int(df.duplicated(subset=subset).sum())
    violations = [] if dup == 0 else [f"Found {dup} duplicate row(s)."]
    return {"passed": not violations, "violations": violations, "duplicate_rows": dup}


def validate_column_types(
    df: pd.DataFrame,
    expected_types: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Check that columns have the expected dtype family.

    Args:
        df: Input DataFrame.
        expected_types: Column → expected dtype string (e.g. ``"int64"``)
            or dtype family (``"numeric"``, ``"datetime"``, ``"categorical"``).
            If ``None``, only internal consistency is checked (no failures).

    Returns:
        A dict with ``passed``, ``violations``, and observed dtypes.
    """
    dtypes = {c: str(dtype) for c, dtype in df.dtypes.items()}
    violations: list[str] = []

    if expected_types:
        for col, expected in expected_types.items():
            if col not in dtypes:
                violations.append(f"Expected column '{col}' is missing.")
                continue
            observed = dtypes[col]
            family = (
                "numeric"
                if observed in NUMERIC_DTYPES
                else ("datetime" if observed.startswith("datetime") else "categorical")
            )
            matches = expected in (observed, family)
            if not matches:
                violations.append(
                    f"Column '{col}': expected dtype {expected!r}, observed {observed!r}."
                )

    return {"passed": not violations, "violations": violations, "dtypes": dtypes}


def validate_unique_constraints(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Check that specified columns contain only unique values.

    Args:
        df: Input DataFrame.
        columns: Columns that must be unique; ``None`` checks every column.

    Returns:
        A dict with ``passed``, ``violations``, and per-column duplicate counts.
    """
    cols = columns if columns is not None else list(df.columns)
    counts: dict[str, int] = {}
    violations: list[str] = []
    for c in cols:
        n_dup = int(df[c].duplicated().sum())
        counts[c] = n_dup
        if n_dup:
            violations.append(f"Column '{c}' is not unique ({n_dup} duplicate values).")
    return {"passed": not violations, "violations": violations, "duplicate_counts": counts}


def validate_constraints(
    df: pd.DataFrame,
    constraints: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate per-column value constraints.

    Supported constraints per column:
    - ``min``: minimum allowed value (inclusive)
    - ``max``: maximum allowed value (inclusive)
    - ``allowed``: list of allowed values
    - ``not_null``: column must not contain nulls
    - ``unique``: column must be unique

    Args:
        df: Input DataFrame.
        constraints: Column → constraint dict.

    Returns:
        A dict with ``passed``, ``violations``, and ``constraints``.

    Raises:
        DataValidationError: If a constraint column does not exist.
    """
    violations: list[str] = []

    for col, rules in constraints.items():
        if col not in df.columns:
            msg = f"Constraint references missing column '{col}'."
            raise DataValidationError(msg)
        series = df[col]

        if rules.get("not_null"):
            n_nulls = int(series.isnull().sum())
            if n_nulls:
                violations.append(
                    f"Column '{col}' has {n_nulls} null value(s) but must be null-free."
                )

        if rules.get("unique"):
            n_dup = int(series.duplicated().sum())
            if n_dup:
                violations.append(f"Column '{col}' must be unique; found {n_dup} duplicate(s).")

        if "allowed" in rules:
            allowed = set(rules["allowed"])
            bad = series.dropna().unique()
            offending = [v for v in bad if v not in allowed]
            if offending:
                violations.append(
                    f"Column '{col}' contains values outside the allowed set: {offending[:5]}."
                )

        lower = rules.get("min")
        upper = rules.get("max")
        if lower is not None or upper is not None:
            numeric = pd.to_numeric(series, errors="coerce")
            if lower is not None and int(numeric.lt(lower).sum()):
                violations.append(f"Column '{col}' has values below min={lower}.")
            if upper is not None and int(numeric.gt(upper).sum()):
                violations.append(f"Column '{col}' has values above max={upper}.")

    return {"passed": not violations, "violations": violations, "constraints": constraints}


def validate_datetime_columns(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Check whether columns are datetime-like (dtype or parseable).

    Args:
        df: Input DataFrame.
        columns: Columns to check; ``None`` checks all object/string columns.

    Returns:
        A dict with ``passed``, ``violations``, and a per-column boolean map.
    """
    candidates = columns if columns is not None else list(df.columns)
    status: dict[str, bool] = {}
    violations: list[str] = []
    for c in candidates:
        series = df[c]
        is_dt = pd.api.types.is_datetime64_any_dtype(series)
        if not is_dt and series.dtype == "object":
            try:
                pd.to_datetime(series.dropna(), errors="raise")
                is_dt = True
            except (ValueError, TypeError):
                is_dt = False
        status[c] = is_dt
        if not is_dt:
            violations.append(f"Column '{c}' is not datetime-like.")
    return {"passed": not violations, "violations": violations, "is_datetime": status}


def validate_categorical_columns(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Check whether columns are categorical (low-cardinality object/bool).

    Args:
        df: Input DataFrame.
        columns: Columns to check; ``None`` checks all non-numeric columns.

    Returns:
        A dict with ``passed``, ``violations``, and a per-column boolean map.
    """
    candidates = (
        columns
        if columns is not None
        else [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    )
    status: dict[str, bool] = {}
    violations: list[str] = []
    for c in candidates:
        cardinality = int(df[c].nunique(dropna=True))
        is_cat = cardinality <= 100
        status[c] = is_cat
        if not is_cat:
            violations.append(
                f"Column '{c}' has high cardinality ({cardinality}) — not categorical."
            )
    return {"passed": not violations, "violations": violations, "is_categorical": status}


def validate_numeric_columns(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Check whether columns are numeric.

    Args:
        df: Input DataFrame.
        columns: Columns to check; ``None`` checks all columns.

    Returns:
        A dict with ``passed``, ``violations``, and a per-column boolean map.
    """
    cols = columns if columns is not None else list(df.columns)
    status: dict[str, bool] = {c: bool(pd.api.types.is_numeric_dtype(df[c])) for c in cols}
    violations = [f"Column '{c}' is not numeric." for c, ok in status.items() if not ok]
    return {"passed": not violations, "violations": violations, "is_numeric": status}


def validate_target_column(
    df: pd.DataFrame,
    target_column: str,
    task_type: str | None = None,
) -> dict[str, Any]:
    """Validate that a target column is suitable for the given task.

    Args:
        df: Input DataFrame.
        target_column: Name of the target column.
        task_type: Optional task hint (``"classification"``/``"regression"``).

    Returns:
        A dict with ``passed``, ``violations``, and target metadata.

    Raises:
        DataValidationError: If the target column is missing or empty.
    """
    if target_column not in df.columns:
        msg = f"Target column '{target_column}' does not exist."
        raise DataValidationError(msg)
    series = df[target_column]
    if series.isnull().all():
        msg = f"Target column '{target_column}' is entirely null."
        raise DataValidationError(msg)

    violations: list[str] = []
    n_unique = int(series.nunique(dropna=True))

    if task_type == "classification":
        if not pd.api.types.is_numeric_dtype(series) and not n_unique:
            violations.append("Classification target has no unique values.")
        elif n_unique < 2:
            violations.append("Classification target must have at least 2 classes.")
    elif task_type == "regression" and not pd.api.types.is_numeric_dtype(series):
        violations.append("Regression target must be numeric.")

    return {
        "passed": not violations,
        "violations": violations,
        "target_column": target_column,
        "unique_values": n_unique,
        "null_count": int(series.isnull().sum()),
        "dtype": str(series.dtype),
    }


def validate_feature_columns(
    df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str | None = None,
) -> dict[str, Any]:
    """Validate that feature columns exist, are non-empty, and differ from the target.

    Args:
        df: Input DataFrame.
        feature_columns: Feature column names to validate.
        target_column: Optional target column to exclude.

    Returns:
        A dict with ``passed``, ``violations``, and resolved feature list.

    Raises:
        DataValidationError: If a feature column is missing or entirely null.
    """
    missing = [c for c in feature_columns if c not in df.columns]
    if missing:
        msg = f"Feature column(s) do not exist: {missing}"
        raise DataValidationError(msg)

    violations: list[str] = []
    empty = [c for c in feature_columns if df[c].isnull().all()]
    if empty:
        violations.append(f"Feature column(s) are entirely null: {empty}")
    if target_column and target_column in feature_columns:
        violations.append(f"Target column '{target_column}' appears in the feature list.")

    resolved = [c for c in feature_columns if c != target_column]
    return {
        "passed": not violations,
        "violations": violations,
        "feature_columns": resolved,
        "n_features": len(resolved),
    }


def validate_schema(
    df: pd.DataFrame,
    schema: dict[str, str],
) -> dict[str, Any]:
    """Validate a DataFrame against a declared schema.

    A schema is a mapping ``column → expected dtype string``.  Numeric
    families (``"numeric"``) accept any numeric dtype; otherwise the dtype
    must match exactly.

    Args:
        df: Input DataFrame.
        schema: Column → expected dtype (or dtype family).

    Returns:
        A dict with ``passed``, ``violations``, ``missing_columns``, and
        ``dtype_mismatches``.
    """
    missing = [c for c in schema if c not in df.columns]
    mismatches: dict[str, str] = {}
    for col, expected in schema.items():
        if col not in df.columns:
            continue
        observed = str(df[col].dtype)
        family = (
            "numeric"
            if observed in NUMERIC_DTYPES
            else ("datetime" if observed.startswith("datetime") else "categorical")
        )
        if expected not in (observed, family):
            mismatches[col] = f"expected {expected}, got {observed}"

    violations = [f"Missing column: {c}" for c in missing] + [
        f"Column '{c}': {reason}." for c, reason in mismatches.items()
    ]
    return {
        "passed": not violations,
        "violations": violations,
        "missing_columns": missing,
        "dtype_mismatches": mismatches,
        "schema": schema,
    }


def infer_schema(df: pd.DataFrame) -> dict[str, Any]:
    """Infer a schema (dtype + nullability + uniqueness) from a DataFrame.

    Args:
        df: Input DataFrame.

    Returns:
        A dict mapping column → ``{"dtype", "family", "nullable", "unique"}``
        plus ``n_columns``.
    """
    schema: dict[str, Any] = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        family = (
            "numeric"
            if dtype in NUMERIC_DTYPES
            else ("datetime" if dtype.startswith("datetime") else "categorical")
        )
        schema[col] = {
            "dtype": dtype,
            "family": family,
            "nullable": bool(df[col].isnull().any()),
            "unique": bool(df[col].nunique(dropna=True) == df[col].notna().sum()),
        }
    return {"n_columns": int(df.shape[1]), "schema": schema}


def validate_dataset(
    df: pd.DataFrame,
    schema: dict[str, str] | None = None,
    target_column: str | None = None,
    max_missing_fraction: float = 1.0,
) -> dict[str, Any]:
    """Run a standard validation battery over a DataFrame.

    Combines schema, missing-value, duplicate, and (optionally) target
    checks into one report.

    Args:
        df: Input DataFrame.
        schema: Optional declared schema.
        target_column: Optional target column to validate.
        max_missing_fraction: Missing-value threshold for each column.

    Returns:
        A dict with ``passed``, ``violations``, and individual check reports.

    Raises:
        DataValidationError: For structurally invalid input (zero rows/columns).
    """
    _ensure_non_empty(df)

    checks: dict[str, Any] = {
        "missing_values": validate_missing_values(df, max_fraction=max_missing_fraction),
        "duplicate_rows": validate_duplicate_rows(df),
    }
    if schema is not None:
        checks["schema"] = validate_schema(df, schema)
    if target_column is not None:
        checks["target"] = validate_target_column(df, target_column)

    violations: list[str] = []
    for check in checks.values():
        violations.extend(check["violations"])

    return {
        "passed": not violations,
        "violations": violations,
        "n_checks": len(checks),
        "checks": checks,
    }


def generate_validation_report(
    df: pd.DataFrame,
    schema: dict[str, str] | None = None,
    target_column: str | None = None,
) -> dict[str, Any]:
    """Generate a comprehensive validation report.

    Args:
        df: Input DataFrame.
        schema: Optional declared schema.
        target_column: Optional target column.

    Returns:
        A dict with ``passed``, ``violations``, ``summary``, and ``details``
        containing every individual check.
    """
    _ensure_non_empty(df)

    details: dict[str, Any] = {
        "missing_values": validate_missing_values(df),
        "duplicate_rows": validate_duplicate_rows(df),
        "unique_constraints": validate_unique_constraints(df, columns=[]),
        "column_types": validate_column_types(df),
        "numeric_columns": validate_numeric_columns(df),
        "categorical_columns": validate_categorical_columns(df),
        "datetime_columns": validate_datetime_columns(df, columns=[]),
        "inferred_schema": infer_schema(df),
    }
    if schema is not None:
        details["schema"] = validate_schema(df, schema)
    if target_column is not None:
        details["target"] = validate_target_column(df, target_column)

    # Type-family checks are informational maps, not pass/fail gates.
    _informational = {"numeric_columns", "categorical_columns", "datetime_columns"}
    violations: list[str] = []
    for name, check in details.items():
        if name in _informational or not isinstance(check, dict):
            continue
        violations.extend(check.get("violations", []))

    return {
        "passed": not violations,
        "violations": violations,
        "n_violations": len(violations),
        "summary": {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "null_total": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
        },
        "details": details,
    }
