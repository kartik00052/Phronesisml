"""Tests for file_loader: format detection, Excel smart loading, CSV/Parquet."""

from __future__ import annotations

import pandas as pd
import pytest

from phronesisml.data.loaders.file_loader import (
    detect_format,
    list_excel_sheets,
    load_file,
    select_best_sheet,
)
from phronesisml.engines.pandas_engine import PandasEngine
from phronesisml.exceptions import DataLoadError


@pytest.fixture
def engine() -> PandasEngine:
    return PandasEngine()


# ── Format detection ──────────────────────────────────────────────


class TestDetectFormat:
    def test_csv(self, tmp_path: object) -> None:
        p = tmp_path / "data.csv"  # type: ignore[operator]
        assert detect_format(str(p)) == "csv"

    def test_tsv(self, tmp_path: object) -> None:
        p = tmp_path / "data.tsv"  # type: ignore[operator]
        assert detect_format(str(p)) == "csv"

    def test_xlsx(self, tmp_path: object) -> None:
        p = tmp_path / "data.xlsx"  # type: ignore[operator]
        assert detect_format(str(p)) == "excel"

    def test_xls(self, tmp_path: object) -> None:
        p = tmp_path / "data.xls"  # type: ignore[operator]
        assert detect_format(str(p)) == "excel"

    def test_parquet(self, tmp_path: object) -> None:
        p = tmp_path / "data.parquet"  # type: ignore[operator]
        assert detect_format(str(p)) == "parquet"

    def test_json(self, tmp_path: object) -> None:
        p = tmp_path / "data.json"  # type: ignore[operator]
        assert detect_format(str(p)) == "json"

    def test_unknown_raises(self, tmp_path: object) -> None:
        p = tmp_path / "data.xyz"  # type: ignore[operator]
        with pytest.raises(DataLoadError, match="Cannot detect format"):
            detect_format(str(p))


# ── CSV loading ──────────────────────────────────────────────────


class TestLoadCSV:
    def test_simple_csv(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "simple.csv"  # type: ignore[operator]
        pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}).to_csv(p, index=False)
        df = load_file(str(p), engine)
        assert len(df) == 3
        assert list(df.columns) == ["a", "b"]

    def test_tsv(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "data.tsv"  # type: ignore[operator]
        pd.DataFrame({"x": [10, 20]}).to_csv(p, index=False, sep="\t")
        df = load_file(str(p), engine)
        assert len(df) == 2
        assert list(df.columns) == ["x"]

    def test_missing_file_raises(self, engine: PandasEngine) -> None:
        with pytest.raises(DataLoadError, match="does not exist"):
            load_file("/nonexistent/file.csv", engine)

    def test_explicit_format_bypasses_detection(
        self, tmp_path: object, engine: PandasEngine
    ) -> None:
        p = tmp_path / "data.csv"  # type: ignore[operator]
        pd.DataFrame({"c": [1]}).to_csv(p, index=False)
        df = load_file(str(p), engine, format="csv")
        assert len(df) == 1


# ── Excel loading ────────────────────────────────────────────────


class TestLoadExcel:
    def test_single_sheet(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "one_sheet.xlsx"  # type: ignore[operator]
        pd.DataFrame({"val": [1, 2, 3]}).to_excel(p, index=False)
        df = load_file(str(p), engine)
        assert len(df) == 3
        assert list(df.columns) == ["val"]

    def test_multi_sheet_selects_largest(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "multi.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Tiny", index=False)
            pd.DataFrame({"b": range(50)}).to_excel(writer, sheet_name="Big", index=False)
            pd.DataFrame({"c": [1, 2]}).to_excel(writer, sheet_name="Medium", index=False)
        df = load_file(str(p), engine)
        # Should pick "Big" (50 rows) over others
        assert len(df) == 50
        assert list(df.columns) == ["b"]

    def test_empty_sheets_raises(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "empty.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame().to_excel(writer, sheet_name="Empty1", index=False)
            pd.DataFrame().to_excel(writer, sheet_name="Empty2", index=False)
        with pytest.raises(DataLoadError, match="empty"):
            load_file(str(p), engine)

    def test_first_sheet_empty_second_has_data(
        self, tmp_path: object, engine: PandasEngine
    ) -> None:
        p = tmp_path / "tricky.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame().to_excel(writer, sheet_name="Blank", index=False)
            pd.DataFrame({"data": [10, 20, 30]}).to_excel(writer, sheet_name="Actual", index=False)
        df = load_file(str(p), engine)
        assert len(df) == 3
        assert list(df.columns) == ["data"]

    def test_explicit_sheet_name(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "explicit.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame({"x": [1]}).to_excel(writer, sheet_name="First", index=False)
            pd.DataFrame({"y": [2, 3]}).to_excel(writer, sheet_name="Second", index=False)
        df = load_file(str(p), engine, sheet_name="Second")
        assert len(df) == 2
        assert list(df.columns) == ["y"]


# ── list_excel_sheets ────────────────────────────────────────────


class TestListExcelSheets:
    def test_lists_all_sheets(self, tmp_path: object) -> None:
        p = tmp_path / "info.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame({"a": [1, 2]}).to_excel(writer, sheet_name="S1", index=False)
            pd.DataFrame({"b": [3]}).to_excel(writer, sheet_name="S2", index=False)
        sheets = list_excel_sheets(str(p))
        assert len(sheets) == 2
        names = {s["name"] for s in sheets}
        assert names == {"S1", "S2"}
        assert sheets[0]["rows"] == 2
        assert sheets[1]["rows"] == 1

    def test_empty_file(self, tmp_path: object) -> None:
        p = tmp_path / "empty.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame().to_excel(writer, sheet_name="Empty", index=False)
        sheets = list_excel_sheets(str(p))
        assert len(sheets) == 1
        assert sheets[0]["rows"] == 0


# ── select_best_sheet ────────────────────────────────────────────


class TestSelectBestSheet:
    def test_picks_largest_sheet(self, tmp_path: object) -> None:
        p = tmp_path / "best.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Small", index=False)
            pd.DataFrame({"b": range(100)}).to_excel(writer, sheet_name="Large", index=False)
        best = select_best_sheet(str(p))
        assert best == "Large"

    def test_all_empty_raises(self, tmp_path: object) -> None:
        p = tmp_path / "nope.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame().to_excel(writer, sheet_name="Empty", index=False)
        with pytest.raises(DataLoadError, match="empty"):
            select_best_sheet(str(p))
