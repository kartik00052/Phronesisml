"""Tests for engine-light resource estimation and engine recommendation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from phronesisml.engines import (
    engine_capabilities,
    engine_comparison_report,
    recommend_engine,
)
from phronesisml.utils.resources import (
    check_memory_sufficiency,
    estimate_dataframe_memory,
    estimate_model_size_mb,
    estimate_training_time,
    format_bytes,
    format_seconds,
)


def test_format_bytes() -> None:
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.0 MB"


def test_format_seconds() -> None:
    assert format_seconds(0) == "0:00:00"
    assert format_seconds(65) == "0:01:05"
    assert format_seconds(3723) == "1:02:03"


def test_estimate_dataframe_memory() -> None:
    df = pd.DataFrame({"a": np.arange(1000, dtype="float64")})
    report = estimate_dataframe_memory(df)
    assert report["estimated_rows"] == 1000
    assert report["memory_bytes"] > 0
    assert report["memory_mb"] > 0


def test_estimate_training_time() -> None:
    report = estimate_training_time(n_rows=1_000_000, n_features=100)
    assert report["complexity"] == "medium"
    assert report["estimated_seconds"] > 0
    assert report["estimated_runtime"].count(":") == 2


def test_estimate_training_time_complexity() -> None:
    low = estimate_training_time(n_rows=1000, n_features=10, complexity="low")
    high = estimate_training_time(n_rows=1000, n_features=10, complexity="high")
    assert high["estimated_seconds"] > low["estimated_seconds"]


def test_estimate_model_size_mb() -> None:
    report = estimate_model_size_mb(n_features=100, n_classes=10)
    assert report["estimated_mb"] > 0
    assert report["estimated_bytes"] == 100 * 10 * 8 * 100


def test_check_memory_sufficiency_ok() -> None:
    report = check_memory_sufficiency(required_mb=100, available_gb=8)
    assert report["sufficient"] is True
    assert report["severity"] == "ok"


def test_check_memory_sufficiency_blocked() -> None:
    report = check_memory_sufficiency(required_mb=8192, available_gb=8)
    assert report["sufficient"] is False
    assert report["severity"] == "blocked"


def test_check_memory_sufficiency_warning() -> None:
    report = check_memory_sufficiency(required_mb=5000, available_gb=8)
    assert report["sufficient"] is True
    assert report["severity"] == "warning"


def test_recommend_engine_pandas() -> None:
    report = recommend_engine(n_rows=100, n_cols=5, memory_bytes=1_000)
    assert report["engine"] == "pandas"


def test_recommend_engine_polars() -> None:
    report = recommend_engine(memory_bytes=100 * 1024 * 1024)
    assert report["engine"] == "polars"


def test_recommend_engine_spark() -> None:
    report = recommend_engine(memory_bytes=5_000_000_000)
    assert report["engine"] == "spark"


def test_engine_capabilities() -> None:
    caps = engine_capabilities()
    assert set(caps["engines"]) == {"pandas", "polars", "spark"}
    assert any(c["key"] == "distributed" for c in caps["capabilities"])
    assert caps["matrix"]["spark"]["distributed"] is True
    assert caps["matrix"]["pandas"]["distributed"] is False


def test_engine_comparison_report() -> None:
    report = engine_comparison_report(n_rows=10, n_cols=3, memory_bytes=1_000)
    assert report["recommendation"]["engine"] == "pandas"
    assert report["input"] == {"n_rows": 10, "n_cols": 3, "memory_bytes": 1000}
    assert "capabilities" in report
