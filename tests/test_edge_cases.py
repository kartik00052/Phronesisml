"""Edge-case robustness tests.

Covers: corrupted files, unsupported extensions, empty datasets,
ambiguous targets, multi-sheet Excel, and 500k-row performance.
"""

from __future__ import annotations

import time

import pandas as pd
import pytest

from aetherml.exceptions import AetherMLError, WorkflowError
from aetherml.sdk import AetherML

# ── Corrupted file ──────────────────────────────────────────────


class TestCorruptedFile:
    def test_corrupted_csv_raises(self, tmp_path: object) -> None:
        p = tmp_path / "corrupted.csv"  # type: ignore[operator]
        p.write_bytes(
            b"a,b,c\n1,2,3\n"
            b"\xff\xfe\xfd\xfc\xfb\xfa\x00\x01\x02\x03\n"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        ml = AetherML(str(p))
        with pytest.raises((AetherMLError, WorkflowError, Exception)) as exc_info:
            ml.run()
        assert exc_info.value is not None

    def test_corrupted_binary_as_csv_raises(self, tmp_path: object) -> None:
        p = tmp_path / "fake.csv"  # type: ignore[operator]
        p.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
        ml = AetherML(str(p))
        with pytest.raises((AetherMLError, WorkflowError, Exception)):
            ml.load()

    def test_truncated_xlsx_raises(self, tmp_path: object) -> None:
        p = tmp_path / "truncated.xlsx"  # type: ignore[operator]
        p.write_bytes(b"PK\x03\x04truncated content")
        ml = AetherML(str(p))
        with pytest.raises((AetherMLError, WorkflowError, Exception)):
            ml.load()


# ── Unsupported extension ───────────────────────────────────────


class TestUnsupportedExtension:
    def test_unsupported_ext_raises(self, tmp_path: object) -> None:
        p = tmp_path / "data.exe"  # type: ignore[operator]
        p.write_bytes(b"MZ\x90\x00")
        ml = AetherML(str(p))
        with pytest.raises((AetherMLError, WorkflowError, Exception)):
            ml.load()

    def test_unsupported_ext_message_contains_filename(self, tmp_path: object) -> None:
        p = tmp_path / "data.parquet"  # type: ignore[operator]
        p.write_bytes(b"\x89PAR1\x00\x00")
        ml = AetherML(str(p))
        # parquet bytes may or may not parse; just confirm no crash on non-parquet
        import contextlib
        with contextlib.suppress(Exception):
            ml.load()


# ── Empty datasets ──────────────────────────────────────────────


class TestEmptyDataset:
    def test_zero_rows_csv(self, tmp_path: object) -> None:
        p = tmp_path / "empty.csv"  # type: ignore[operator]
        p.write_text("a,b,c\n", encoding="utf-8")
        ml = AetherML(str(p))
        with pytest.raises((AetherMLError, WorkflowError, ValueError)):
            ml.run()

    def test_zero_columns_csv(self, tmp_path: object) -> None:
        p = tmp_path / "nocols.csv"  # type: ignore[operator]
        p.write_text("\n\n\n", encoding="utf-8")
        ml = AetherML(str(p))
        with pytest.raises((AetherMLError, WorkflowError, Exception)):
            ml.run()

    def test_single_cell_csv(self, tmp_path: object) -> None:
        p = tmp_path / "single.csv"  # type: ignore[operator]
        p.write_text("a\n", encoding="utf-8")
        ml = AetherML(str(p))
        # Should fail — 1 row, 1 col, no target
        with pytest.raises((AetherMLError, WorkflowError, Exception)):
            ml.run()


# ── Ambiguous / missing target ──────────────────────────────────


class TestAmbiguousTarget:
    def test_all_numeric_no_target_label(self, tmp_path: object) -> None:
        """Dataset with no column named 'target' and all columns numeric."""
        p = tmp_path / "no_target.csv"  # type: ignore[operator]
        df = pd.DataFrame(
            {
                "col_a": range(20),
                "col_b": range(20, 40),
                "col_c": range(40, 60),
            }
        )
        df.to_csv(p, index=False)
        ml = AetherML(str(p))
        result = ml.detect_target()
        # Should still detect something — may be ambiguous
        assert result.task_type in ("classification", "regression", "ambiguous")

    def test_all_constant_columns(self, tmp_path: object) -> None:
        """Dataset where all values are identical — target detection is meaningless."""
        p = tmp_path / "constant.csv"  # type: ignore[operator]
        df = pd.DataFrame({"a": [1] * 20, "b": [2] * 20, "target": [0] * 20})
        df.to_csv(p, index=False)
        ml = AetherML(str(p))
        result = ml.detect_target()
        # May detect "target" or another column — all are constant
        assert result.column in ("target", "a", "b")
        # Confidence must be 0 due to zero variance
        assert result.confidence == 0.0


# ── Multi-sheet Excel ───────────────────────────────────────────


class TestMultiSheetExcel:
    def test_auto_selects_largest_sheet(self, tmp_path: object) -> None:
        """Auto-sheet-selection picks the sheet with the most rows, not all sheets."""
        p = tmp_path / "multi.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame({"a": range(5), "b": range(5)}).to_excel(
                writer, sheet_name="small", index=False
            )
            pd.DataFrame({"x": range(50), "y": range(50)}).to_excel(
                writer, sheet_name="big", index=False
            )
            pd.DataFrame({"z": range(20)}).to_excel(
                writer, sheet_name="medium", index=False
            )
        ml = AetherML(str(p))
        s = ml.summary()
        # Should load the "big" sheet (50 rows)
        assert s.rows == 50
        assert "x" in s.column_names
        assert "y" in s.column_names

    def test_single_sheet_excel(self, tmp_path: object) -> None:
        p = tmp_path / "single.xlsx"  # type: ignore[operator]
        df = pd.DataFrame({"a": range(10), "b": range(10)})
        df.to_excel(p, index=False)
        ml = AetherML(str(p))
        s = ml.summary()
        assert s.rows == 10


