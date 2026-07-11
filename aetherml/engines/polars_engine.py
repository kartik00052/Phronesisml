"""Polars-based data engine.

Implements ``BaseEngine`` using Polars as the computation backend.
Polars is the **default** engine for AetherML — it provides excellent
single-machine performance with native lazy evaluation.

Lazy evaluation is the natural mode here: ``lazy()`` converts a
``DataFrame`` to a ``LazyFrame``, and ``collect()`` materialises
the query plan.  All intermediate operations are optimised by the
Polars query planner before execution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypeAlias

import pandas as pd
import polars as pl

from aetherml.engines.base_engine import BaseEngine, EngineType
from aetherml.exceptions import EngineError

# Polars join "how" parameter literal type.
_HowType: TypeAlias = Literal["inner", "left", "right", "full", "semi", "anti", "cross", "outer"]


class PolarsEngine(BaseEngine):
    """Data engine backed by Polars."""

    engine_type = EngineType.POLARS

    # ── I/O ─────────────────────────────────────────────────────────

    def read(self, path: str | Path, **kwargs: Any) -> pl.DataFrame:
        path = Path(path)
        suffix = path.suffix.lower()
        read_ops: dict[str, Any] = {
            ".csv": pl.read_csv,
            ".parquet": pl.read_parquet,
            ".json": pl.read_ndjson,
            ".jsonl": pl.read_ndjson,
            ".ipc": pl.read_ipc,
        }
        reader = read_ops.get(suffix)
        if reader is None:
            msg = f"Unsupported file format: {suffix}"
            raise EngineError(msg)
        result: pl.DataFrame = reader(path, **kwargs)
        return result

    def write(self, df: pl.DataFrame, path: str | Path, **kwargs: Any) -> None:
        path = Path(path)
        suffix = path.suffix.lower()
        write_ops: dict[str, Any] = {
            ".csv": lambda d, p, **kw: d.write_csv(p, **kw),
            ".parquet": lambda d, p, **kw: d.write_parquet(p, **kw),
            ".json": lambda d, p, **kw: d.write_ndjson(p, **kw),
            ".jsonl": lambda d, p, **kw: d.write_ndjson(p, **kw),
            ".ipc": lambda d, p, **kw: d.write_ipc(p, **kw),
        }
        writer = write_ops.get(suffix)
        if writer is None:
            msg = f"Unsupported file format for writing: {suffix}"
            raise EngineError(msg)
        writer(df, path, **kwargs)

    # ── Transformations ─────────────────────────────────────────────

    def filter(
        self,
        df: pl.DataFrame | pl.LazyFrame,
        conditions: Any,
    ) -> pl.DataFrame | pl.LazyFrame:
        return df.filter(conditions)

    def transform(
        self,
        df: pl.DataFrame | pl.LazyFrame,
        func: Any,
        **kwargs: Any,
    ) -> pl.DataFrame | pl.LazyFrame:
        result: pl.DataFrame | pl.LazyFrame = func(df, **kwargs)
        return result

    def aggregate(
        self,
        df: pl.DataFrame | pl.LazyFrame,
        group_by: list[str] | str,
        aggs: dict[str, Any],
    ) -> pl.DataFrame | pl.LazyFrame:
        cols = [group_by] if isinstance(group_by, str) else group_by
        return df.group_by(cols).agg([pl.col(col).alias(f"{col}_{op}") for col, op in aggs.items()])

    def join(
        self,
        left: pl.DataFrame | pl.LazyFrame,
        right: pl.DataFrame | pl.LazyFrame,
        on: str | list[str],
        how: str = "inner",
    ) -> pl.DataFrame | pl.LazyFrame:
        on_list = [on] if isinstance(on, str) else on
        how_literal = how  # str → _HowType checked at runtime
        if isinstance(left, pl.LazyFrame) and isinstance(right, pl.LazyFrame):
            return left.join(right, on=on_list, how=how_literal)  # type: ignore[arg-type]
        if isinstance(left, pl.DataFrame) and isinstance(right, pl.DataFrame):
            return left.join(right, on=on_list, how=how_literal)  # type: ignore[arg-type]
        msg = f"Cannot join {type(left).__name__} with {type(right).__name__}"
        raise EngineError(msg)

    # ── Lazy / Collect ──────────────────────────────────────────────

    def collect(self, df: Any) -> pd.DataFrame:
        if isinstance(df, pl.LazyFrame):
            return df.collect().to_pandas()
        if isinstance(df, pl.DataFrame):
            return df.to_pandas()
        msg = f"Expected Polars DataFrame or LazyFrame, got {type(df).__name__}"
        raise EngineError(msg)

    def lazy(self, df: pl.DataFrame) -> pl.LazyFrame:
        return df.lazy()

    # ── Introspection ───────────────────────────────────────────────

    def shape(self, df: pl.DataFrame) -> tuple[int, int]:
        return df.shape

    def columns(self, df: pl.DataFrame) -> list[str]:
        return df.columns

    def dtypes(self, df: pl.DataFrame) -> dict[str, str]:
        return {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes, strict=True)}

    def head(self, df: pl.DataFrame, n: int = 5) -> pd.DataFrame:
        return df.head(n).to_pandas()

    def memory_usage(self, df: pl.DataFrame) -> int:
        return int(df.estimated_size("bytes"))
