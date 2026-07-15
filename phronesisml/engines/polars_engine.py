"""Polars-based data engine.

Implements ``BaseEngine`` using Polars as the computation backend.
Polars is the **default** engine for Phronesis — it provides excellent
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

from phronesisml.engines.base_engine import BaseEngine, EngineType
from phronesisml.exceptions import EngineError

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
        if isinstance(df, pd.DataFrame):
            return df
        msg = f"Expected Polars DataFrame, LazyFrame, or Pandas DataFrame, got {type(df).__name__}"
        raise EngineError(msg)

    def lazy(self, df: pl.DataFrame) -> pl.LazyFrame:
        return df.lazy()

    # ── Introspection ───────────────────────────────────────────────

    def shape(self, df: pl.DataFrame) -> tuple[int, int]:
        return df.shape

    def columns(self, df: Any) -> list[str]:
        if isinstance(df, pd.DataFrame):
            return list(df.columns)
        result: list[str] = df.columns
        return result

    def dtypes(self, df: pl.DataFrame) -> dict[str, str]:
        return {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes, strict=True)}

    def head(self, df: Any, n: int = 5) -> pd.DataFrame:
        if isinstance(df, pd.DataFrame):
            return df.head(n)
        return df.head(n).to_pandas()

    def memory_usage(self, df: Any) -> int:
        if isinstance(df, pd.DataFrame):
            return int(df.memory_usage(deep=True).sum())
        if isinstance(df, pl.LazyFrame):
            return int(df.collect().estimated_size("bytes"))
        if isinstance(df, pl.DataFrame):
            return int(df.estimated_size("bytes"))
        msg = f"Expected DataFrame or LazyFrame, got {type(df).__name__}"
        raise EngineError(msg)

    def sample(
        self,
        df: Any,
        n: int | None = None,
        fraction: float | None = None,
        random_state: int | None = None,
        strategy: str = "random",
        target_column: str | None = None,
    ) -> pl.DataFrame:
        """Return a sampled subset using Polars native sampling."""
        if isinstance(df, pl.LazyFrame):
            df = df.collect()

        n_rows = len(df)

        if strategy == "head":
            size = n or int(n_rows * (fraction or 1.0))
            return df.head(size)  # type: ignore[no-any-return]

        if strategy == "time_aware" and n is not None:
            # Evenly spaced indices for temporal preservation
            step = n_rows / n
            indices = [int(i * step) for i in range(n)]
            return df[indices]  # type: ignore[no-any-return]

        if strategy == "stratified" and target_column and n is not None:
            # Polars doesn't have native stratified sampling — convert to pandas
            pd_df = df.to_pandas()
            try:
                from sklearn.model_selection import train_test_split

                fraction_val = n / n_rows
                sampled, _ = train_test_split(
                    pd_df,
                    train_size=fraction_val,
                    stratify=pd_df[target_column],
                    random_state=random_state,
                )
                return pl.from_pandas(sampled.reset_index(drop=True))
            except (ValueError, ImportError):
                # Fallback to random
                pass

        # Default: random sampling
        if n is not None:
            return df.sample(n=min(n, n_rows), seed=random_state)  # type: ignore[no-any-return]
        elif fraction is not None:
            return df.sample(fraction=min(fraction, 1.0), seed=random_state)  # type: ignore[no-any-return]
        else:
            return df  # type: ignore[no-any-return]