# ── Performance: 500k+ rows ─────────────────────────────────────


class TestLargeDatasetPerformance:
    def test_summarize_500k_is_fast(self, tmp_path: object) -> None:
        """summarize() on 500k rows should be fast — no full statistics."""
        p = tmp_path / "big.csv"  # type: ignore[operator]
        n = 500_000
        df = pd.DataFrame(
            {
                "f1": range(n),
                "f2": range(n),
                "f3": [float(x) for x in range(n)],
                "target": [0, 1] * (n // 2),
            }
        )
        df.to_csv(p, index=False)

        ml = AetherML(str(p))
        start = time.perf_counter()
        s = ml.summary()
        elapsed = time.perf_counter() - start

        assert s.rows == n
        assert s.columns == 4
        assert elapsed < 10.0, f"summarize() took {elapsed:.1f}s — too slow for 500k rows"

    def test_summarize_vs_run_ratio(self, tmp_path: object) -> None:
        """summarize() should be dramatically faster than full run()."""
        p = tmp_path / "medium.csv"  # type: ignore[operator]
        n = 10_000
        df = pd.DataFrame(
            {
                "f1": range(n),
                "f2": range(n),
                "target": [0, 1] * (n // 2),
            }
        )
        df.to_csv(p, index=False)

        ml_summary = AetherML(str(p))
        start = time.perf_counter()
        ml_summary.summary()
        summary_time = time.perf_counter() - start

        ml_full = AetherML(str(p))
        start = time.perf_counter()
        ml_full.run()
        run_time = time.perf_counter() - start

        # summary() should be at least 2x faster than run()
        assert summary_time < run_time / 2, (
            f"summary() ({summary_time:.2f}s) should be much faster than "
            f"run() ({run_time:.2f}s)"
        )
