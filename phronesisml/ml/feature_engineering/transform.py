"""Transform recipe — reproducible re-application of feature engineering.

``engineer_features`` (``ml.feature_engineering.engineer``) records every
deterministic transform it applies (null fill, label encoding, min-max
scaling, feature selection) in its log entry.  This module turns that log
into a serializable *recipe* that can be applied to unseen rows at
prediction time so ``predict()`` reproduces the exact feature space the
trained model saw — without retraining and without duplicating logic.

Recipes are plain dicts (JSON-serializable) so they persist cleanly into
the artifact suite (``feature_metadata.json``).

Public functions:
- ``build_transform_recipe``: derive a recipe from a FE log entry.
- ``apply_transform_recipe``: apply a recipe to a raw DataFrame.
"""

from __future__ import annotations

from typing import Any

from phronesisml.exceptions import DataTransformError

_RECIPE_VERSION = 1


def build_transform_recipe(
    log_entry: dict[str, Any],
    target_column: str | None = None,
) -> dict[str, Any]:
    """Build a serializable transform recipe from a feature-engineering log.

    Args:
        log_entry: The log entry returned by ``engineer_features``.
        target_column: The excluded target column (if any).

    Returns:
        A JSON-serializable recipe dict with keys ``version``,
        ``null_strategy``, ``fill_value``, ``categorical_columns``,
        ``encoding_maps``, ``numeric_columns``, ``scaling_params``,
        ``feature_columns``, and ``target_column``.
    """
    steps = {s.get("action"): s for s in log_entry.get("steps", []) if isinstance(s, dict)}
    encode = steps.get("encode_features", {})
    scale = steps.get("scale_numeric", {})
    fill = steps.get("fill_nulls", {})

    return {
        "version": _RECIPE_VERSION,
        "null_strategy": fill.get("strategy", "fill"),
        "fill_value": 0,
        "categorical_columns": list(encode.get("columns_encoded", [])),
        "encoding_maps": dict(encode.get("encoding_maps", {})),
        "numeric_columns": list(scale.get("columns_scaled", [])),
        "scaling_params": dict(scale.get("scaling_params", {})),
        "feature_columns": list(log_entry.get("feature_columns", [])),
        "target_column": target_column,
    }


def apply_transform_recipe(
    df: Any,
    recipe: dict[str, Any],
) -> Any:
    """Apply a transform recipe to new (raw) rows.

    Reproduces, in order: target removal, null fill, categorical label
    encoding (unseen labels map to ``0``), min-max scaling, and final
    feature selection/ordering — matching ``engineer_features``.

    Args:
        df: A pandas DataFrame shaped like the data the pipeline was
            trained on (the target column, if present, is ignored).
        recipe: A recipe produced by :func:`build_transform_recipe`.

    Returns:
        A ``pandas.DataFrame`` of engineered features, with columns in
        recipe order, ready for ``model.predict()``.

    Raises:
        DataTransformError: If the input is missing recipe columns, or a
            required feature column cannot be derived from the input.
    """
    result = df.copy()

    target = recipe.get("target_column")
    if target is not None and target in result.columns:
        result = result.drop(columns=[target])

    numeric_cols = list(recipe.get("numeric_columns", []))
    categorical_cols = list(recipe.get("categorical_columns", []))
    required = set(numeric_cols) | set(categorical_cols)
    missing = sorted(required - set(result.columns))
    if missing:
        msg = (
            f"Prediction data is missing required columns: {missing}. "
            f"Provide raw rows containing the training columns "
            f"(numeric={numeric_cols}, categorical={categorical_cols})."
        )
        raise DataTransformError(msg)

    fill_value = recipe.get("fill_value", 0)
    for col in numeric_cols + categorical_cols:
        result[col] = result[col].fillna(fill_value)

    for col, mapping in recipe.get("encoding_maps", {}).items():
        if col in result.columns:
            result[col] = result[col].map(mapping).fillna(0).astype(int)

    for col, params in recipe.get("scaling_params", {}).items():
        if col not in result.columns:
            continue
        col_min = float(params["min"])
        col_max = float(params["max"])
        span = col_max - col_min
        result[col] = result[col].astype(float)
        if span == 0:
            result[col] = 0.0
        else:
            result[col] = (result[col] - col_min) / span

    feature_columns = list(recipe.get("feature_columns", []))
    underivable = [c for c in feature_columns if c not in result.columns]
    if underivable:
        msg = (
            f"Feature column(s) {underivable} cannot be derived from the input "
            "by the saved recipe (e.g. derived columns such as 'outlier_flag'). "
            "Pass already-engineered features via 'already_engineered=True'."
        )
        raise DataTransformError(msg)

    return result[feature_columns]
