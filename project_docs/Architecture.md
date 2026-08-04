# PhronesisML — Architecture

> **Version:** 0.2.2 · **Date:** 2026-08-04
> **Status:** Consolidated reference. Canonical deep-dives live in `../docs/architecture.md` (layer model), `../docs/design-decisions.md` (8 decisions with rejected alternatives), and `PROJECT_KNOWLEDGE_BASE.md` (file-by-file reference). This document is the single entry point and must match the tree.

## 1. Layering

```
SDK Layer        Phronesis (OOP), Simple API (12 fn + async), run_pipeline()
Workflow Layer   LangGraph StateGraph(WorkflowState) — nodes are agent closures; routers
Agent Layer      11 protocol agents — Upload, ETL, Validation, EDA, Target Detection,
                 Feature Engineering, Model Selection, Evaluation, Explainability,
                 Reporting, Storage
Service Layer    services/storage (artifact IO), services/data_resolution
Engine Layer     BaseEngine ABC — PandasEngine / PolarsEngine / SparkEngine
Data Layer       loaders, validators, transformers, profilers (data/), ML modules (ml/)
```

## 2. Non-negotiable invariants

- **SDK-first:** the CLI is a thin adapter over `simple` / `sdk`. No business logic lives in `interfaces/`.
- **Offline-first:** no mandatory cloud/LLM/GPU/network dependency. Optional integrations (MLflow, Spark) degrade gracefully.
- **Deterministic:** seeded RNG in sampling, HPO, explainability. Same input + config = same output.
- **LangGraph orchestration:** do not bypass the graph to call agents ad hoc.
- **Composition root:** agents are constructor-injected in exactly two places (`phronesisml/__init__.py` → `agents/compose.py` and `sdk.py`). No service locators, no import-time construction.
- **Engine abstraction:** all data ops go through `BaseEngine`. `collect()` always returns a pandas DataFrame. Engine-neutral code MUST defensively copy before in-place mutation (BUG-01 rule).
- **Agents are Protocols:** `BaseAgent.run(state) -> AgentResult(success, data, error, error_type, error_message, error_context)`. Agents MUST NOT raise for expected failures.
- **Field ownership:** every `WorkflowState` field is owned by exactly one stage (`workflow/state.py`).

## 3. Pipeline order

`upload → etl → validation → eda → target_detection → feature_engineering → model_selection → evaluation → explainability → reporting → storage`

Unsupervised tracks (clustering, anomaly) are routed conditionally; storage has no router; pre-flight sampling node is insertable before EDA/FE/target/model-selection/explainability.

## 4. Engine auto-selection

| Size | Engine |
|---|---|
| < 2 MB | pandas |
| 2–500 MB | polars |
| > 500 MB | spark |

Override via `EngineConfig.preferred` (`"pandas"` / `"polars"` / `"spark"`). Spark master defaults to `local[*]`.

## 5. Exception hierarchy

```
PhronesisError
├── ConfigurationError
├── DataError
│   ├── DataLoadError
│   ├── DataTransformError
│   └── DataValidationError
├── EngineError
│   └── EngineSelectionError
├── WorkflowError
└── AgentError
    └── AgentNotImplementedError
```

Fail-fast on `AgentError`; graceful partial-results on `AgentNotImplementedError`; optional integrations degrade with a warning, never a crash.

## 6. Key modules

| Concern | Module |
|---|---|
| OOP SDK | `phronesisml/sdk.py` (`Phronesis`) |
| Simple API | `phronesisml/simple.py` |
| Config | `phronesisml/configs/settings.py` (`PhronesisConfig` + sub-configs) |
| Exceptions | `phronesisml/exceptions.py` |
| Workflow | `phronesisml/workflow/{state,graph,router,nodes,sampling_node}.py` |
| Engines | `phronesisml/engines/{base_engine,pandas_engine,polars_engine,spark_engine,engine_selector}.py` |
| Data (new) | `phronesisml/data/{io,validation,etl,eda}.py`, `data/transformers/`, `data/loaders/`, `data/validators/`, `data/profilers/` |
| ML | `phronesisml/ml/{target_detection,feature_engineering,automl,evaluation,explainability,clustering,anomaly,reports,preflight}/` |
| Services | `phronesisml/services/{storage,data_resolution}.py` |
| Interfaces | `phronesisml/interfaces/{cli,api}/` |

## 7. Versioning

Single source: `phronesisml/__init__.py:__version__` = `"0.2.2"`. Python floor `>=3.11` (per `pyproject.toml`), CI validates on 3.13. MIT license.
