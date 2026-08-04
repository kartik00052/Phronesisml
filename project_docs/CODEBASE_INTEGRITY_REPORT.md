# CODEBASE_INTEGRITY_REPORT.md — PhronesisML (v0.2.2)

> **Audit:** codebase integrity (contracts, exports, composition discipline)
> **Version:** `0.2.2` · **Date:** 2026-08-04
> **Baseline:** `pytest` 274 passed, `ruff check` clean, `ruff format --check` clean,
> `mypy` 50 errors (documented stub-category baseline; 51 before the v0.3.0 REST-module removal).

---

## 1. Summary

The integrity audit verified the **single-source-of-truth rule** (AI_QUALITY_GATE §2)
across four dimensions: (a) composition discipline, (b) export/import symmetry,
(c) data-contract alignment, (d) constant/literal consolidation. Three classes of
violation were found and fixed; no failing code was commented out, no tests disabled.

## 2. Composition Discipline

| Check | Result | Detail |
|-------|--------|--------|
| One composition root | ✅ Fixed | `simple.py` no longer instantiates agents directly. `Phronesis.__init__` accepts `agent_overrides` and all agent construction flows through `compose_agents()` (RCA `NEW-02`) |
| No `ml._agents[…] = …` mutation | ✅ Fixed | Both `select_model_async` and `train_async` rewritten (verified by smoke run with `cv=3`) |

## 3. Export / Import Symmetry

| Check | Result | Detail |
|-------|--------|--------|
| Every simple function exported | ✅ Fixed | `evaluate`/`evaluate_async` added to `__all__` + `_LAZY_IMPORTS` (RCA `NEW-01`) |
| Stage constants single source | ✅ Fixed | `_FULL_PIPELINE_STAGES` defined once in `_stages.py`; `graph.PIPELINE_ORDER`, `__init__._FULL_PIPELINE_STAGES`, and all `_STAGES_*` derived from it (RCA `NEW-03`) |
| `_STAGES_EVALUATE` dead constant | ✅ Fixed | Now an alias of `_STAGES_SELECT_MODEL` (identical semantics) and re-exported for back-compat |

## 4. Data-Contract Alignment

| Check | Result | Detail |
|-------|--------|--------|
| Explainability contract | ✅ Fixed (prior session) | `summary.py` validates the real service shape; legacy keys tolerated |
| Report IO keys | ✅ Fixed (prior session) | `io.py` reads real `WorkflowState`/`best_pipeline`/`candidate_models` keys |
| HTML builder | ✅ Fixed (prior session) | `</2>` → `</h2>`; dead `_build_clustering_section`/`_build_anomaly_section` removed |
| State field vocabulary | ✅ Fixed | Preflight report keys `n_rows`/`n_cols` → `row_count`/`column_count` (RCA `NEW-08`) |

## 5. Constant / Literal Consolidation (RCA `NEW-04`)

| Literal | Old sites | Fix |
|---------|-----------|-----|
| Ambiguity threshold `0.6` | `ml/evaluation/metrics.py:159` (literal) vs `ml/target_detection/detector.py:62` `AMBIGUITY_THRESHOLD` | `metrics.py` imports `AMBIGUITY_THRESHOLD` |
| Classification unique-value cutoff `20` | `ml/target_detection/analysis.py:131` (literal) vs `ml/automl/auto_selector.py:35` `MAX_CLASSIFICATION_UNIQUE_VALUES` | `analysis.py` imports the constant |
| Pandas/polars boundary `2 MiB` | `engines/recommend.py:18` + `engines/engine_selector.py:31` (duplicated literals) | Both import `configs.settings.PANDAS_MAX_BYTES` |
| Polars/spark boundary `2_000_000_000` vs 500 MiB | `engines/recommend.py:84` (drifted from `config.data.max_memory_bytes` default) | `recommend.py` uses `DEFAULT_MAX_MEMORY_BYTES` (500 MiB) — routing paths now agree |
| Upload size limit `2 GiB` | `configs/settings.py:54` + `agents/upload/agent.py:39` (duplicated) | Both reference `DEFAULT_MAX_FILE_SIZE_BYTES` |

## 6. Doc Drift Fixed

- `agents/base.py` `_StubAgent` docstring: "15 agent directories" → "11 agent directories".
- `configs/settings.py` module docstring: claimed Pydantic `BaseSettings`; now describes the actual `BaseModel` fields.
- `engines/base_engine.py` module docstring: CJK fragment (`强制`) replaced with English ("we want to enforce subclassing").
- `engines/recommend.py` docstring comment claiming `engine_selector` is the source of truth removed (now `configs.settings` is).

## 7. Type-Check Integrity

`mypy phronesisml` = **50 errors in 26 files**, all in the documented stub-category
(missing pandas/sklearn/psutil/openpyxl/xlrd/mlflow/pyspark stubs). Two genuine type
errors introduced during the prior report-IO rewrite (`io.py:93` version-None
assignment, `io.py:212` metrics-table arg-type) were fixed in this pass and are no
longer present.

## 8. Remaining Integrity Work

- Upload agent always uses the default size limit (`state.max_file_size_bytes` is
  never populated) — wiring the config value into `WorkflowState` is recommended.
- `AI_QUALITY_GATE.md` still cites the old mypy count (34); will be updated in the docs-sync phase.
