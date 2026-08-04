"""Engine-light resource estimation utilities.

Small, deterministic helpers that complement the heavier pre-flight
``ResourceEstimator`` (which needs an engine and a DataFrame):

- ``format_bytes`` / ``format_seconds``: human-readable formatting
- ``estimate_dataframe_memory``: pandas deep-memory estimate
- ``estimate_training_time``: rows × features × complexity heuristic
- ``estimate_model_size_mb``: feature-count based model footprint
- ``check_memory_sufficiency``: memory threshold check with severity

All values are best-effort estimates for planning/decisions, not
benchmarks.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def format_bytes(num_bytes: int) -> str:
    """Format a byte count into a human-readable string.

    Args:
        num_bytes: Byte count (>= 0).

    Returns:
        e.g. ``"512.0 KB"``, ``"1.5 GB"``.
    """
    num = float(max(0, int(num_bytes)))
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    for unit in units:
        if num < 1024.0 or unit == units[-1]:
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024.0
    return f"{num:.1f} PB"


def format_seconds(seconds: float) -> str:
    """Format a duration in seconds into a human-readable string.

    Args:
        seconds: Duration in seconds (>= 0).

    Returns:
        e.g. ``"0:00:03"`` (H:MM:SS).
    """
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def estimate_dataframe_memory(df: pd.DataFrame) -> dict[str, Any]:
    """Estimate the in-memory size of a DataFrame.

    Args:
        df: Input DataFrame.

    Returns:
        A dict with ``memory_bytes``, ``memory_mb``,
        ``estimated_rows``, and ``estimated_columns``.
    """
    memory_bytes = int(df.memory_usage(deep=True).sum())
    return {
        "memory_bytes": memory_bytes,
        "memory_mb": round(memory_bytes / (1024 * 1024), 3),
        "estimated_rows": int(df.shape[0]),
        "estimated_columns": int(df.shape[1]),
    }


def estimate_training_time(
    n_rows: int,
    n_features: int,
    complexity: str = "medium",
) -> dict[str, Any]:
    """Estimate training wall-clock time for a single model.

    Heuristic: ``rows * features * complexity_factor / ROWS_PER_SECOND``
    with ``ROWS_PER_SECOND = 50_000``.  The result is a rough planning
    value, not a benchmark.

    Args:
        n_rows: Number of training rows.
        n_features: Number of features.
        complexity: ``"low"`` (linear models), ``"medium"`` (ensemble),
            or ``"high"`` (deep/expensive models).

    Returns:
        A dict with ``estimated_seconds``, ``estimated_runtime``
        (formatted), and ``complexity``.
    """
    factors = {"low": 1.0, "medium": 3.0, "high": 8.0}
    factor = factors.get(complexity, 3.0)
    rows_per_second = 50_000.0
    estimated_seconds = max(0.0, (n_rows * max(n_features, 1) * factor) / rows_per_second)
    return {
        "estimated_seconds": round(estimated_seconds, 2),
        "estimated_runtime": format_seconds(estimated_seconds),
        "complexity": complexity,
    }


def estimate_model_size_mb(
    n_features: int,
    n_classes: int = 0,
    n_estimators: int = 100,
    bytes_per_feature: float = 8.0,
) -> dict[str, Any]:
    """Estimate an in-memory model footprint in MB.

    Heuristic: each estimator holds a dense coefficient/feature matrix of
    ``n_features * (n_classes or 1)`` float values; ensemble models
    multiply by ``n_estimators``.

    Args:
        n_features: Number of features the model sees.
        n_classes: Number of classes (0 for regression / single output).
        n_estimators: Number of ensemble members.
        bytes_per_feature: Bytes per stored float.

    Returns:
        A dict with ``estimated_bytes`` and ``estimated_mb``.
    """
    outputs = max(n_classes, 1)
    per_tree = n_features * outputs * bytes_per_feature
    total_bytes = per_tree * n_estimators
    return {
        "estimated_bytes": int(total_bytes),
        "estimated_mb": round(total_bytes / (1024 * 1024), 4),
    }


def check_memory_sufficiency(
    required_mb: float,
    available_gb: float | None = None,
    warn_threshold_ratio: float = 0.5,
    block_threshold_ratio: float = 0.9,
) -> dict[str, Any]:
    """Check whether required memory is within available memory.

    Args:
        required_mb: Estimated memory requirement in MB.
        available_gb: Available system memory in GB.  If ``None``, a
            conservative default of 8 GB is assumed.
        warn_threshold_ratio: Warn when usage exceeds this fraction of
            available memory.
        block_threshold_ratio: Block when usage exceeds this fraction of
            available memory.

    Returns:
        A dict with ``sufficient`` (bool), ``severity``
        (``"ok"`` / ``"warning"`` / ``"blocked"``), and ``ratio``.
    """
    available_mb = (available_gb or 8.0) * 1024.0
    ratio = required_mb / available_mb if available_mb > 0 else 1.0

    if ratio >= block_threshold_ratio:
        severity = "blocked"
        sufficient = False
    elif ratio >= warn_threshold_ratio:
        severity = "warning"
        sufficient = True
    else:
        severity = "ok"
        sufficient = True

    return {
        "sufficient": sufficient,
        "severity": severity,
        "ratio": round(ratio, 4),
        "required_mb": round(required_mb, 2),
        "available_mb": round(available_mb, 2),
    }
