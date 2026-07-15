"""Target detection — heuristic identification of the target column and task type.

All functions receive an engine-native DataFrame, a ``BaseEngine``
instance, and the EDA ``data_profile`` dict.  They use
``engine.collect()`` to materialise the data and ``engine.dtypes()``
for type-aware heuristics.  No direct pandas or polars imports are
used here — all data access flows through the engine.

Heuristic pipeline (applied in order):
1. **Name signals**: columns named ``target``, ``label``, ``y``,
   ``outcome``, ``class``, ``answer`` are strong hints.  These are
   checked first but are *not* a hard requirement — a column named
   ``age`` can still be detected as a target if no name match is found.
2. **Cardinality/dtype signals**:
   - Categorical (string) column with 2–50 unique values → likely
     classification target.
   - Numeric column with 2–5 unique values → ambiguous between
     classification and regression.  **Must not be silently guessed.**
   - Numeric column with >50 unique values → likely regression target.
3. **Ambiguity handling**: when a column falls into the ambiguous zone
   (2–5 unique values and numeric), a confidence score below
   ``AMBIGUITY_THRESHOLD`` (0.6) is returned along with a human-readable
   ``ambiguity_reason``.  The caller (TargetDetectionAgent) surfaces
   this to the user rather than picking one silently.

Confidence threshold:
    ``AMBIGUITY_THRESHOLD = 0.6`` — below this, the detection result
    is flagged as ambiguous.  This value is documented here and in the
    agent docstring; both must agree (this is the exact category of
    drift found in Pass 1/2 audits — do not reintroduce it).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from phronesisml.engines.base_engine import BaseEngine
from phronesisml.utils.dtypes import NUMERIC_DTYPES

logger = logging.getLogger(__name__)

# Columns whose names are strong target hints (case-insensitive match).
_TARGET_NAME_HINTS = frozenset(
    {
        "target",
        "label",
        "y",
        "outcome",
        "class",
        "answer",
        "target_variable",
        "response",
        "dependent",
    }
)

# Confidence below this threshold → ambiguous detection.
AMBIGUITY_THRESHOLD = 0.6

# ── ID / UUID / High-Cardinality Column Detection ─────────────────
# Patterns that indicate a column is likely an identifier, not a target.
_ID_COLUMN_PATTERNS = re.compile(
    r"(^|_)id$"
    r"|(^|_)number$"
    r"|(^|_)uuid$"
    r"|(^|_)key$"
    r"|(^|_)code$"
    r"|(^|_)identifier$"
    r"|(^|_)index$"
    r"|(^|_)pk$"
    r"|(^|_)fk$"
    r"|(^|_)sid$"
    r"|(^|_)nid$"
    r"|(^|_)uid$"
    r"|(^|_)eid$"
    r"|(^|_)tid$"
    r"|(^|_)row_num$"
    r"|(^|_)row_number$"
    r"|(^|_)seq$"
    r"|(^|_)sequence$",
    re.IGNORECASE,
)

# Uniqueness ratio threshold: if n_unique / n_rows > this, column is
# likely an ID (not a meaningful target).
_ID_UNIQUENESS_THRESHOLD = 0.9

# Monotonicity threshold: if monotonic ratio > this, column is likely
# an auto-increment ID.
_ID_MONOTONIC_THRESHOLD = 0.95


def detect_target(
    df: Any,
    engine: BaseEngine,
    data_profile: dict[str, Any],
) -> dict[str, Any]:
    """Detect the likely target column and infer the task type.

    Args:
        df: Engine-native DataFrame (the processed/validated data).
        engine: The active computation engine.
        data_profile: The EDA profile dict produced by
            ``data.profilers.stats.profile_dataset``.

    Returns:
        A dict with keys: ``target_column``, ``task_type``,
        ``confidence``, ``ambiguity_reason`` (``None`` if unambiguous),
        ``candidates`` (list of scored candidates for transparency).

    """
    collected = engine.cached_collect(df)
    dtypes = engine.dtypes(df)
    profile_numeric = data_profile.get("numeric_summary", {})
    profile_categorical = data_profile.get("categorical_summary", {})

    # Merge categorical and numeric summaries for unified access
    all_summaries: dict[str, Any] = {}
    all_summaries.update(profile_numeric)
    all_summaries.update(profile_categorical)

    # ── Build candidate list ─────────────────────────────────────────
    candidates: list[dict[str, Any]] = []
    nunique_series = collected.nunique()
    n_rows = len(collected)
    for col in engine.columns(df):
        if col not in all_summaries:
            continue
        dtype_str = dtypes.get(col, "")
        n_unique = int(nunique_series.get(col, 0))
        is_numeric = dtype_str in NUMERIC_DTYPES
        col_summary = all_summaries.get(col, {})

        candidate = _score_column(col, is_numeric, n_unique, n_rows, collected, col_summary)
        candidates.append(candidate)

    # ── Select best candidate ────────────────────────────────────────
    if not candidates:
        return _no_target_found()

    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    best = candidates[0]

    if best["confidence"] < AMBIGUITY_THRESHOLD:
        # Even if the best candidate's own signal wasn't explicitly
        # ambiguous, the overall detection is ambiguous because no
        # candidate scored above the threshold.
        ambiguity_reason = best["ambiguity_reason"]
        if ambiguity_reason is None:
            ambiguity_reason = (
                f"No candidate exceeded the confidence threshold "
                f"({AMBIGUITY_THRESHOLD}). Best candidate '{best['column']}' "
                f"scored {best['confidence']:.2f} with signals: "
                f"{', '.join(best['signals'])}."
            )
        logger.warning(
            "Target detection ambiguous: best candidate '%s' has confidence %.2f < %.2f.",
            best["column"],
            best["confidence"],
            AMBIGUITY_THRESHOLD,
        )
        return {
            "target_column": best["column"],
            "task_type": "ambiguous",
            "confidence": best["confidence"],
            "ambiguity_reason": ambiguity_reason,
            "candidates": candidates,
        }

    logger.info(
        "Target detected: '%s' (%s, confidence=%.2f).",
        best["column"],
        best["task_type"],
        best["confidence"],
    )
    return {
        "target_column": best["column"],
        "task_type": best["task_type"],
        "confidence": best["confidence"],
        "ambiguity_reason": None,
        "candidates": candidates,
    }


def _is_id_column(
    col: str,
    n_unique: int,
    n_rows: int,
    is_numeric: bool,
    collected: Any,
) -> bool:
    """Heuristic check: is this column an ID/UUID/sequence (not a target)?

    Checks three signals:
    1. **Name pattern**: ``*_id``, ``*_number``, ``*_uuid``, etc.
    2. **High uniqueness ratio**: ``n_unique / n_rows > 0.9``
    3. **Monotonic sequence**: values increase monotonically (auto-increment)

    Returns True if the column is likely an identifier and should NOT
    be considered a target candidate.
    """
    # Skip if row count is 0 (avoid division by zero)
    if n_rows == 0:
        return False

    # 1. Name pattern match
    if _ID_COLUMN_PATTERNS.search(col):
        logger.debug("Column '%s' matched ID name pattern.", col)
        return True

    # 2. High uniqueness ratio (near-duplicate of row index)
    uniqueness_ratio = n_unique / n_rows
    if uniqueness_ratio > _ID_UNIQUENESS_THRESHOLD:
        logger.debug(
            "Column '%s' has high uniqueness ratio %.3f (n_unique=%d, n_rows=%d).",
            col,
            uniqueness_ratio,
            n_unique,
            n_rows,
        )
        return True

    # 3. Monotonic sequence check (only for numeric columns with
    #    many unique values — otherwise this is expensive and
    #    unlikely to match).
    if is_numeric and n_unique > 100:
        try:
            values = collected[col].to_list()
            # Check if strictly non-decreasing (monotonic)
            is_monotonic = all(values[i] <= values[i + 1] for i in range(len(values) - 1))
            if is_monotonic:
                monotonic_ratio = n_unique / n_rows
                if monotonic_ratio > _ID_MONOTONIC_THRESHOLD:
                    logger.debug(
                        "Column '%s' is monotonic (ratio=%.3f) — likely an ID.",
                        col,
                        monotonic_ratio,
                    )
                    return True
        except Exception:
            # If we can't check monotonicity, skip this heuristic
            pass

    return False


def _score_column(
    col: str,
    is_numeric: bool,
    n_unique: int,
    n_rows: int,
    collected: Any,
    col_summary: dict[str, Any],
) -> dict[str, Any]:
    """Score a single column as a target candidate.

    Returns a dict with ``column``, ``task_type``, ``confidence``,
    ``ambiguity_reason``, and ``signals`` (list of which heuristics
    fired, for transparency).
    """
    signals: list[str] = []
    confidence = 0.0
    task_type = "unknown"
    ambiguity_reason: str | None = None

    # ── ID / UUID / High-Cardinality Pre-filter ──────────────────────
    if _is_id_column(col, n_unique, n_rows, is_numeric, collected):
        confidence = 0.0
        task_type = "excluded"
        ambiguity_reason = (
            f"Column '{col}' is excluded as a potential target: "
            f"likely an ID, UUID, or unique sequence "
            f"(uniqueness ratio={n_unique / n_rows:.3f})."
        )
        signals.append("id_column_excluded")
        return {
            "column": col,
            "task_type": task_type,
            "confidence": confidence,
            "ambiguity_reason": ambiguity_reason,
            "signals": signals,
            "n_unique": n_unique,
            "is_numeric": is_numeric,
        }

    # ── Name signal ──────────────────────────────────────────────────
    if col.lower().strip() in _TARGET_NAME_HINTS:
        confidence += 0.4
        signals.append("name_hint")

    # ── Cardinality / dtype signal ───────────────────────────────────
    if n_unique == 0:
        # Empty column — skip
        confidence = 0.0
        signals.append("empty_column")
    elif n_unique == 1:
        # Constant column — not a useful target
        confidence = 0.0
        signals.append("constant_column")
    elif is_numeric and n_unique in range(3, 6):
        # Numeric with 2–5 unique values: ambiguous
        confidence += 0.3
        task_type = "ambiguous"
        ambiguity_reason = (
            f"Column '{col}' is numeric with {n_unique} unique values "
            f"(range 2–5). This could be binary/multiclass classification "
            f"or regression. Manual review recommended."
        )
        signals.append("numeric_low_cardinality_ambiguous")
    elif is_numeric and n_unique > 50:
        # High-cardinality numeric: likely regression
        confidence += 0.5
        task_type = "regression"
        signals.append("numeric_high_cardinality")
    elif is_numeric and n_unique > 5:
        # Medium-cardinality numeric: could be regression or ordinal
        confidence += 0.4
        task_type = "regression"
        signals.append("numeric_medium_cardinality")
    elif not is_numeric and 2 <= n_unique <= 50:
        # Categorical with 2–50 values: likely classification
        confidence += 0.5
        task_type = "classification"
        signals.append("categorical_low_cardinality")
    elif not is_numeric and n_unique > 50:
        # High-cardinality categorical: might be an ID, not a target
        confidence -= 0.2
        task_type = "classification"
        signals.append("categorical_high_cardinality_penalty")
    elif is_numeric and n_unique == 2:
        # Exactly 2 unique numeric values: likely binary classification
        # but the numeric type makes it ambiguous
        confidence += 0.3
        task_type = "ambiguous"
        ambiguity_reason = (
            f"Column '{col}' is numeric with exactly 2 unique values. "
            f"This could be binary classification (0/1 encoded) or "
            f"regression with only two observed outcomes."
        )
        signals.append("numeric_binary_ambiguous")

    # Clamp confidence to [0, 1]
    confidence = max(0.0, min(1.0, confidence))

    return {
        "column": col,
        "task_type": task_type,
        "confidence": confidence,
        "ambiguity_reason": ambiguity_reason,
        "signals": signals,
        "n_unique": n_unique,
        "is_numeric": is_numeric,
    }


def _no_target_found() -> dict[str, Any]:
    """Return a result when no viable target is found."""
    return {
        "target_column": None,
        "task_type": None,
        "confidence": 0.0,
        "ambiguity_reason": "No viable target column detected.",
        "candidates": [],
    }


# ── Pre-flight Validation ──────────────────────────────────────────
# These checks run AFTER target detection but BEFORE feature engineering
# and model training to catch OOM / memory explosion early.

# Maximum safe dataset size (rows × columns) for one-hot encoding.
# Beyond this, feature engineering can explode memory.
_MAX_FEATURE_PRODUCT = 500_000  # e.g. 10K rows × 50 cols

# Maximum number of categorical values before one-hot encoding
# becomes dangerous (creates too many sparse columns).
_MAX_CATEGORICAL_CARDINALITY = 100


def validate_target_safety(
    df: Any,
    engine: BaseEngine,
    target_column: str,
    task_type: str,
    data_profile: dict[str, Any],
) -> dict[str, Any]:
    """Pre-flight validation: check if the detected target will cause
    downstream failures (OOM, encoding explosion, etc.).

    Runs after target detection, before feature engineering.

    Args:
        df: Engine-native DataFrame.
        engine: Active computation engine.
        target_column: Detected target column name.
        task_type: Detected task type.
        data_profile: EDA profile dict.

    Returns:
        A dict with:
        - ``safe``: bool — True if safe to proceed.
        - ``warnings``: list of warning strings (non-fatal).
        - ``blockers``: list of blocker strings (fatal — must not proceed).
        - ``estimated_memory_mb``: estimated memory for feature engineering.

    """
    warnings: list[str] = []
    blockers: list[str] = []
    estimated_memory_mb = 0.0

    collected = engine.cached_collect(df)
    n_rows = len(collected)
    n_cols = len(engine.columns(df))
    profile_categorical = data_profile.get("categorical_summary", {})
    profile_numeric = data_profile.get("numeric_summary", {})

    # ── Check 1: Dataset size × column count ─────────────────────────
    feature_product = n_rows * n_cols
    if feature_product > _MAX_FEATURE_PRODUCT * 10:
        blockers.append(
            f"Dataset too large for safe processing: {n_rows:,} rows × {n_cols} "
            f"cols = {feature_product:,} (limit: {_MAX_FEATURE_PRODUCT * 10:,}). "
            f"Reduce dataset size or increase memory allocation."
        )
    elif feature_product > _MAX_FEATURE_PRODUCT:
        warnings.append(
            f"Dataset is large: {n_rows:,} rows × {n_cols} cols = {feature_product:,}. "
            f"Feature engineering may use significant memory."
        )

    # ── Check 2: High-cardinality categoricals ───────────────────────
    high_card_cats = []
    for col, summary in profile_categorical.items():
        if col == target_column:
            continue
        n_unique = summary.get("n_unique", 0)
        if n_unique > _MAX_CATEGORICAL_CARDINALITY:
            high_card_cats.append((col, n_unique))

    if high_card_cats:
        names = [f"{c} ({u} values)" for c, u in high_card_cats[:5]]
        warnings.append(
            f"High-cardinality categorical columns detected: {', '.join(names)}. "
            f"These will be dropped during encoding to prevent memory explosion."
        )

    # ── Check 3: Target cardinality vs row count ─────────────────────
    if target_column in profile_categorical:
        target_nunique = profile_categorical[target_column].get("n_unique", 0)
        if target_nunique > n_rows * 0.95:
            blockers.append(
                f"Target column '{target_column}' has {target_nunique} unique values "
                f"out of {n_rows} rows ({target_nunique / n_rows:.1%}). "
                f"This looks like an ID column, not a meaningful target."
            )
        elif target_nunique > n_rows * 0.5:
            warnings.append(
                f"Target column '{target_column}' has high cardinality "
                f"({target_nunique}/{n_rows} = {target_nunique / n_rows:.1%}). "
                f"Consider if this is the correct target."
            )
    elif target_column in profile_numeric:
        target_nunique = profile_numeric[target_column].get("n_unique", 0)
        if target_nunique > n_rows * 0.95:
            blockers.append(
                f"Target column '{target_column}' has {target_nunique} unique values "
                f"out of {n_rows} rows ({target_nunique / n_rows:.1%}). "
                f"This looks like an ID column, not a meaningful target."
            )

    # ── Check 4: Class imbalance (classification only) ───────────────
    if task_type == "classification" and target_column in profile_categorical:
        value_counts = collected[target_column].value_counts()
        if hasattr(value_counts, "to_dict"):
            counts = value_counts.to_dict()
        else:
            counts = dict(zip(value_counts.index, value_counts, strict=False))
        total = sum(counts.values())
        if total > 0:
            minority_ratio = min(counts.values()) / total
            if minority_ratio < 0.01:
                warnings.append(
                    f"Severe class imbalance in target '{target_column}': "
                    f"minority class is {minority_ratio:.2%} of samples. "
                    f"Model may struggle to learn minority class patterns."
                )

    # ── Check 5: Estimated memory for one-hot encoding ───────────────
    # Estimate: each categorical column with K values creates K new columns
    estimated_new_cols = 0
    for col, summary in profile_categorical.items():
        if col == target_column:
            continue
        n_unique = summary.get("n_unique", 0)
        # Cap at 100 to avoid over-counting (high-card cats are dropped)
        estimated_new_cols += min(n_unique, 100)

    estimated_memory_mb = (n_rows * (n_cols + estimated_new_cols) * 8) / (
        1024 * 1024
    )  # 8 bytes per float64

    if estimated_memory_mb > 4096:  # > 4 GB
        blockers.append(
            f"Estimated memory for feature engineering: {estimated_memory_mb:.0f} MB. "
            f"This exceeds the 4 GB safety limit. Reduce dataset size or "
            f"enable memory-efficient mode."
        )
    elif estimated_memory_mb > 1024:  # > 1 GB
        warnings.append(
            f"Estimated memory for feature engineering: {estimated_memory_mb:.0f} MB. "
            f"Monitor memory usage during feature engineering."
        )

    safe = len(blockers) == 0

    if not safe:
        logger.warning(
            "Pre-flight validation FAILED: %d blocker(s), %d warning(s).",
            len(blockers),
            len(warnings),
        )
    elif warnings:
        logger.info(
            "Pre-flight validation PASSED with %d warning(s).",
            len(warnings),
        )
    else:
        logger.info("Pre-flight validation PASSED — no issues detected.")

    return {
        "safe": safe,
        "warnings": warnings,
        "blockers": blockers,
        "estimated_memory_mb": estimated_memory_mb,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "estimated_new_cols": estimated_new_cols,
    }
