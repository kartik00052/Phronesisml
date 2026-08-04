# DUPLICATION_REPORT.md — PhronesisML (v0.2.2)

> **Audit:** code duplication · **Version:** `0.2.2` · **Date:** 2026-08-04
> **Method:** read-only static scan for repeated literals/constants, reimplemented
> helpers, and copy-paste blocks, cross-referenced with `AI_QUALITY_GATE.md` §2
> (single-source-of-truth rule).
> **Baseline:** `pytest` 274 passed.

---

## 1. Executive Summary

No large copy-paste blocks exist; the codebase is clean on that axis. The duplication
found was **micro-duplication of policy constants and thresholds** that could silently
drift (and in one case already had — `recommend.py` used a 2 GB polars/spark boundary
while `engine_selector.py` routed at 500 MB). All instances found were consolidated to
named single-source constants. One helper duplication (`candidate_to_dict`) was
verified as already resolved.

## 2. Findings

### DUP-01 — Engine routing thresholds (FIXED, RCA NEW-04)

- `engines/engine_selector.py:31` and `engines/recommend.py:18` both hard-coded `2 * 1024 * 1024`.
- `recommend.py:84` hard-coded `2_000_000_000` for the polars/spark boundary while
  `configs.settings.DataConfig.max_memory_bytes` defaults to `500 * 1024 * 1024`.
  **Behavioural inconsistency:** a 1 GB dataset was "polars" per the pure heuristics but
  "spark" per the real selector.
- **Fix:** canonical constants `PANDAS_MAX_BYTES`, `DEFAULT_MAX_MEMORY_BYTES`,
  `DEFAULT_MAX_FILE_SIZE_BYTES` defined once in `configs/settings.py`; both routing
  modules import them.

### DUP-02 — Ambiguity threshold (FIXED)

- `ml/target_detection/detector.py:62` `AMBIGUITY_THRESHOLD = 0.6` vs
  `ml/evaluation/metrics.py:159` literal `0.6`.
- **Fix:** `metrics.py` imports `AMBIGUITY_THRESHOLD`.

### DUP-03 — Classification unique-value cutoff (FIXED)

- `ml/automl/auto_selector.py:35` `MAX_CLASSIFICATION_UNIQUE_VALUES = 20` vs
  `ml/target_detection/analysis.py:131` literal `20`.
- **Fix:** `analysis.py` imports the constant (already consumed by `detector.py`).

### DUP-04 — Upload size limit (FIXED)

- `configs/settings.py` `max_file_size_bytes` default `2 * 1024 * 1024 * 1024` vs
  `agents/upload/agent.py:39` `_DEFAULT_MAX_FILE_SIZE_BYTES` (same value).
- **Fix:** upload agent imports `DEFAULT_MAX_FILE_SIZE_BYTES`.

### DUP-05 — Stage-order constants triplicated (FIXED, RCA NEW-03)

- `_stages.py` (12 `_STAGES_*` lists), `__init__.py` `_FULL_PIPELINE_STAGES`,
  `workflow/graph.py` `PIPELINE_ORDER` — three independent copies of the canonical
  11-stage order.
- **Fix:** `_stages.py` defines `_FULL_PIPELINE_STAGES` once; every other constant is
  a derived slice/alias (`_STAGES_SELECT_MODEL`/`_STAGES_EVALUATE` and
  `_STAGES_CLUSTER`/`_STAGES_ANOMALY` are now shared list objects).

### DUP-06 — candidate serialization (VERIFIED RESOLVED)

- Audit flagged a duplicate `candidate_to_dict`-style block in `sdk.py`.
  Verified today: `candidate_to_dict` exists only in `ml/automl/auto_selector.py:347`
  and is imported by `agents/model_selection/agent.py`; no duplicate remains in `sdk.py`.

## 3. Not-eligible duplication (deliberate, documented)

- `_STAGES_CLUSTER == _STAGES_ANOMALY` — same stage set by design (both stop at
  reporting, skip explainability).
- `_STAGES_SELECT_MODEL == _STAGES_EVALUATE` — `evaluate` is an alias of select+eval.

## 4. Sibling sites to watch (future)

- `simple.py::_build_config` duplicates the field-mapping between simple-API kwargs
  and `PhronesisConfig`; consider hoisting into `configs/settings.py` (see
  ARCHITECTURE_AUDIT.md §9).
- `ml/preflight/estimator.py` and `ml/reports/io.py` both compute row/column counts —
  OK today (different layers), but guard against new consumers re-deriving them ad hoc.
