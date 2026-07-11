"""Unit tests for engine modules: base, Polars, and Spark."""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import polars as pl
import pytest

from aetherml.engines.base_engine import BaseEngine, EngineType
from aetherml.engines.polars_engine import PolarsEngine
from aetherml.engines.spark_engine import SparkEngine
from aetherml.exceptions import EngineError

try:
    import pyarrow  # noqa: F401

    _has_pyarrow = True
except ImportError:
    _has_pyarrow = False


# ── Base Engine ──────────────────────────────────────────────────────────


class TestEngineType:
    def test_enum_values(self) -> None:
        assert EngineType.PANDAS == "pandas"
        assert EngineType.POLARS == "polars"
        assert EngineType.SPARK == "spark"

    def test_is_str_enum(self) -> None:
        assert issubclass(EngineType, str)
        assert isinstance(EngineType.PANDAS, str)

    def test_string_comparison(self) -> None:
        assert EngineType.PANDAS == "pandas"
        assert EngineType.POLARS != "pandas"


class TestBaseEngine:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError, match="abstract method"):
            BaseEngine()  # type: ignore[abstract]

    def test_is_abc(self) -> None:
        assert issubclass(BaseEngine, ABC)


# ── Polars Engine ────────────────────────────────────────────────────────


class TestPolarsEngineIO:
    def test_read_csv(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n")
        engine = PolarsEngine()
        result = engine.read(csv_file)
        assert isinstance(result, pl.DataFrame)
        assert result.shape == (2, 2)

    def test_write_csv(self, tmp_path: Path) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        out_file = tmp_path / "out.csv"
        engine.write(df, out_file)
        assert out_file.exists()

    def test_read_json(self, tmp_path: Path) -> None:
        json_file = tmp_path / "test.json"
        json_file.write_text('{"a":1,"b":2}\n{"a":3,"b":4}\n')
        engine = PolarsEngine()
        result = engine.read(json_file)
        assert isinstance(result, pl.DataFrame)
        assert result.shape == (2, 2)

    def test_write_json(self, tmp_path: Path) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        out_file = tmp_path / "out.json"
        engine.write(df, out_file)
        assert out_file.exists()

    def test_read_parquet(self, tmp_path: Path) -> None:
        pq_file = tmp_path / "test.parquet"
        pl.DataFrame({"a": [1, 2], "b": [3, 4]}).write_parquet(pq_file)
        engine = PolarsEngine()
        result = engine.read(pq_file)
        assert isinstance(result, pl.DataFrame)
        assert result.shape == (2, 2)

    def test_write_parquet(self, tmp_path: Path) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        out_file = tmp_path / "out.parquet"
        engine.write(df, out_file)
        assert out_file.exists()

    def test_read_unknown_extension_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("a,b\n1,2\n")
        engine = PolarsEngine()
        with pytest.raises(EngineError, match="Unsupported file format"):
            engine.read(bad_file)

    def test_write_unknown_extension_raises(self, tmp_path: Path) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1]})
        with pytest.raises(EngineError, match="Unsupported file format for writing"):
            engine.write(df, Path("out.xyz"))


class TestPolarsEngineCollect:
    @pytest.mark.skipif(
        not _has_pyarrow,
        reason="pyarrow not installed",
    )
    def test_collect_lazy_frame(self) -> None:
        engine = PolarsEngine()
        lf = pl.DataFrame({"a": [1, 2]}).lazy()
        result = engine.collect(lf)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @pytest.mark.skipif(
        not _has_pyarrow,
        reason="pyarrow not installed",
    )
    def test_collect_eager_frame(self) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1, 2]})
        result = engine.collect(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_collect_invalid_type_raises(self) -> None:
        engine = PolarsEngine()
        with pytest.raises(EngineError, match="Expected Polars"):
            engine.collect("not a dataframe")


class TestPolarsEngineLazy:
    def test_lazy_returns_lazy_frame(self) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1, 2]})
        result = engine.lazy(df)
        assert isinstance(result, pl.LazyFrame)


class TestPolarsEngineIntrospection:
    def test_shape(self) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        assert engine.shape(df) == (3, 2)

    def test_columns(self) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"x": [1], "y": [2]})
        assert engine.columns(df) == ["x", "y"]

    def test_dtypes(self) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1], "b": [1.0]})
        dtypes = engine.dtypes(df)
        assert "a" in dtypes
        assert "b" in dtypes

    @pytest.mark.skipif(not _has_pyarrow, reason="pyarrow not installed")
    def test_head(self) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": list(range(10))})
        result = engine.head(df, n=3)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_memory_usage(self) -> None:
        engine = PolarsEngine()
        df = pl.DataFrame({"a": [1, 2, 3]})
        usage = engine.memory_usage(df)
        assert usage > 0


class TestPolarsEngineRepr:
    def test_repr(self) -> None:
        engine = PolarsEngine()
        assert "PolarsEngine" in repr(engine)
        assert "polars" in repr(engine)


# ── Spark Engine ─────────────────────────────────────────────────────────


class TestSparkEngine:
    def test_get_or_create_session_raises_import_error(self) -> None:
        engine = SparkEngine()
        with (
            patch.dict("sys.modules", {"pyspark": None, "pyspark.sql": None}),
            pytest.raises(ImportError, match="PySpark is not installed"),
        ):
            engine._get_or_create_session()

    def test_lazy_returns_input_unchanged(self) -> None:
        engine = SparkEngine()
        mock_df = object()
        result = engine.lazy(mock_df)
        assert result is mock_df

    def test_memory_usage_returns_zero(self) -> None:
        engine = SparkEngine()
        result = engine.memory_usage(object())
        assert result == 0

    def test_engine_type(self) -> None:
        engine = SparkEngine()
        assert engine.engine_type == EngineType.SPARK

    def test_repr(self) -> None:
        engine = SparkEngine()
        assert "SparkEngine" in repr(engine)
        assert "spark" in repr(engine)
