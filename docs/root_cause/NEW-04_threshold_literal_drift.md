# Root Cause Analysis — threshold literal drift

> **File:** `docs/root_cause/NEW-04_threshold_literal_drift.md` · **Date:** 2026-08-04 · **ID:** NEW-04

## Issue Summary
Four policy thresholds existed as bare literals in one module while their canonical
named constant lived elsewhere (or nowhere), allowing silent drift. One drift was
already real: the pure engine-recommendation heuristic routed datasets up to **2 GB**
to Polars while the actual engine selector routed at **500 MB** — the same dataset
received contradictory recommendations depending on which code path was consulted.

## Root Cause
Named constants existed in the "origin" module but consumers re-typed the value
instead of importing it, so the compiler could not detect divergence. Byte-limit
defaults were also re-declared in config fields and agent fallbacks.

## Affected Components
- `phronesisml/engines/recommend.py` (`2_000_000_000`, `2 * 1024 * 1024`)
- `phronesisml/engines/engine_selector.py` (`2 * 1024 * 1024`)
- `phronesisml/ml/evaluation/metrics.py:159` (`0.6`)
- `phronesisml/ml/target_detection/analysis.py:131` (`20`)
- `phronesisml/agents/upload/agent.py:39` (`2 * 1024 * 1024 * 1024`)
- `phronesisml/configs/settings.py` (Field defaults)

## Affected APIs
- `recommend_engine` / `engine_comparison_report` (public heuristics)
- `PhronesisConfig` defaults (`max_memory_bytes`, `max_file_size_bytes`)

## Affected SDK Functions
- engine auto-selection path in `Phronesis`

## Affected CLI
- none

## Affected REST (removed in v0.3.0)
- Obsolete: the `/capabilities` (engine recommendation payload) was removed with the
  REST layer in v0.3.0.

## Fix Applied
- Canonical constants `PANDAS_MAX_BYTES`, `DEFAULT_MAX_MEMORY_BYTES`,
  `DEFAULT_MAX_FILE_SIZE_BYTES` added to `configs/settings.py` (exported in `__all__`).
- `recommend.py`, `engine_selector.py`, and `upload/agent.py` import them.
- `metrics.py` imports `AMBIGUITY_THRESHOLD` from `detector.py`.
- `analysis.py` imports `MAX_CLASSIFICATION_UNIQUE_VALUES` from `auto_selector.py`.
- `recommend.py` polars/spark boundary corrected from 2 GB to `DEFAULT_MAX_MEMORY_BYTES`
  (500 MiB), aligning the heuristics with the real selector.

## Regression Test Added
- `tests/test_resources_engines.py` (recommend_engine pandas/polars/spark) still passes,
  confirming boundary behaviour at 1 KB / 100 MB / 5 GB.
- Full suite 270 passed.

## Future Prevention
- Audit sibling threshold sites periodically (see `../../project_docs/DUPLICATION_REPORT.md` §4).
- New thresholds must be named constants in one canonical location and imported,
  never re-typed.
