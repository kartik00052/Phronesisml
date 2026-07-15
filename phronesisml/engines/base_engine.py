"""Abstract base class for Phronesis data engines.

The engine layer provides a uniform interface over different data
processing backends (Pandas, Polars, PySpark).  All data operations
in the SDK flow through an engine instance, so switching backends is
transparent to the rest of the framework.

Design rationale:
- ABC over Protocol: engines have shared default behaviour (e.g.
  ``__repr__``) and we want强制 subclassing so that every new engine
  is audited against the full interface.
- Polars lazy semantics as the internal standard: ``collect()`` and
  ``lazy()`` are first-class.  Engines that do not natively support
  lazy evaluation (Pandas) convert at the boundary.
- The ``EngineType`` enum provides type-safe engine identification
  without stringly-typed comparisons.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

__all__ = ["BaseEngine", "EngineType", "NUMERIC_DTYPES"]
from enum import StrEnum
from pathlib import Path
from typing import Any

import pandas as pd

from phronesisml.utils.dtypes import NUMERIC_DTYPES  # noqa: F401 — backward-compat re-export


class EngineType(StrEnum):
    """Identifies a computation backend."""

    PANDAS = "pandas"
    POLARS = "polars"
    SPARK = "spark"


class BaseEngine(ABC):
    """Abstract interface that every data engine must implement.

    The method signatures use ``Any`` for DataFrame types because the
    concrete type varies by backend (``pd.DataFrame``, ``pl.DataFrame``,
    ``pyspark.sql.DataFrame``).  Type narrowing happens in subclasses.
    """

    engine_type: EngineType

    def __init__(self) -> None:
        self._collect_cache: dict[int, pd.DataFrame] = {}

    @abstractmethod
    def read(self, path: str | Path, **kwargs: Any) -> Any:
        """Read data from *path* into the engine's native DataFrame.

        Supported formats are determined by the concrete engine.
        ``kwargs`` are forwarded to the underlying reader (e.g.
        ``sep`` for CSV, ``schema`` for Parquet).
        """
        ...

    @abstractmethod
    def write(self, df: Any, path: str | Path, **kwargs: Any) -> None:
        """Write *df* to *path*.

        The file format is inferred from the path extension.
        """
        ...

    @abstractmethod
    def filter(self, df: Any, conditions: Any) -> Any:
        """Return rows satisfying *conditions*.

        ``conditions`` is engine-specific: a boolean Series for Pandas,
        a boolean expression for Polars, etc.
        """
        ...

    @abstractmethod
    def transform(self, df: Any, func: Any, **kwargs: Any) -> Any:
        """Apply *func* to *df*.

        ``func`` is engine-specific:
        - Pandas/Polars: a callable ``(DataFrame) -> DataFrame``.
        - Spark: a UDF or SQL expression string.

        Additional keyword arguments are forwarded to the engine's
        transform implementation.
        """
        ...

    @abstractmethod
    def aggregate(
        self,
        df: Any,
        group_by: list[str] | str,
        aggs: dict[str, Any],
    ) -> Any:
        """Group by *group_by* and apply *aggs* aggregation.

        ``aggs`` maps column names to aggregation function names
        (e.g. ``{"revenue": "sum", "price": "mean"}``).
        """
        ...

    @abstractmethod
    def join(
        self,
        left: Any,
        right: Any,
        on: str | list[str],
        how: str = "inner",
    ) -> Any:
        """Join two DataFrames on the shared column(s) *on*.

        ``how`` is one of ``"inner"``, ``"left"``, ``"right"``, ``"outer"``.
        """
        ...

    @abstractmethod
    def collect(self, df: Any) -> pd.DataFrame:
        """Materialise a lazy plan into a concrete Pandas DataFrame.

        Engines that do not support lazy evaluation (Pandas) simply
        return *df* unchanged.  This is the universal output format —
        all downstream code receives Pandas DataFrames.
        """
        ...

    def cached_collect(self, df: Any) -> pd.DataFrame:
        """Cache-aware version of ``collect()``.

        Uses the object id of *df* as cache key.  If the same DataFrame
        has been collected before, returns the cached result directly.
        """
        key = id(df)
        cached = self._collect_cache.get(key)
        if cached is not None:
            return cached
        result = self.collect(df)
        self._collect_cache[key] = result
        return result

    def clear_collect_cache(self) -> None:
        """Clear the collect cache to free memory."""
        self._collect_cache.clear()

    @abstractmethod
    def lazy(self, df: Any) -> Any:
        """Convert *df* into the engine's lazy representation.

        For Polars this is ``pl.LazyFrame``; for Pandas it is a no-op
        wrapper; for Spark the DataFrame is already lazy.
        """
        ...

    @abstractmethod
    def shape(self, df: Any) -> tuple[int, int]:
        """Return ``(n_rows, n_columns)`` for the given DataFrame."""
        ...

    @abstractmethod
    def columns(self, df: Any) -> list[str]:
        """Return the column names of *df*."""
        ...

    @abstractmethod
    def dtypes(self, df: Any) -> dict[str, str]:
        """Return a mapping of column name → dtype string."""
        ...

    @abstractmethod
    def head(self, df: Any, n: int = 5) -> pd.DataFrame:
        """Return the first *n* rows as a Pandas DataFrame."""
        ...

    @abstractmethod
    def memory_usage(self, df: Any) -> int:
        """Estimate the memory footprint of *df* in bytes.

        This is used by the engine selector to choose an appropriate
        backend based on data size.
        """
        ...

    @abstractmethod
    def sample(
        self,
        df: Any,
        n: int | None = None,
        fraction: float | None = None,
        random_state: int | None = None,
        strategy: str = "random",
        target_column: str | None = None,
    ) -> Any:
        """Return a sampled subset of *df*.

        The original DataFrame is never modified.  The returned DataFrame
        is in the engine's native format.

        Args:
            n: Number of rows to sample.  Mutually exclusive with *fraction*.
            fraction: Fraction of rows to sample (0.0–1.0).  Mutually
                exclusive with *n*.
            random_state: Random seed for reproducibility.
            strategy: Sampling strategy ('random', 'stratified', 'head',
                'time_aware').
            target_column: Target column for stratified sampling.

        Returns:
            A new DataFrame with sampled rows.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(engine_type={self.engine_type.value!r})"
