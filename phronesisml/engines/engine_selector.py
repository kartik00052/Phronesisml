"""Engine selector — chooses the best computation backend for the data.

Selection criteria (in order):
1. If the user explicitly forces an engine via ``EngineConfig.preferred``,
   use that engine regardless of data size.
2. Estimate the dataset's memory footprint (file size as a proxy when
   the DataFrame is not yet loaded; ``memory_usage()`` when it is).
3. Route based on the estimate:
   - ``< 2 MB``   → Pandas  (fastest startup, simplest API)
   - ``2 MB – max_memory_bytes``  → Polars  (default, best single-machine perf)
   - ``> max_memory_bytes``  → Spark  (distributed processing)

The thresholds are configurable via ``DataConfig.max_memory_bytes``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from phronesisml.configs.settings import PhronesisConfig
from phronesisml.engines.base_engine import BaseEngine, EngineType
from phronesisml.engines.pandas_engine import PandasEngine
from phronesisml.engines.polars_engine import PolarsEngine
from phronesisml.exceptions import EngineSelectionError

logger = logging.getLogger(__name__)

# Thresholds in bytes
_PANDAS_MAX = 2 * 1024 * 1024  # 2 MB


_DATA_EXTENSIONS = frozenset(
    {
        ".csv",
        ".parquet",
        ".json",
        ".jsonl",
        ".tsv",
        ".xlsx",
        ".xls",
        ".avro",
        ".orc",
    }
)


def _estimate_file_size(path: str | Path) -> int:
    """Return file size in bytes, or 0 if the path is not a regular file."""
    p = Path(path)
    if p.is_file():
        return p.stat().st_size
    if p.is_dir():
        total = 0
        for f in p.rglob("*"):
            if f.is_file() and f.suffix.lower() in _DATA_EXTENSIONS:
                total += f.stat().st_size
        return total
    return 0


def select_engine(
    config: PhronesisConfig | None = None,
    data_path: str | Path | None = None,
    df: Any = None,
) -> BaseEngine:
    """Select and return the most appropriate engine.

    Args:
        config: SDK configuration.  Uses defaults if ``None``.
        data_path: Path to the data file/directory.  Used for size
            estimation when *df* is not provided.
        df: An already-loaded DataFrame.  If provided, its in-memory
            size is used for selection instead of file size.

    Returns:
        An initialised ``BaseEngine`` instance.

    """
    if config is None:
        config = PhronesisConfig()

    # 1. User-forced engine
    preferred = config.engine.preferred
    if preferred is not None:
        return _build_engine(EngineType(preferred), config)

    # 2. Estimate memory footprint
    if df is not None:
        # Use the Pandas engine to measure memory (universal fallback)
        pandas_eng = PandasEngine()
        try:
            memory_bytes = pandas_eng.memory_usage(df)
        except Exception as exc:
            logger.warning("Memory usage measurement failed, defaulting to 0: %s", exc)
            memory_bytes = 0
    elif data_path is not None:
        memory_bytes = _estimate_file_size(data_path)
    else:
        memory_bytes = 0

    # 3. Route by size
    if memory_bytes < _PANDAS_MAX:
        engine_type = EngineType.PANDAS
    elif memory_bytes <= config.data.max_memory_bytes:
        engine_type = EngineType.POLARS
    else:
        engine_type = EngineType.SPARK

    return _build_engine(engine_type, config)


def _build_engine(engine_type: EngineType, config: PhronesisConfig) -> BaseEngine:
    """Instantiate an engine by type."""
    if engine_type == EngineType.PANDAS:
        return PandasEngine()
    if engine_type == EngineType.POLARS:
        return PolarsEngine()
    if engine_type == EngineType.SPARK:
        from phronesisml.engines.spark_engine import SparkEngine

        return SparkEngine(master=config.engine.spark_master)
    msg = f"Unknown engine type: {engine_type}"
    raise EngineSelectionError(msg)
