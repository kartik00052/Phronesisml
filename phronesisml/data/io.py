"""Data ingestion toolkit — public DataFrame loaders and dataset utilities.

These are engine-light, deterministic, offline convenience functions that
return plain Pandas DataFrames (or small dict/iterator helpers).  They
compose the existing loader machinery (``file_loader``) where practical
and avoid duplicating engine logic.

Design:
- Pure functions; no global state; no network calls.
- Format-specific loaders delegate to Pandas readers with a consistent
  ``DataLoadError`` wrapper.
- Directory / zip / multi-file loading iterates paths in sorted order so
  results are reproducible.
"""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from phronesisml.exceptions import DataLoadError

logger = logging.getLogger(__name__)


def _as_path(path: str | Path) -> Path:
    path = Path(path)
    if not path.exists():
        msg = f"Path does not exist: {path}"
        raise DataLoadError(msg)
    return path


def _wrap_load(path: Path, reader: Any) -> pd.DataFrame:
    try:
        result = reader()
        if not isinstance(result, pd.DataFrame):
            result = pd.DataFrame(result)
        logger.info("Loaded %d rows, %d columns from %s", *result.shape, path)
        return result
    except DataLoadError:
        raise
    except Exception as exc:
        msg = f"Failed to load data from {path}: {exc}"
        raise DataLoadError(msg) from exc


def load_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Load a CSV file into a DataFrame.

    Args:
        path: Path to the CSV file.
        **kwargs: Forwarded to ``pandas.read_csv`` (e.g. ``sep``, ``encoding``).

    Returns:
        A Pandas DataFrame.

    Raises:
        DataLoadError: If the file is missing or cannot be read.
    """
    path = _as_path(path)
    return _wrap_load(path, lambda: pd.read_csv(path, **kwargs))


def load_tsv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Load a TSV file (tab-separated) into a DataFrame.

    Args:
        path: Path to the TSV file.
        **kwargs: Forwarded to ``pandas.read_csv``.

    Returns:
        A Pandas DataFrame.

    Raises:
        DataLoadError: If the file is missing or cannot be read.
    """
    path = _as_path(path)
    kwargs.setdefault("sep", "\t")
    return _wrap_load(path, lambda: pd.read_csv(path, **kwargs))


