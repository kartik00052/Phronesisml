# PUBLIC_API_AUDIT.md — PhronesisML (v0.2.2)

> **Audit:** public API surface · **Version:** `0.2.2` · **Date:** 2026-08-04
> **Method:** read-only audit of `phronesisml/__init__.py` (`__all__`, `_LAZY_IMPORTS`),
> `simple.py`, `sdk.py`, `results.py`, CLI `interfaces/cli/app.py`.
> **Baseline:** 270 tests passed.

---

## 1. Verified Public Surface

### 1.1 Simple API — exported pairs

| Sync | Async | Returns | Stage set |
|------|-------|---------|-----------|
| `analyze` | `analyze_async` | `DatasetProfile` | upload…eda |
| `clean` | `clean_async` | `CleanResult` | upload…etl |
| `validate` | `validate_async` | `ValidationResult` | upload…validation |
| `detect_target` | `detect_target_async` | `TargetResult` | upload…target_detection |
| `detect_task` | `detect_task_async` | `TaskDetectionResult` | upload…target_detection |
| `cluster` | `cluster_async` | `ClusteringResult` | upload…reporting (no explainability) |
| `detect_anomalies` | `detect_anomalies_async` | `AnomalyResult` | upload…reporting (no explainability) |
| `engineer` | `engineer_async` | `FeatureResult` | upload…feature_engineering |
| `select_model` | `select_model_async` | `ModelResult` | upload…evaluation |
| `evaluate` | `evaluate_async` | `ModelResult` | upload…evaluation |
| `explain` | `explain_async` | `ExplainResult` | upload…explainability |
| `report` | `report_async` | `ExplainResult` (report dict) | upload…reporting |
| `train` | `train_async` | `TrainResult` | full 11 stages |

All 13 sync functions + their `_async` twins are present in `__all__` and
`_LAZY_IMPORTS`, lazily loaded via `__getattr__` (verified: `import phronesisml`
does not eagerly import `langgraph`).

### 1.2 OOP API

- `Phronesis(data_path, config=None, agent_overrides=None)` — chained stages
  `load / validate / analyze / engineer / select_model / evaluate / explain / report / train`
  returning the typed report dataclasses (`DatasetSummary`, `ValidationReport`,
  `EDAReport`, `FeatureReport`, `ModelInfo`, `ExplanationReport`, …).

### 1.3 Advanced API

- `run_pipeline(data_path, engine_preference, null_strategy, stages, config, sampling_config)`
- Types: `PhronesisConfig`, `SamplingConfig`, `PhronesisError`, `ConfigurationError`,
  `WorkflowError`, `WorkflowState`, result dataclasses.

### 1.4 CLI (`phronesisml[cli]`)

`run`, `info`, `version`, help — verified wired to the same pipeline.

### 1.5 REST (`phronesisml[api]`)

`/health`, `/capabilities`, `/version`, `/analyze`, `/train` (async job), plus docs.

---

## 2. Findings Fixed in This Audit

| ID | Finding | Fix |
|----|---------|-----|
| NEW-01 | `evaluate_async` was implemented (`simple.py`) and used by REST (`routes.py:396`) but **not exported** from `__init__.py`; no sync `evaluate` existed | Added sync `evaluate` + exported both `evaluate` / `evaluate_async` in `__all__` + `_LAZY_IMPORTS`. `evaluate_async` now delegates to `select_model_async` (identical stage set, verified) |
| NEW-02 | `select_model_async(cv=…)` and `train_async(cv/model_type=…)` bypassed the composition root by constructing `ModelSelectionAgent` directly and mutating `ml._agents` | Replaced with sanctioned `agent_overrides={"model_selection": {"cv": …}}` passed to `Phronesis`; all agent construction stays in `compose_agents` |
| NEW-08 | Preflight report dict used `n_rows`/`n_cols` while `WorkflowState` uses `row_count`/`column_count` | Preflight keys renamed to `row_count`/`column_count` for a single vocabulary |

## 3. API Contract Integrity Checks

- **Explainability contract** (previously broken): canonical service output is
  `{feature_importance, explainer_type, sampled, n_samples_used, n_features_used, max_samples}`.
  `ml/explainability/summary.py` previously validated never-produced keys
  (`feature_names`, `explainer`, `status`). Rewritten to the service contract with
  legacy-key tolerance (`explainer`/`feature_names` accepted if present). 6 tests cover it.
- **Result builders** read the real `best_pipeline` keys
  (`model_type`, `best_params`, `score`, `trials_used`, `time_elapsed`, `truncated`,
  `estimated_training_cost`) — no more phantom keys.
- **Reporting** (`ml/reports/io.py`) reads real `WorkflowState` keys
  (`row_count`, `transform_log`, `preflight_warnings`, `preflight_blockers`,
  `candidate_models`, `resource_report`/`engine`), and no longer reads
  `n_rows`, `engine`, `timestamp`, `errors` etc. as state fields.

## 4. Remaining Gaps (non-blocking)

1. *(REST gap — obsolete since v0.3.0: `interfaces/api/routes.py` was removed.)*
2. No test asserts the full `__all__` / `_LAZY_IMPORTS` symmetry; add an API-contract
   test that every `__all__` name resolves via `getattr(phronesisml, name)`.
3. `WorkflowState.run_id`/`status` remain unpopulated end-to-end (historical BUG-05);
   worth wiring at graph start for fully populated reports.
