"""Retroactive tests for performance/robustness changes in Phases 2, 3, 6.

These tests cover specific behavior that was modified without dedicated tests:
- Upload agent: file-size guard and single getsize() call
- Engine selector: _DATA_EXTENSIONS filter for directory estimation
- Target detection: vectorized nunique()
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

# ── Upload agent: file-size guard ─────────────────────────────────────


class TestUploadFileSizeGuard:
    """Test the file-size guard in UploadAgent."""

    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self, tmp_path: Path) -> None:
        from phronesisml.agents.upload.agent import UploadAgent
        from phronesisml.engines.pandas_engine import PandasEngine

        big_file = tmp_path / "big.csv"
        big_file.write_text("a,b\n1,2\n")

        agent = UploadAgent(engine=PandasEngine())
        state = SimpleNamespace(
            data_path=str(big_file),
            max_file_size_bytes=1,  # 1 byte — our file exceeds this
        )

        result = await agent.run(state)
        assert not result.success
        assert "File too large" in result.error

    @pytest.mark.asyncio
    async def test_accepts_file_under_limit(self, tmp_path: Path) -> None:
        from phronesisml.agents.upload.agent import UploadAgent
        from phronesisml.engines.pandas_engine import PandasEngine

        csv_file = tmp_path / "small.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n")

        agent = UploadAgent(engine=PandasEngine())
        state = SimpleNamespace(
            data_path=str(csv_file),
            max_file_size_bytes=1_000_000,  # 1 MB — plenty
        )

        result = await agent.run(state)
        assert result.success

    @pytest.mark.asyncio
    async def test_single_getsize_call(self, tmp_path: Path) -> None:
        """Verify os.path.getsize is called for the size check."""
        from phronesisml.agents.upload.agent import UploadAgent
        from phronesisml.engines.pandas_engine import PandasEngine

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        agent = UploadAgent(engine=PandasEngine())
        state = SimpleNamespace(
            data_path=str(csv_file),
            max_file_size_bytes=1_000_000,
        )

        patch_target = "phronesisml.agents.upload.agent.os.path.getsize"
        with patch(patch_target, return_value=100) as mock_getsize:
            await agent.run(state)
            # getsize called once for the size guard check
            assert mock_getsize.call_count == 1


# ── Engine selector: _DATA_EXTENSIONS filter ──────────────────────────


class TestDataExtensionsFilter:
    """Test that _estimate_file_size only counts data files in directories."""

    def test_counts_only_data_files(self, tmp_path: Path) -> None:
        from phronesisml.engines.engine_selector import _estimate_file_size

        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n")
        parquet_file = tmp_path / "data.parquet"
        parquet_file.write_bytes(b"fake parquet")

        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("not a data file")
        py_file = tmp_path / "script.py"
        py_file.write_text("print('hello')")

        total = _estimate_file_size(tmp_path)
        expected = csv_file.stat().st_size + parquet_file.stat().st_size
        assert total == expected

    def test_single_file_ignores_extension(self, tmp_path: Path) -> None:
        from phronesisml.engines.engine_selector import _estimate_file_size

        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("hello")
        assert _estimate_file_size(txt_file) == txt_file.stat().st_size

    def test_nonexistent_path_returns_zero(self) -> None:
        from phronesisml.engines.engine_selector import _estimate_file_size

        assert _estimate_file_size("/nonexistent/path/xyz.csv") == 0

    def test_empty_directory_returns_zero(self, tmp_path: Path) -> None:
        from phronesisml.engines.engine_selector import _estimate_file_size

        assert _estimate_file_size(tmp_path) == 0


# ── Target detection: vectorized nunique() ────────────────────────────


class TestTargetDetectionNunique:
    """Test that detect_target uses vectorized nunique() correctly."""

    def test_nunique_vectorized(self, pandas_engine: Any) -> None:
        from phronesisml.data.profilers.stats import profile_dataset
        from phronesisml.ml.target_detection.detector import detect_target

        df = pd.DataFrame(
            {
                "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0],
                "feature_b": [10, 20, 30, 40, 50],
                "label": ["A", "B", "A", "B", "A"],
            }
        )
        profile = profile_dataset(df, pandas_engine)

        # PandasEngine.collect() returns the DataFrame as-is
        result = detect_target(df, pandas_engine, profile)
        assert "target_column" in result
        assert "task_type" in result
        assert "confidence" in result
        assert result["target_column"] == "label"
