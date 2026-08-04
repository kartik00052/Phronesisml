# ARCHITECTURE_AUDIT.md — PhronesisML (v0.2.2)

> **Audit:** architecture · **Version:** `0.2.2` · **Date:** 2026-08-04
> **Scope:** `phronesisml/` source tree, workflow orchestration, engine abstraction, public API surface.
> **Method:** read-only static audit (subagent + targeted verification), cross-checked against `AI_QUALITY_GATE.md` (constitution) and `Architecture.md`.
> **Baseline:** `pytest` 274 passed, `ruff check` clean, `ruff format --check` clean (121 files), `mypy` 50 errors (documented stub-category baseline; 51 before the v0.3.0 REST-module removal).

---

## 1. Executive Summary

PhronesisML is an **offline-first, deterministic AutoML SDK** with a layered architecture:

```
interfaces (CLI / REST / simple API / OOP SDK)
        │
        ▼
   simple.py / sdk.py ──► workflow/graph.py (LangGraph orchestration)
        │                          │
        ▼                          ▼
   agents/compose.py  ◄──  agents/*  (11 agents, constructor injection)
        │                          │
        ▼                          ▼
   services ──► ml/* (automl, evaluation, explainability, reports, preflight)
        │                          │
        ▼                          ▼
   engines/* (pandas / polars / spark)   ◄── configs/settings.py
```

The architecture is **sound and genuinely inspectable**: a single composition root
(`agents/compose.py::compose_agents()`), a single workflow state object
(`workflow/state.py::WorkflowState`), LangGraph-routed stages driven by one canonical
stage-order constant (`_stages._FULL_PIPELINE_STAGES`), and a clean engine abstraction.

This audit found **no structural defects**. The issues that existed were *single-point*
discipline violations (composition-root bypass, duplicated constants, orphaned exports),
all of which are now fixed. See `CODEBASE_INTEGRITY_REPORT.md` and `DUPLICATION_REPORT.md`.

---

## 2. Layer Inventory

| Layer | Modules | Responsibility |
|-------|---------|----------------|
| Simple API | `simple.py`, `_result_builders.py`, `_stages.py`, `results.py` | sync + async convenience functions (`analyze`, `clean`, `train`, `evaluate`, …) returning typed result dataclasses |
| OOP SDK | `sdk.py` | `Phronesis` class: chained pipeline (`load → validate → … → train`), `run_pipeline` fallback |
| Workflow | `workflow/graph.py`, `workflow/state.py`, `workflow/nodes.py`, `workflow/router.py`, `workflow/sampling_node.py` | LangGraph graph construction, routing, state, pre-flight sampling |
| Agents | `agents/*` (11 agents) | one class per pipeline stage, composed in `agents/compose.py` |
| ML subsystems | `ml/automl`, `ml/evaluation`, `ml/explainability`, `ml/feature_engineering`, `ml/target_detection`, `ml/preflight`, `ml/reports`, `ml/clustering`, `ml/anomaly` | model candidate generation, bounded HPO, metrics, SHAP, feature engineering, target detection, reporting |
| Data | `data/` | IO loaders, ETL, validation, EDA |
| Engines | `engines/` | `BaseEngine` ABC + pandas/polars/spark backends; `engine_selector` (build) + `recommend` (pure heuristics) |
| Interfaces | `interfaces/cli` | Typer CLI |
| Services | `services/` | storage / artifact persistence |
| Config | `configs/settings.py` | pydantic `BaseModel` config dataclasses |
| Utils | `utils/` | dtype maps, resource estimation |

## 3. The Composition Root

`agents/compose.py::compose_agents()` is the **only** place concrete agent/engine classes
are instantiated. Verified:

- All 11 agents constructed via constructor injection (`engine`, `config`, `ETLConfig`, `feature_selection_config`).
- `sdk.py::_make_agents` and `__init__.py::compose_all_agents` delegate to it.
- **New:** `agent_overrides: dict[str, dict[str, Any]] | None` — a sanctioned, typed
  escape hatch for constructor kwargs (e.g. `{"model_selection": {"cv": 5}}`). This
  replaced the ad-hoc `simple.py` mutation of `ml._agents["model_selection"]`
  (see RCA `NEW-02`). Unknown agent names raise `ValueError`.

## 4. Workflow Orchestration

- `WorkflowState` (`workflow/state.py`) is a pydantic model with an explicit
  field-ownership map (`FIELD_OWNER`), so every state field is written by exactly one agent.
- `workflow/graph.py` builds the `StateGraph`, routes via `workflow/router.py`,
  and orders stages by `PIPELINE_ORDER`.
- **Single source of truth:** `_stages.py::_FULL_PIPELINE_STAGES` now defines the
  11-stage order exactly once; `graph.PIPELINE_ORDER`, `__init__._FULL_PIPELINE_STAGES`
  and all `_STAGES_*` are derived slices (see RCA `NEW-03`).

## 5. Engine Abstraction

- `engines/base_engine.py` is an ABC (`EngineType` enum + shared defaults), with
  pandas / polars / spark backends. `collect()/lazy()` first-class.
- `engine_selector.select_engine` routes by size:
  `< 2 MiB → pandas`, `<= config.data.max_memory_bytes (500 MiB default) → polars`, else spark.
- `recommend.recommend_engine` exposes the same policy as pure heuristics; it now
  imports `PANDAS_MAX_BYTES` / `DEFAULT_MAX_MEMORY_BYTES` from `configs.settings.py`
  so the two routing paths cannot drift (RCA `NEW-04`).

## 6. Public API Surface

Simple API (13 sync + async pairs): `analyze`, `clean`, `validate`, `detect_target`,
`detect_task`, `cluster`, `detect_anomalies`, `engineer`, `select_model`, `evaluate`,
`explain`, `report`, `train`. All exported from `phronesisml.__all__` and lazily loaded.
`evaluate` / `evaluate_async` were previously orphaned (see `PUBLIC_API_AUDIT.md`).

OOP: `Phronesis` (method-chained pipeline). Advanced: `run_pipeline`, config/result types.

## 7. Determinism & Offline Property

Randomness is seeded (`random_state=42` convention, `workflow/sampling_node.py`),
HPO is resource-bounded (`max_trials`, `max_time_seconds` hard ceilings), and all
reporting/artifacts are JSON/Markdown/HTML with no network dependency. Verified by
`tests/test_determinism.py` (full-pipeline byte-identical re-runs).

## 8. Findings Summary

| Finding | Severity | Status |
|---------|----------|--------|
| Composition-root bypass in `simple.py` (manual agent construction) | Medium | Fixed (`agent_overrides`) |
| Stage-order constant triplication | Medium | Fixed (single source in `_stages.py`) |
| Orphaned `evaluate_async` export | Medium | Fixed |
| Engine routing threshold drift (`recommend` 2GB vs `selector` 500MB) | Medium | Fixed |
| Duplicated byte-limit / threshold literals | Low | Fixed (named constants) |
| Doc drift (agent count, config docstring, CJK text) | Low | Fixed |

## 9. Recommendations (future)

1. Wire `DataConfig.max_file_size_bytes` into `WorkflowState` so the upload agent's
   fallback constant becomes config-driven (currently always the default).
2. Move `simple.py`'s `_build_config` into `configs/settings.py` so the simple API and
   OOP API share one config-construction path.
3. Consider splitting `ml/reports/io.py` (report dict builders vs Markdown rendering).
