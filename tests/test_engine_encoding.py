"""Engine-level tests for non-UTF-8 CSV/TSV decoding.

Regression coverage for uploads exported as Windows-1252 / Latin-1 (e.g.
Excel exports containing ``£`` or accented characters), which previously
raised ``UnicodeDecodeError`` (pandas) or ``ComputeError`` (polars).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from phronesisml.engines.pandas_engine import PandasEngine
from phronesisml.engines.polars_engine import PolarsEngine

_ROWS = "name,price\nCafé,3.50\nCrème brûlée,4.25\nNaïve,1.00\n"


@pytest.fixture()
def cp1252_csv(tmp_path: Path) -> Path:
    path = tmp_path / "retail.csv"
    path.write_bytes(_ROWS.encode("cp1252"))
    return path


def test_pandas_engine_reads_cp1252_csv(cp1252_csv: Path) -> None:
    df = PandasEngine().read(cp1252_csv)
    assert df.shape == (3, 2)
    assert df["name"].tolist() == ["Café", "Crème brûlée", "Naïve"]


def test_polars_engine_reads_cp1252_csv(cp1252_csv: Path) -> None:
    df = PolarsEngine().read(cp1252_csv)
    assert df.shape == (3, 2)
    assert df["name"].to_list() == ["Café", "Crème brûlée", "Naïve"]


def test_polars_engine_reads_cp1252_tsv(tmp_path: Path) -> None:
    path = tmp_path / "retail.tsv"
    path.write_bytes(_ROWS.replace(",", "\t").encode("cp1252"))
    df = PolarsEngine().read(path)
    assert df.shape == (3, 2)
    assert df["name"].to_list() == ["Café", "Crème brûlée", "Naïve"]


def test_engines_still_read_utf8(tmp_path: Path) -> None:
    path = tmp_path / "utf8.csv"
    path.write_text(_ROWS, encoding="utf-8")
    assert PandasEngine().read(path).shape == (3, 2)
    assert PolarsEngine().read(path).shape == (3, 2)
