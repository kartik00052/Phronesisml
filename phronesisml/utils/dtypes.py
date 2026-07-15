"""Shared dtype constants used across the PhronesisML framework.

This module is the single source of truth for the ``NUMERIC_DTYPES``
constant, which is used by engines, profilers, feature engineering,
target detection, and model selection to identify numeric columns.
"""

from __future__ import annotations

__all__ = ["NUMERIC_DTYPES"]

NUMERIC_DTYPES: frozenset[str] = frozenset(
    {
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint24",
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
