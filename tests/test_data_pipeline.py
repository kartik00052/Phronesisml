"""Unit tests for data pipeline modules: file loader and cleaning transformers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from aetherml.data.loaders.file_loader import detect_format, load_file
from aetherml.data.transformers.cleaning import (
    cast_dtypes,
    encode_categoricals,
    handle_nulls,
)
from aetherml.exceptions import DataLoadError, DataTransformError

# ── File Loader: detect_format ───────────────────────────────────────────


class TestDetectFormat:
    def test_csv(self) -> None:
        assert detect_format("data.csv") == "csv"

    def test_tsv(self) -> None:
        assert detect_format("data.tsv") == "csv"

    def test_parquet(self) -> None:
        assert detect_format("data.parquet") == "parquet"

    def test_pq(self) -> None:
        assert detect_format("data.pq") == "parquet"

    def test_json(self) -> None:
        assert detect_format("data.json") == "json"

    def test_jsonl(self) -> None:
        assert detect_format("data.jsonl") == "json"

    def test_ndjson(self) -> None:
        assert detect_format("data.ndjson") == "json"

    def test_feather(self) -> None:
        assert detect_format("data.feather") == "feather"

    def test_arrow(self) -> None:
        assert detect_format("data.arrow") == "feather"

    def test_xlsx(self) -> None:
        assert detect_format("data.xlsx") == "excel"

    def test_xls(self) -> None:
        assert detect_format("data.xls") == "excel"

    def test_unknown_extension_raises(self) -> None:
        with pytest.raises(DataLoadError, match="Cannot detect format"):
            detect_format("data.xyz")

    def test_case_insensitive(self) -> None:
        assert detect_format("data.CSV") == "csv"
        assert detect_format("data.Csv") == "csv"
        assert detect_format("data.PARQUET") == "parquet"
        assert detect_format("data.JSON") == "json"


# ── File Loader: load_file ──────────────────────────────────────────────


class TestLoadFile:
    def test_nonexistent_file_raises(self) -> None:
        engine = MagicMock()
        with pytest.raises(DataLoadError, match="does not exist"):
            load_file("/nonexistent/data.csv", engine)

    def test_delegates_to_engine_read(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        engine = MagicMock()
        mock_df = pd.DataFrame({"a": [1], "b": [2]})
        engine.read.return_value = mock_df
        engine.collect.return_value = mock_df

        result = load_file(csv_file, engine)
        engine.read.assert_called_once()
        engine.collect.assert_called_once_with(mock_df)
        assert len(result) == 1

    def test_explicit_format_override(self, tmp_path: Path) -> None:
        data_file = tmp_path / "test.xyz"
        data_file.write_text("a,b\n1,2\n")

        engine = MagicMock()
        mock_df = pd.DataFrame({"a": [1], "b": [2]})
        engine.read.return_value = mock_df
        engine.collect.return_value = mock_df

        result = load_file(data_file, engine, format="csv")
        engine.read.assert_called_once()
        assert len(result) == 1


# ── Cleaning: handle_nulls ──────────────────────────────────────────────


class TestHandleNulls:
    def test_invalid_strategy_raises(self) -> None:
        df = pd.DataFrame({"a": [1, None]})
        with pytest.raises(DataTransformError, match="Unknown null strategy"):
            handle_nulls(df, strategy="invalid")

    def test_drop_removes_rows(self) -> None:
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, 6]})
        result, log = handle_nulls(df, strategy="drop")
        assert len(result) == 2
        assert log["strategy"] == "drop"
        assert log["columns_affected"] == 1

    def test_fill_replaces_nulls(self) -> None:
        df = pd.DataFrame({"a": [1.0, None, 3.0]})
        result, log = handle_nulls(df, strategy="fill", fill_value=0)
        assert result["a"].tolist() == [1.0, 0.0, 3.0]
        assert log["strategy"] == "fill"

    def test_flag_adds_indicator_columns(self) -> None:
        df = pd.DataFrame({"a": [1.0, None, 3.0]})
        result, log = handle_nulls(df, strategy="flag")
        assert "a_is_null" in result.columns
        assert result["a_is_null"].tolist() == [0, 1, 0]
        assert log["strategy"] == "flag"

    def test_no_nulls_returns_original(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result, log = handle_nulls(df, strategy="drop")
        assert len(result) == 3
        assert log["columns_affected"] == 0

    def test_specific_columns(self) -> None:
        df = pd.DataFrame({"a": [1.0, None], "b": [None, 2.0]})
        result, log = handle_nulls(df, strategy="fill", fill_value=0, columns=["a"])
        assert result["a"].tolist() == [1.0, 0.0]
        assert pd.isna(result["b"].iloc[0])


# ── Cleaning: cast_dtypes ───────────────────────────────────────────────


class TestCastDtypes:
    def test_nonexistent_column_raises(self) -> None:
        df = pd.DataFrame({"a": [1, 2]})
        with pytest.raises(DataTransformError, match="not found"):
            cast_dtypes(df, {"missing": "float64"})

    def test_successful_cast(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result, log = cast_dtypes(df, {"a": "float64"})
        assert result["a"].dtype == "float64"
        assert "a" in log["columns_cast"]

    def test_incompatible_cast_raises(self) -> None:
        df = pd.DataFrame({"a": ["hello", "world"]})
        with pytest.raises(DataTransformError, match="Failed to cast"):
            cast_dtypes(df, {"a": "int64"})


# ── Cleaning: encode_categoricals ───────────────────────────────────────


class TestEncodeCategoricals:
    def test_auto_detects_object_columns(self) -> None:
        df = pd.DataFrame({"a": ["x", "y", "z"], "b": [1, 2, 3]})
        result, log = encode_categoricals(df)
        assert result["a"].dtype != "object"
        assert result["b"].dtype == "int64"
        assert "a" in log["columns_encoded"]

    def test_label_encoding_works(self) -> None:
        df = pd.DataFrame({"a": ["cat", "dog", "cat"]})
        result, log = encode_categoricals(df, columns=["a"])
        assert result["a"].dtype != "object"
        # "cat" should map to 0, "dog" to 1
        assert set(result["a"].unique()) == {0, 1}

    def test_no_objects_returns_original(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
        result, log = encode_categoricals(df)
        assert log["columns_encoded"] == 0
        assert result["a"].tolist() == [1, 2, 3]

    def test_unsupported_strategy_raises(self) -> None:
        df = pd.DataFrame({"a": ["x", "y"]})
        with pytest.raises(DataTransformError, match="Unsupported encoding"):
            encode_categoricals(df, strategy="onehot")

    def test_multiple_columns(self) -> None:
        df = pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"], "c": [1, 2]})
        result, log = encode_categoricals(df, columns=["a", "b"])
        assert result["a"].dtype != "object"
        assert result["b"].dtype != "object"
        assert result["c"].dtype == "int64"