def load_json(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Load a JSON file into a DataFrame.

    Args:
        path: Path to the JSON file.
        **kwargs: Forwarded to ``pandas.read_json``.

    Returns:
        A Pandas DataFrame.

    Raises:
        DataLoadError: If the file is missing or cannot be read.
    """
    path = _as_path(path)
    return _wrap_load(path, lambda: pd.read_json(path, **kwargs))


def load_jsonl(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Load a JSON Lines (.jsonl / .ndjson) file into a DataFrame.

    Args:
        path: Path to the JSON Lines file.
        **kwargs: Forwarded to ``pandas.read_json``.

    Returns:
        A Pandas DataFrame.

    Raises:
        DataLoadError: If the file is missing or cannot be read.
    """
    path = _as_path(path)
    kwargs.setdefault("lines", True)
    return _wrap_load(path, lambda: pd.read_json(path, **kwargs))


def load_parquet(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Load a Parquet file into a DataFrame.

    Args:
        path: Path to the Parquet file.
        **kwargs: Forwarded to ``pandas.read_parquet``.

    Returns:
        A Pandas DataFrame.

    Raises:
        DataLoadError: If the file is missing or cannot be read.
    """
    path = _as_path(path)
    return _wrap_load(path, lambda: pd.read_parquet(path, **kwargs))


def load_excel(
    path: str | Path,
    sheet_name: str | int | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Load an Excel file into a DataFrame.

    When *sheet_name* is ``None``, the best (most populated) sheet is
    auto-selected, matching the pipeline loader behaviour.

    Args:
        path: Path to the Excel file (``.xlsx`` or ``.xls``).
        sheet_name: Sheet name or 0-based index.  If ``None``, auto-select.
        **kwargs: Forwarded to ``pandas.read_excel``.

    Returns:
        A Pandas DataFrame.

    Raises:
        DataLoadError: If the file is missing or cannot be read.
    """
    from phronesisml.data.loaders.file_loader import select_best_sheet

    path = _as_path(path)
    if sheet_name is None:
        sheet_name = select_best_sheet(path)
    return _wrap_load(path, lambda: pd.read_excel(path, sheet_name=sheet_name, **kwargs))


def load_directory(
    directory: str | Path,
    pattern: str = "*.csv",
    recursive: bool = True,
    **kwargs: Any,
) -> dict[str, pd.DataFrame]:
    """Load every matching file in a directory into a dict of DataFrames.

    Results are keyed by absolute file path and iterated in sorted order
    for deterministic output.

    Args:
        directory: Directory to scan.
        pattern: Glob pattern for file selection (default ``*.csv``).
        recursive: Whether to recurse into subdirectories.
        **kwargs: Forwarded to ``load_csv`` for each file.

    Returns:
        A dict mapping file path → DataFrame.

    Raises:
        DataLoadError: If the directory does not exist or no files match.
    """
    directory = Path(directory)
    if not directory.is_dir():
        msg = f"Directory does not exist: {directory}"
        raise DataLoadError(msg)

    globber = directory.rglob(pattern) if recursive else directory.glob(pattern)
    files = sorted(p for p in globber if p.is_file())
    if not files:
        msg = f"No files matching {pattern!r} in {directory}."
        raise DataLoadError(msg)

    return {str(p): load_csv(p, **kwargs) for p in files}


def load_multiple_files(
    paths: list[str | Path],
    combine: str = "concat",
    **kwargs: Any,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Load multiple files at once.

    Args:
        paths: List of file paths to load.
        combine: ``"concat"`` (default) returns one concatenated DataFrame;
            ``"dict"`` returns a dict keyed by path.
        **kwargs: Forwarded to ``load_csv`` for each file.

    Returns:
        A concatenated DataFrame (``combine="concat"``) or a dict of
        DataFrames keyed by path (``combine="dict"``).

    Raises:
        DataLoadError: If *combine* is unknown or a path fails to load.
    """
    if not paths:
        msg = "No file paths provided."
        raise DataLoadError(msg)

    loaded: dict[str, pd.DataFrame] = {}
    for p in sorted(str(x) for x in paths):
        loaded[p] = load_csv(p, **kwargs)

    if combine == "dict":
        return loaded
    if combine == "concat":
        frames = list(loaded.values())
        if not frames:
            msg = "No dataframes to concatenate."
            raise DataLoadError(msg)
        return pd.concat(frames, ignore_index=True)

    msg = f"Unknown combine mode: {combine!r}. Use 'concat' or 'dict'."
    raise DataLoadError(msg)


def load_zip(
    zip_path: str | Path,
    member: str | None = None,
    **kwargs: Any,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Load data files from inside a ZIP archive.

    Args:
        zip_path: Path to the ZIP archive.
        member: Specific member filename to load.  When ``None``, all
            supported data members are loaded.
        **kwargs: Forwarded to ``load_csv`` for each member.

    Returns:
        A single DataFrame when *member* is given; otherwise a dict
        mapping member filename → DataFrame.

    Raises:
        DataLoadError: If the archive cannot be read or no data members
            are found.
    """
    zip_path = _as_path(zip_path)
    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as exc:
        msg = f"Failed to open zip archive {zip_path}: {exc}"
        raise DataLoadError(msg) from exc

    with archive:
        _DATA_SUFFIXES = (".csv", ".tsv", ".json", ".jsonl", ".ndjson")
        members = sorted(n for n in archive.namelist() if n.lower().endswith(_DATA_SUFFIXES))

        def _read_member(name: str) -> pd.DataFrame:
            with archive.open(name) as fh:
                if name.lower().endswith((".jsonl", ".ndjson")):
                    return pd.read_json(fh, lines=True, **kwargs)
                if name.lower().endswith(".json"):
                    return pd.read_json(fh, **kwargs)
                return pd.read_csv(fh, **kwargs)

        def _wrap_member(name: str) -> pd.DataFrame:
            return _wrap_load(zip_path, lambda: _read_member(name))

        if member is not None:
            if member not in members:
                msg = f"Member {member!r} not found or not a supported data file in {zip_path}."
                raise DataLoadError(msg)
            return _wrap_member(member)

        if not members:
            msg = f"No supported data files found in zip archive {zip_path}."
            raise DataLoadError(msg)

        return {name: _wrap_member(name) for name in members}


def merge_datasets(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str | list[str] | None = None,
    how: str = "inner",
    **kwargs: Any,
) -> pd.DataFrame:
    """Merge two DataFrames on one or more key columns.

    Args:
        left: Left DataFrame.
        right: Right DataFrame.
        on: Column(s) to join on.  If ``None``, columns present in both.
        how: Join type (``"inner"``, ``"left"``, ``"right"``, ``"outer"``,
            or ``"cross"``).
        **kwargs: Forwarded to ``pandas.merge``.

    Returns:
        The merged DataFrame.
    """
    return pd.merge(left, right, on=on, how=how, **kwargs)


def concatenate_datasets(
    frames: list[pd.DataFrame] | dict[str, pd.DataFrame],
    axis: int = 0,
    **kwargs: Any,
) -> pd.DataFrame:
    """Concatenate multiple DataFrames along an axis.

    Args:
        frames: List of DataFrames (or dict of them, in sorted key order).
        axis: 0 to stack rows, 1 to join columns.
        **kwargs: Forwarded to ``pandas.concat``.

    Returns:
        The concatenated DataFrame.
    """
    if isinstance(frames, dict):
        frames = [frames[k] for k in sorted(frames)]
    if not frames:
        msg = "No dataframes to concatenate."
        raise DataLoadError(msg)
    return pd.concat(frames, axis=axis, **kwargs)


def infer_file_type(path: str | Path) -> dict[str, str]:
    """Infer the file type and family from a path.

    Args:
        path: File path or name.

    Returns:
        A dict with ``format`` (csv/parquet/json/feather/excel), ``family``
        (tabular/structured), and ``extension``.

    Raises:
        DataLoadError: If the format cannot be inferred.
    """
    from phronesisml.data.loaders.file_loader import detect_format

    path = Path(path)
    fmt = detect_format(path)
    family = "tabular" if fmt in ("csv", "parquet", "feather") else "structured"
    return {"format": fmt, "family": family, "extension": path.suffix.lower()}


def detect_encoding(path: str | Path, sample_bytes: int = 100_000) -> str:
    """Detect the text encoding of a file.

    Deterministic and offline: UTF-8 (with/without BOM) is detected first;
    if decoding fails, the ``chardet`` package is used when available, with
    a ``latin-1`` fallback (which never fails to decode).

    Args:
        path: Path to the text file.
        sample_bytes: Number of leading bytes to inspect.

    Returns:
        The detected encoding name (e.g. ``"utf-8"``, ``"cp1252"``).

    Raises:
        DataLoadError: If the file cannot be read.
    """
    path = _as_path(path)
    try:
        raw = path.open("rb").read(sample_bytes)
    except OSError as exc:
        msg = f"Failed to read {path}: {exc}"
        raise DataLoadError(msg) from exc

    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    try:
        import chardet  # type: ignore[import-not-found]

        detected = chardet.detect(raw)
        if detected and detected.get("encoding"):
            return str(detected["encoding"])
    except ImportError:
        logger.info("chardet not installed; falling back to latin-1.")

    return "latin-1"


def preview_dataset(df: pd.DataFrame, n: int = 5) -> dict[str, Any]:
    """Build a compact preview of a DataFrame.

    Args:
        df: Input DataFrame.
        n: Number of rows to include in the preview.

    Returns:
        A dict with ``shape``, ``columns``, ``dtypes``, and ``preview``
        (first *n* rows as records).
    """
    return {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "preview": df.head(n).to_dict("records"),
    }


def stream_large_dataset(
    path: str | Path,
    chunksize: int = 10_000,
    **kwargs: Any,
) -> Iterator[pd.DataFrame]:
    """Stream a large file in chunks (generator).

    Uses ``pandas.read_csv(..., chunksize=...)``.  The returned iterator
    yields one DataFrame per chunk, so memory stays bounded.

    Args:
        path: Path to the file.
        chunksize: Rows per chunk.
        **kwargs: Forwarded to ``pandas.read_csv``.

    Yields:
        Chunks of the dataset as DataFrames.

    Raises:
        DataLoadError: If the file is missing.
    """
    path = _as_path(path)
    reader = pd.read_csv(path, chunksize=chunksize, **kwargs)
    yield from reader


def estimate_dataset_size(path: str | Path) -> dict[str, Any]:
    """Estimate the on-disk and in-memory size of a dataset.

    Args:
        path: Path to the data file.

    Returns:
        A dict with ``file_size_bytes``, ``file_size_mb``, ``estimated_rows``
        (CSV/JSONL best-effort line estimate), and ``extension``.
    """
    path = _as_path(path)
    file_bytes = path.stat().st_size
    ext = path.suffix.lower()

    estimated_rows: int | None = None
    if ext in (".csv", ".tsv", ".jsonl", ".ndjson"):
        # Deterministic line-count estimate over the whole file.
        with path.open("rb") as fh:
            estimated_rows = sum(1 for _ in fh)

    return {
        "file_size_bytes": file_bytes,
        "file_size_mb": round(file_bytes / (1024 * 1024), 3),
        "estimated_rows": estimated_rows,
        "extension": ext,
    }


def dataset_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Summarise a DataFrame: shape, dtypes, missingness, duplicates.

    Args:
        df: Input DataFrame.

    Returns:
        A dict with ``shape``, ``columns``, ``dtypes``, ``missing_counts``,
        ``missing_fraction``, ``duplicate_rows``, ``numeric_columns``,
        ``categorical_columns``, and ``memory_bytes``.
    """
    missing_counts = df.isnull().sum().to_dict()
    missing_counts = {col: int(v) for col, v in missing_counts.items()}

    return {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_counts": missing_counts,
        "missing_fraction": round(float(df.isnull().mean().mean()), 6),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_columns": [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])],
        "categorical_columns": [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])],
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
    }
