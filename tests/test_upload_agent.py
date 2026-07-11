"""Tests for the UploadAgent — Excel, CSV, and error handling."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from aetherml.agents.upload.agent import UploadAgent
from aetherml.engines.pandas_engine import PandasEngine


@pytest.fixture
def engine() -> PandasEngine:
    return PandasEngine()


class TestUploadAgentCSV:
    async def test_loads_csv(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "data.csv"  # type: ignore[operator]
        pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(p, index=False)
        agent = UploadAgent(engine=engine)
        state = SimpleNamespace(data_path=str(p))
        result = await agent.run(state)
        assert result.success
        assert result.data["row_count"] == 2
        assert result.data["file_format"] == "csv"
        assert list(result.data["raw_data"].columns) == ["a", "b"]

    async def test_no_data_path(self, engine: PandasEngine) -> None:
        agent = UploadAgent(engine=engine)
        state = SimpleNamespace(data_path=None)
        result = await agent.run(state)
        assert not result.success
        assert "No data_path" in result.error


class TestUploadAgentExcel:
    async def test_loads_single_sheet_excel(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "single.xlsx"  # type: ignore[operator]
        pd.DataFrame({"x": [10, 20, 30]}).to_excel(p, index=False)
        agent = UploadAgent(engine=engine)
        state = SimpleNamespace(data_path=str(p))
        result = await agent.run(state)
        assert result.success
        assert result.data["row_count"] == 3
        assert result.data["file_format"] == "excel"

    async def test_multi_sheet_picks_largest(self, tmp_path: object, engine: PandasEngine) -> None:
        p = tmp_path / "multi.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Tiny", index=False)
            pd.DataFrame({"b": range(100)}).to_excel(writer, sheet_name="Big", index=False)
        agent = UploadAgent(engine=engine)
        state = SimpleNamespace(data_path=str(p))
        result = await agent.run(state)
        assert result.success
        assert result.data["row_count"] == 100
        assert list(result.data["raw_data"].columns) == ["b"]
        # Check metadata includes sheet info
        assert "excel_sheets" in result.metadata
        sheets = result.metadata["excel_sheets"]
        assert len(sheets) == 2

    async def test_first_sheet_empty_second_has_data(
        self, tmp_path: object, engine: PandasEngine
    ) -> None:
        p = tmp_path / "tricky.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame().to_excel(writer, sheet_name="Blank", index=False)
            pd.DataFrame({"val": [1, 2, 3, 4, 5]}).to_excel(writer, sheet_name="Data", index=False)
        agent = UploadAgent(engine=engine)
        state = SimpleNamespace(data_path=str(p))
        result = await agent.run(state)
        assert result.success
        assert result.data["row_count"] == 5
        assert list(result.data["raw_data"].columns) == ["val"]
