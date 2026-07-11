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
from typing import Any

from aetherml.engines.base_engine import BaseEngine

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

# Unique-value counts in this range trigger the ambiguity check for
# numeric columns.  Values outside this range are classified with
# higher confidence.
_AMBIGUOUS_CARDINALITY_RANGE = range(2, 6)  # 2, 3, 4, 5


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
    collected = engine.collect(df)
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
    for col in engine.columns(df):
        if col not in all_summaries:
            continue
        dtype_str = dtypes.get(col, "")
        n_unique = int(nunique_series.get(col, 0))
        is_numeric = dtype_str in _NUMERIC_DTYPES
        col_summary = all_summaries.get(col, {})

        candidate = _score_column(col, is_numeric, n_unique, col_summary)
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


def _score_column(
    col: str,
    is_numeric: bool,
    n_unique: int,
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
    elif is_numeric and n_unique in _AMBIGUOUS_CARDINALITY_RANGE:
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


# Re-export the numeric dtype set fromprofilers for consistency
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
