"""PySpark-based data engine.

Implements ``BaseEngine`` with PySpark for large-scale / distributed
datasets.  Uses lazy Spark DataFrames natively — ``lazy()`` is a no-op
and ``collect()`` converts to Pandas.

Design notes:
- PySpark DataFrames are already lazy (execution is triggered by
  actions like ``collect()``, ``show()``, etc.), so ``lazy()`` is a
  no-op and ``collect()`` converts to Pandas.
- The Spark session is NOT created at import time — it is created
  on first use via ``_get_or_create_session()``.
- PySpark is an optional dependency: ``pip install phronesisml[spark]``.
  If not installed, all methods raise ``ImportError`` with install
  instructions.
- Default master is ``local[*]`` — no remote cluster required for
  development and testing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from phronesisml.engines.base_engine import BaseEngine, EngineType
from phronesisml.exceptions import EngineError


class SparkEngine(BaseEngine):
    """Data engine backed by PySpark.

    Requires ``pyspark`` to be installed: ``pip install phronesisml[spark]``.
    """

    engine_type = EngineType.SPARK

    def __init__(self, master: str = "local[*]") -> None:
        super().__init__()
        self._master = master
        self._session: Any = None

    def _get_or_create_session(self) -> Any:
        if self._session is not None:
            return self._session
        try:
            from pyspark.sql import SparkSession
        except ImportError as exc:
            msg = "PySpark is not installed. Install it with: pip install phronesisml[spark]"
            raise ImportError(msg) from exc
        self._session = SparkSession.builder.master(self._master).appName("Phronesis").getOrCreate()
        return self._session

    # ── I/O ─────────────────────────────────────────────────────────

    def read(self, path: str | Path, **kwargs: Any) -> Any:
        spark = self._get_or_create_session()
        path_str = str(path)
        suffix = Path(path_str).suffix.lower()
        format_map = {
            ".csv": "csv",
            ".parquet": "parquet",
            ".json": "json",
            ".jsonl": "json",
        }
        fmt = format_map.get(suffix)
        if fmt is None:
            msg = f"Unsupported file format: {suffix}"
            raise EngineError(msg)
        reader = spark.read.format(fmt)
        if fmt == "csv":
            reader = reader.option("header", "true").option("inferSchema", "true")
        return reader.load(path_str)

    def write(self, df: Any, path: str | Path, **kwargs: Any) -> None:
        path_str = str(path)
        suffix = Path(path_str).suffix.lower()
        format_map = {".csv": "csv", ".parquet": "parquet", ".json": "json"}
        fmt = format_map.get(suffix)
        if fmt is None:
            msg = f"Unsupported file format for writing: {suffix}"
            raise EngineError(msg)
        writer = df.write.format(fmt)
        if fmt == "csv":
            writer = writer.option("header", "true")
        writer.mode("overwrite").save(path_str)

    # ── Transformations ─────────────────────────────────────────────

    def filter(self, df: Any, conditions: Any) -> Any:
        return df.filter(conditions)

    def transform(self, df: Any, func: Any, **kwargs: Any) -> Any:
        return func(df, **kwargs)

    def aggregate(
        self,
        df: Any,
        group_by: list[str] | str,
        aggs: dict[str, Any],
    ) -> Any:
        from pyspark.sql import functions as F

        cols = [group_by] if isinstance(group_by, str) else group_by
        agg_exprs = [
            F.col(col).__getattribute__(op)().alias(f"{col}_{op}") for col, op in aggs.items()
        ]
        return df.groupBy(cols).agg(*agg_exprs)

    def join(
        self,
        left: Any,
        right: Any,
        on: str | list[str],
        how: str = "inner",
    ) -> Any:
        on_list = [on] if isinstance(on, str) else on
        return left.join(right, on=on_list, how=how)

    # ── Lazy / Collect ──────────────────────────────────────────────

    def collect(self, df: Any) -> pd.DataFrame:
        return df.toPandas()

    def lazy(self, df: Any) -> Any:
        # PySpark DataFrames are already lazy — return as-is.
        return df

    # ── Introspection ───────────────────────────────────────────────

    def shape(self, df: Any) -> tuple[int, int]:
        return (df.count(), len(df.columns))

    def columns(self, df: Any) -> list[str]:
        result: list[str] = df.columns
        return result

    def dtypes(self, df: Any) -> dict[str, str]:
        return {field.name: str(field.dataType) for field in df.schema.fields}

    def head(self, df: Any, n: int = 5) -> pd.DataFrame:
        return df.limit(n).toPandas()

    def memory_usage(self, df: Any) -> int:
        # Approximate: Spark doesn't expose per-DataFrame memory easily.
        # Return 0 to indicate "unknown" — the engine selector should
        # use file-size heuristics instead for Spark-bound data.
        return 0

    def sample(
        self,
        df: Any,
        n: int | None = None,
        fraction: float | None = None,
        random_state: int | None = None,
        strategy: str = "random",
        target_column: str | None = None,
    ) -> Any:
        """Return a sampled subset using Spark's native sampling."""
        if strategy == "head":
            size = n or int(df.count() * (fraction or 1.0))
            return df.limit(size)

        if strategy == "time_aware" and n is not None:
            # Evenly spaced: use modulo-based sampling
            total = df.count()
            step = total / n
            from pyspark.sql import functions as F

            return (
                df.withColumn("_row_id", F.monotonically_increasing_id())
                .filter(F.col("_row_id") % int(step) == 0)
                .limit(n)
                .drop("_row_id")
            )

        # Default: random sampling
        if fraction is not None:
            return df.sample(fraction=min(fraction, 1.0), seed=random_state)
        elif n is not None:
            total = df.count()
            frac = min(n / max(total, 1), 1.0)
            return df.sample(fraction=frac, seed=random_state)
        else:
            return df
