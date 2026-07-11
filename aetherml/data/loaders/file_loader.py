"""Data loaders — read data from various sources via the active engine.

Loaders are thin wrappers around ``BaseEngine.read()`` that add:
- Format detection from file extensions
- Uniform return type (Pandas DataFrame via ``engine.collect()``)
- Error wrapping with ``DataLoadError``
- Smart Excel handling: auto-selects the best non-empty sheet when
  multiple sheets exist.

Loaders do NOT own data — they are pure functions that return DataFrames.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from aetherml.engines.base_engine import BaseEngine
from aetherml.exceptions import DataLoadError

logger = logging.getLogger(__name__)

# Supported formats and their file extensions
_FORMAT_EXTENSIONS: dict[str, list[str]] = {
    "csv": [".csv", ".tsv"],
    "parquet": [".parquet", ".pq"],
    "json": [".json", ".jsonl", ".ndjson"],
    "feather": [".feather", ".arrow"],
    "excel": [".xlsx", ".xls"],
}

_EXCEL_EXTENSIONS = {".xlsx", ".xls"}


def _check_excel_deps(path: Path) -> None:
    """Raise a clear error if the required Excel library is missing."""
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        try:
            import openpyxl  # noqa: F401
        except ImportError as exc:
            msg = (
                "Excel (.xlsx) files require the 'openpyxl' package. "
                "Install it with: pip install openpyxl"
            )
            raise DataLoadError(msg) from exc
    elif suffix == ".xls":
        try:
            import xlrd  # noqa: F401
        except ImportError as exc:
            msg = (
                "Legacy Excel (.xls) files require the 'xlrd' package. "
                "Install it with: pip install xlrd"
            )
            raise DataLoadError(msg) from exc


def list_excel_sheets(path: str | Path) -> list[dict[str, Any]]:
    """List all sheets in an Excel file with their row counts.

    Args:
        path: Path to the Excel file.

    Returns:
        A list of dicts with keys ``name``, ``index``, ``rows``, ``cols``.

    Raises:
        DataLoadError: If the file cannot be read.
    """
    path = Path(path)
    _check_excel_deps(path)
    try:
        xls = pd.ExcelFile(path)
    except Exception as exc:
        msg = f"Failed to read Excel file: {path}: {exc}"
        raise DataLoadError(msg) from exc

    sheets: list[dict[str, Any]] = []
    for idx, name in enumerate(xls.sheet_names):
        try:
            df_full = pd.read_excel(xls, sheet_name=name)
            sheets.append(
                {
                    "name": name,
                    "index": idx,
                    "rows": len(df_full),
                    "cols": len(df_full.columns),
                }
            )
        except Exception:
            sheets.append(
                {
                    "name": name,
                    "index": idx,
                    "rows": 0,
                    "cols": 0,
                }
            )
    return sheets


def select_best_sheet(path: str | Path) -> str | int:
    """Pick the best sheet from a multi-sheet Excel file.

    Selection criteria (in order):
    1. Most non-empty rows (excluding all-NaN rows).
    2. First sheet as tiebreaker.

    Args:
        path: Path to the Excel file.

    Returns:
        Sheet name or index suitable for ``pd.read_excel(sheet_name=...)``.

    Raises:
        DataLoadError: If no usable sheet is found.
    """
    sheets = list_excel_sheets(path)
    if not sheets:
        msg = f"No sheets found in Excel file: {path}"
        raise DataLoadError(msg)

    # Score each sheet by non-empty row count
    scored: list[tuple[int, int, str | int]] = []
    for s in sheets:
        # Read and count non-all-NaN rows
        try:
            df = pd.read_excel(path, sheet_name=s["name"])
            non_empty = int(df.dropna(how="all").shape[0])
        except Exception:
            non_empty = 0
        scored.append((non_empty, -s["index"], s["name"]))

    # Sort by non-empty rows desc, then by index asc (tiebreaker)
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    best_name = scored[0][2]
    best_rows = scored[0][0]
    logger.info(
        "Excel sheet selection: chose '%s' (%d non-empty rows) from %d sheets",
        best_name,
        best_rows,
        len(sheets),
    )
    if best_rows == 0:
        msg = (
            f"All sheets in Excel file '{path}' are empty. "
            f"Sheets found: {[s['name'] for s in sheets]}"
        )
        raise DataLoadError(msg)
    return best_name


def detect_format(path: str | Path) -> str:
    """Detect file format from the file extension.

    Returns:
        Format name string (e.g. ``"csv"``, ``"parquet"``).

    Raises:
        DataLoadError: If the format cannot be determined.

    """
    suffix = Path(path).suffix.lower()
    for fmt, extensions in _FORMAT_EXTENSIONS.items():
        if suffix in extensions:
            return fmt
    msg = f"Cannot detect format from extension '{suffix}' for path: {path}"
    raise DataLoadError(msg)


def load_file(
    path: str | Path,
    engine: BaseEngine,
    format: str | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Load a file into a Pandas DataFrame via the given engine.

    Args:
        path: Path to the data file.
        engine: The active computation engine.
        format: Explicit format override (``"csv"``, ``"parquet"``, etc.).
            If ``None``, the format is auto-detected from the file extension.
        **kwargs: Additional arguments forwarded to the engine's reader
            (e.g. ``sep=";"``, ``header=False``, ``sheet_name="Sheet1"``).

    Returns:
        A Pandas DataFrame with the loaded data.

    Raises:
        DataLoadError: If loading fails for any reason.

    """
    path = Path(path)
    if not path.exists():
        msg = f"Data file does not exist: {path}"
        raise DataLoadError(msg)

    if format is None:
        format = detect_format(path)

    logger.info("Loading %s file from %s", format, path)

    # ── Excel: smart sheet selection ──────────────────────────────────
    if path.suffix.lower() in _EXCEL_EXTENSIONS:
        _check_excel_deps(path)
        if "sheet_name" not in kwargs:
            kwargs["sheet_name"] = select_best_sheet(path)

    try:
        df = engine.read(path, **kwargs)
        # Normalise to Pandas via collect()
        result = engine.collect(df)
        logger.info("Loaded %d rows, %d columns", result.shape[0], result.shape[1])
        return result
    except DataLoadError:
        raise
    except Exception as exc:
        msg = f"Failed to load data from {path}: {exc}"
        raise DataLoadError(msg) from exc


def infer_format(path: str | Path) -> str:
    """Public alias for ``detect_format``."""
    return detect_format(path)
