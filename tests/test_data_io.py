"""Tests for the data ingestion toolkit (``phronesisml.data.io``).

Covers loaders, dataset utilities, and composition helpers.  All tests are
offline and deterministic.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from phronesisml.data import (
    concatenate_datasets,
    dataset_summary,
    detect_encoding,
    estimate_dataset_size,
    infer_file_type,
    load_csv,
    load_directory,
    load_json,
    load_jsonl,
    load_multiple_files,
    load_parquet,
    load_tsv,
    load_zip,
    merge_datasets,
    preview_dataset,
    stream_large_dataset,
)
from phronesisml.exceptions import DataLoadError


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "id": np.arange(50),
            "value": rng.normal(0, 1, 50),
            "label": [f"x{i % 5}" for i in range(50)],
        }
    )


@pytest.fixture()
def data_dir(tmp_path: Path, sample_df: pd.DataFrame) -> Path:
    sample_df.to_csv(tmp_path / "a.csv", index=False)
    sample_df.to_csv(tmp_path / "b.tsv", sep="\t", index=False)
    sample_df.to_json(tmp_path / "c.json", orient="records")
    sample_df.to_json(tmp_path / "d.jsonl", orient="records", lines=True)
    sample_df.to_parquet(tmp_path / "e.parquet", index=False)
    nested = tmp_path / "nested"
    nested.mkdir()
    sample_df.head(10).to_csv(nested / "f.csv", index=False)
    sample_df.to_csv(tmp_path / "g.csv", index=False)
    return tmp_path


def test_load_csv(data_dir: Path, sample_df: pd.DataFrame) -> None:
    result = load_csv(data_dir / "a.csv")
    assert result.shape == sample_df.shape
    assert list(result.columns) == list(sample_df.columns)


def test_load_tsv(data_dir: Path, sample_df: pd.DataFrame) -> None:
    result = load_tsv(data_dir / "b.tsv")
    assert result.shape == sample_df.shape


def test_load_json(data_dir: Path, sample_df: pd.DataFrame) -> None:
    result = load_json(data_dir / "c.json")
    assert result.shape == sample_df.shape


def test_load_jsonl(data_dir: Path, sample_df: pd.DataFrame) -> None:
    result = load_jsonl(data_dir / "d.jsonl")
    assert result.shape == sample_df.shape


def test_load_parquet(data_dir: Path, sample_df: pd.DataFrame) -> None:
    result = load_parquet(data_dir / "e.parquet")
    assert result.shape == sample_df.shape


def test_load_missing_file_raises(data_dir: Path) -> None:
    with pytest.raises(DataLoadError):
        load_csv(data_dir / "missing.csv")


def test_load_directory_sorted(data_dir: Path) -> None:
    loaded = load_directory(data_dir, pattern="*.csv", recursive=False)
    assert sorted(loaded) == list(loaded)


def test_load_directory_recursive(data_dir: Path, sample_df: pd.DataFrame) -> None:
    loaded = load_directory(data_dir, pattern="*.csv")
    assert len(loaded) == 3
    shapes = {v.shape for v in loaded.values()}
    assert shapes == {sample_df.shape, sample_df.head(10).shape}


def test_load_directory_no_match_raises(tmp_path: Path) -> None:
    with pytest.raises(DataLoadError):
        load_directory(tmp_path, pattern="*.nope")


def test_load_multiple_files_concat(data_dir: Path, sample_df: pd.DataFrame) -> None:
    combined = load_multiple_files([data_dir / "a.csv", data_dir / "g.csv"])
    assert isinstance(combined, pd.DataFrame)
    assert combined.shape[0] == sample_df.shape[0] * 2


def test_load_multiple_files_dict(data_dir: Path) -> None:
    loaded = load_multiple_files([data_dir / "a.csv"], combine="dict")
    assert isinstance(loaded, dict)
    assert len(loaded) == 1


def test_load_multiple_files_bad_combine_raises(data_dir: Path) -> None:
    with pytest.raises(DataLoadError):
        load_multiple_files([data_dir / "a.csv"], combine="bogus")


def test_load_zip(data_dir: Path, sample_df: pd.DataFrame) -> None:
    zip_path = data_dir / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.write(data_dir / "a.csv", "a.csv")
    loaded = load_zip(zip_path)
    assert isinstance(loaded, dict)
    assert loaded["a.csv"].shape == sample_df.shape


def test_load_zip_member(data_dir: Path, sample_df: pd.DataFrame) -> None:
    zip_path = data_dir / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.write(data_dir / "a.csv", "a.csv")
    result = load_zip(zip_path, member="a.csv")
    assert isinstance(result, pd.DataFrame)
    assert result.shape == sample_df.shape


def test_merge_datasets(sample_df: pd.DataFrame) -> None:
    right = sample_df[["id", "label"]].rename(columns={"label": "label2"})
    merged = merge_datasets(sample_df, right, on="id")
    assert "label2" in merged.columns
    assert merged.shape[0] == sample_df.shape[0]


def test_concatenate_datasets(sample_df: pd.DataFrame) -> None:
    combined = concatenate_datasets([sample_df, sample_df])
    assert combined.shape[0] == sample_df.shape[0] * 2


def test_infer_file_type(data_dir: Path) -> None:
    info = infer_file_type(data_dir / "a.csv")
    assert info == {"format": "csv", "family": "tabular", "extension": ".csv"}


def test_detect_encoding_utf8(data_dir: Path) -> None:
    assert detect_encoding(data_dir / "a.csv") == "utf-8"


def test_preview_dataset(sample_df: pd.DataFrame) -> None:
    preview = preview_dataset(sample_df, n=2)
    assert preview["shape"] == {"rows": 50, "columns": 3}
    assert len(preview["preview"]) == 2


def test_estimate_dataset_size(data_dir: Path) -> None:
    info = estimate_dataset_size(data_dir / "a.csv")
    assert info["file_size_bytes"] > 0
    assert info["extension"] == ".csv"
    assert info["estimated_rows"] == 51  # header + 50 rows


def test_dataset_summary(sample_df: pd.DataFrame) -> None:
    summary = dataset_summary(sample_df)
    assert summary["shape"] == {"rows": 50, "columns": 3}
    assert summary["duplicate_rows"] == 0
    assert "value" in summary["numeric_columns"]
    assert "label" in summary["categorical_columns"]


def test_stream_large_dataset(data_dir: Path) -> None:
    chunks = list(stream_large_dataset(data_dir / "a.csv", chunksize=10))
    assert len(chunks) == 5
    assert sum(c.shape[0] for c in chunks) == 50
