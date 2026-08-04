"""Engine recommendation — pure, offline engine suitability heuristics.

Complements ``engines.engine_selector.select_engine`` (which *builds*
the chosen engine) with deterministic recommendation reports that work
from raw dataset characteristics without instantiating engines:

- ``recommend_engine``: choose pandas / polars / spark by size
- ``engine_capabilities``: per-engine feature support matrix
- ``engine_comparison_report``: full comparison for a dataset
"""

from __future__ import annotations

from typing import Any

from phronesisml.configs.settings import DEFAULT_MAX_MEMORY_BYTES, PANDAS_MAX_BYTES

# Per-engine capability matrix.
_CAPABILITIES: dict[str, dict[str, bool]] = {
    "pandas": {
        "in_memory": True,
        "distributed": False,
        "lazy_evaluation": False,
        "missing_value_ops": True,
        "datetime_ops": True,
        "streaming": False,
        "gpu": False,
    },
    "polars": {
        "in_memory": True,
        "distributed": False,
        "lazy_evaluation": True,
        "missing_value_ops": True,
        "datetime_ops": True,
        "streaming": True,
        "gpu": False,
    },
    "spark": {
        "in_memory": False,
        "distributed": True,
        "lazy_evaluation": True,
        "missing_value_ops": True,
        "datetime_ops": True,
        "streaming": True,
        "gpu": False,
    },
}

_CAPABILITY_LABELS: dict[str, str] = {
    "in_memory": "In-memory processing",
    "distributed": "Distributed / cluster",
    "lazy_evaluation": "Lazy evaluation",
    "missing_value_ops": "Missing-value handling",
    "datetime_ops": "Datetime operations",
    "streaming": "Streaming / chunked reads",
    "gpu": "GPU acceleration",
}


def recommend_engine(
    n_rows: int = 0,
    n_cols: int = 0,
    memory_bytes: int = 0,
) -> dict[str, Any]:
    """Recommend an engine from dataset characteristics alone.

    Args:
        n_rows: Estimated number of rows (informational only).
        n_cols: Estimated number of columns (informational only).
        memory_bytes: Estimated in-memory footprint in bytes.

    Returns:
        A dict with ``engine`` (``"pandas"`` / ``"polars"`` /
        ``"spark"``), ``reason``, and ``routing`` detail.
    """
    if memory_bytes < PANDAS_MAX_BYTES:
        engine = "pandas"
        reason = (
            f"Dataset is small (≈{memory_bytes} bytes); Pandas gives the "
            "fastest startup and simplest API."
        )
    elif memory_bytes <= DEFAULT_MAX_MEMORY_BYTES:
        engine = "polars"
        reason = (
            f"Dataset is medium (≈{memory_bytes} bytes); Polars balances "
            "single-machine performance with lazy evaluation."
        )
    else:
        engine = "spark"
        reason = f"Dataset is large (≈{memory_bytes} bytes); Spark enables distributed processing."

    return {
        "engine": engine,
        "reason": reason,
        "routing": {
            "n_rows": n_rows,
            "n_cols": n_cols,
            "memory_bytes": memory_bytes,
            "pandas_max_bytes": PANDAS_MAX_BYTES,
        },
    }


def engine_capabilities() -> dict[str, Any]:
    """Return the per-engine capability matrix.

    Returns:
        A dict with ``engines`` (list), ``capabilities`` (list of dicts:
        key, label, per-engine boolean), and ``matrix`` (engine →
        capability → bool).
    """
    engines = sorted(_CAPABILITIES)
    capabilities = [
        {
            "key": key,
            "label": _CAPABILITY_LABELS[key],
            "engines": {e: bool(_CAPABILITIES[e].get(key, False)) for e in engines},
        }
        for key in _CAPABILITY_LABELS
    ]
    return {
        "engines": engines,
        "capabilities": capabilities,
        "matrix": _CAPABILITIES,
    }


def engine_comparison_report(
    n_rows: int = 0,
    n_cols: int = 0,
    memory_bytes: int = 0,
) -> dict[str, Any]:
    """Produce a combined engine recommendation report.

    Args:
        n_rows: Estimated number of rows.
        n_cols: Estimated number of columns.
        memory_bytes: Estimated in-memory footprint in bytes.

    Returns:
        A dict with the recommendation, the capability matrix, and the
        input characteristics.
    """
    rec = recommend_engine(n_rows=n_rows, n_cols=n_cols, memory_bytes=memory_bytes)
    caps = engine_capabilities()
    chosen_caps = caps["matrix"].get(rec["engine"], {})
    return {
        "recommendation": rec,
        "input": {
            "n_rows": n_rows,
            "n_cols": n_cols,
            "memory_bytes": memory_bytes,
        },
        "chosen_engine_capabilities": chosen_caps,
        "capabilities": caps["capabilities"],
    }
