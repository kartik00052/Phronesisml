"""Pandas-based data engine.

Implements ``BaseEngine`` using pandas as the computation backend.
Best suited for small-to-medium datasets that fit comfortably in
single-machine memory.

All operations are eager (no lazy evaluation).  ``lazy()`` returns
the DataFrame unchanged wrapped in a thin ``_LazyPandas`` proxy so
that ``collect()`` can be called uniformly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from aetherml.engines.base_engine import BaseEngine, EngineType
from aetherml.exceptions import EngineError


class _LazyPandas:
    """Thin wrapper so that ``engine.lazy(df) → engine.collect(result)`` works."""

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df


class PandasEngine(BaseEngine):
    """Data engine backed by pandas."""

    engine_type = EngineType.PANDAS

    # ── I/O ─────────────────────────────────────────────────────────

    def read(self, path: str | Path, **kwargs: Any) -> pd.DataFrame:
        path = Path(path)
        suffix = path.suffix.lower()
        read_ops: dict[str, Any] = {
            ".csv": pd.read_csv,
            ".parquet": pd.read_parquet,
            ".json": pd.read_json,
            ".jsonl": lambda p, **kw: pd.read_json(p, lines=True, **kw),
            ".feather": pd.read_feather,
            ".xlsx": pd.read_excel,
        }
        reader = read_ops.get(suffix)
        if reader is None:
            msg = f"Unsupported file format: {suffix}"
            raise EngineError(msg)
        return reader(path, **kwargs)

    def write(self, df: pd.DataFrame, path: str | Path, **kwargs: Any) -> None:
        path = Path(path)
        suffix = path.suffix.lower()
        write_ops: dict[str, Any] = {
            ".csv": lambda d, p, **kw: d.to_csv(p, index=kw.pop("index", False), **kw),
            ".parquet": lambda d, p, **kw: d.to_parquet(p, **kw),
            ".json": lambda d, p, **kw: d.to_json(p, **kw),
            ".feather": lambda d, p, **kw: d.to_feather(p, **kw),
        }
        writer = write_ops.get(suffix)
        if writer is None:
            msg = f"Unsupported file format for writing: {suffix}"
            raise EngineError(msg)
        writer(df, path, **kwargs)

    # ── Transformations ─────────────────────────────────────────────

    def filter(self, df: pd.DataFrame, conditions: Any) -> pd.DataFrame:
        return df.loc[conditions].copy()

    def transform(self, df: pd.DataFrame, func: Any, **kwargs: Any) -> pd.DataFrame:
        return func(df, **kwargs)

    def aggregate(
        self,
        df: pd.DataFrame,
        group_by: list[str] | str,
        aggs: dict[str, Any],
    ) -> pd.DataFrame:
        cols = [group_by] if isinstance(group_by, str) else group_by
        return df.groupby(cols).agg(aggs).reset_index()

    def join(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        on: str | list[str],
        how: str = "inner",
    ) -> pd.DataFrame:
        return left.merge(right, on=on, how=how)

    # ── Lazy / Collect ──────────────────────────────────────────────

    def collect(self, df: Any) -> pd.DataFrame:
        if isinstance(df, _LazyPandas):
            return df._df
        return df

    def lazy(self, df: pd.DataFrame) -> _LazyPandas:
        return _LazyPandas(df)

    # ── Introspection ───────────────────────────────────────────────

    def shape(self, df: pd.DataFrame) -> tuple[int, int]:
        result: tuple[int, int] = df.shape
        return result

    def columns(self, df: pd.DataFrame) -> list[str]:
        return list(df.columns)

    def dtypes(self, df: pd.DataFrame) -> dict[str, str]:
        return {col: str(dtype) for col, dtype in df.dtypes.items()}

    def head(self, df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
        return df.head(n)

    def memory_usage(self, df: pd.DataFrame) -> int:
        return int(df.memory_usage(deep=True).sum())
