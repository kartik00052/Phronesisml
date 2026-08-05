# PhronesisML — Repository Structure

> Read-only audit (Step 2 of the v0.3.0 release-planning audit). Describes the full
> module hierarchy, layering, and architecture of the codebase as it exists on `main`
> (uncommitted QA state). Companion report: `project_docs/PROJECT_CAPABILITY_REPORT.md`.

## Quick Facts

| Aspect | Value |
|---|---|
| Package | `phronesisml` v0.3.0 (`__init__.py:56`) |
| Python support | `>=3.11,<3.14` (`pyproject.toml:11`); `.python-version` = 3.12 |
| Build backend | hatchling; version single-sourced via `[tool.hatch.version]` → `phronesisml/__init__.py` |
| Package tree | ~101 `.py` files (mypy-clean baseline per CHANGELOG 0.3.0) |
| Tests | 21 files under `tests/`; baseline `312 passed, 6 xfailed` (525.66s) |
| Pipeline stages | 11 (`_stages.py:31`) |
| Agents | 11 (`agents/`) |
| Engines | 3 (pandas / polars / spark) |
| CLI commands | 12 (`interfaces/cli/app.py`) |
| Public `__all__` | 79 symbols (`__init__.py:58`) |
| Packaging | pip + uv dual workflow; `uv.lock` tracked |
| CI | `.github/workflows/ci.yml` + `docs.yml` |
| Docs | mkdocs site (`mkdocs.yml`, `docs/`), `project_docs/` (30 files) |

## Top-Level Layout

```
PhronesisML/
├── phronesisml/                  # The package (canonical source)
├── tests/                        # pytest suite (20 files)
├── docs/                         # mkdocs user-facing documentation
├── project_docs/                 # engineering/audit/planning docs (30 files)
├── benchmarks/                   # benchmark harness (baseline only)
├── scripts/                      # demo-data downloader
├── .github/workflows/            # ci.yml, docs.yml + issue/PR templates, dependabot
├── data/                         # demo datasets (iris.csv, credit_card_clients.csv)
├── assets/                       # hero-banner.svg
├── dist/                         # phronesisml-0.3.0 wheel (213,333 B) + sdist (330,888 B)
├── pyproject.toml                # metadata, deps, extras, tooling config
├── uv.lock                       # locked resolution (win32/darwin-arm64/linux)
├── requirements.txt              # pip-pinned equivalent of the lock
├── README.md, CHANGELOG.md, LICENSE, SECURITY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md
├── Makefile, mkdocs.yml, .pre-commit-config.yaml, .editorconfig, .gitignore
├── test_phronesis.py             # legacy E2E diagnostic script (CI runs it)
└── scratch/generated: .venv/, dist/, site/, mlruns/, Phronesis_artifacts/,
                        qa_artifacts/, __pycache__/, *.csv QA datasets (heart,
                        BankChurners, diabetes) at repo root
```

## The Package — `phronesisml/`

### Public entry points (top-level modules)

| Module | Role |
|---|---|
| `__init__.py` | Canonical public surface: `__all__` (79 symbols), lazy-import registry `_LAZY_IMPORTS` (`:144`), `__getattr__` (`:212`), `run_pipeline()` (`:239`), `_extract_summary()` |
| `_stages.py` | Single source of truth for the 11-stage pipeline order + `_STAGES_*` per-operation slices |
| `simple.py` | Simple API — 23 sync + 23 async wrappers over the SDK |
| `sdk.py` | OOP API — `Phronesis` class + 13 report/result dataclasses + `SavedRun` |
| `results.py` | 11 frozen result dataclasses shared by simple API and SDK |
| `_result_builders.py` | Builders converting SDK state → typed result objects |
| `exceptions.py` | Exception hierarchy (10 classes, root `PhronesisError`) |

### Layers (inward dependency)

```
Python SDK (simple / Phronesis / run_pipeline)
        │ calls
        ▼
Workflow (LangGraph graph, WorkflowState, nodes, router, sampling_node)
        │ orchestrates
        ▼
Agents (11 pipeline agents; constructor-injected dependencies)
        │ delegate
        ▼
Services + data/ + ml/ (stateless domain logic)
        │ consume
        ▼
Engines (BaseEngine: pandas / polars / spark)
        ▼
Reports / Storage (report.md, report.html, pipeline.json, model.joblib, …)
```

### `__init__.py` public surface (`__all__` = 79 symbols)

- **Simple API functions (46):** `analyze`, `clean`, `validate`, `detect_target`,
  `detect_task`, `cluster`, `detect_anomalies`, `engineer`, `select_model`, `evaluate`,
  `recommend`, `explain`, `report`, `train`, `profile`, `predict`, `compare`, `save`,
  `restore`, `load`, `version`, `capabilities`, `health` — each with an `_async` twin.
- **Simple result types (11):** `AnomalyResult`, `CleanResult`, `ClusteringResult`,
  `DatasetProfile`, `ExplainResult`, `FeatureResult`, `ModelResult`, `TaskDetectionResult`,
  `TargetResult`, `TrainResult`, `ValidationResult`.
- **OOP API (14):** `Phronesis`, `AnomalyReport`, `ClusteringReport`, `DatasetSummary`,
  `EDAReport`, `EvaluationMetrics`, `ExplanationReport`, `FeatureReport`, `ModelInfo`,
  `TaskInfo`, `TargetInfo`, `ValidationReport`, `ModelComparison`, `SavedRun`.
- **Advanced (8):** `PhronesisConfig`, `SamplingConfig`, `PhronesisError`,
  `ConfigurationError`, `WorkflowError`, `WorkflowState`, `run_pipeline`, `__version__`.

### `configs/`

- `settings.py` — Pydantic configs: `EngineConfig`, `DataConfig`,
  `FeatureSelectionConfig`, `SamplingConfig`, `PhronesisConfig`; canonical byte
  thresholds (`PANDAS_MAX_BYTES` = 2 MB, `DEFAULT_MAX_MEMORY_BYTES` = 500 MB,
  `DEFAULT_MAX_FILE_SIZE_BYTES` = 2 GB).

### `data/`

- `io.py` — loaders (`load_csv`, `load_tsv`, `load_json`, `load_jsonl`, `load_parquet`,
  `load_excel`), multi-file/dir/zip loaders, encoding detection, streaming, size
  estimation.
- `etl.py` — immutable transforms: drop/select/rename columns, filter/sort, dedupe,
  outlier removal, normalize/standardize, one-hot, datetime, splits, sampling (21 fns).
- `eda.py` — summary stats, correlation matrix, missing matrix, distributions, target
  distribution, outliers, skewness, type + quality reports (10 fns).
- `validation.py` — schema/type/quality checks, `validate_dataset` (`:446`),
  `generate_validation_report` (13 fns).
- `validators/checks.py` — engine-coupled `validate_dataframe`.
- `profilers/stats.py` — `profile_dataset` (numeric/categorical profiling).
- `transformers/cleaning.py` — `handle_nulls`, `cast_dtypes`, `encode_categoricals`.
- `loaders/file_loader.py` — format detection, Excel sheet selection, `load_file`.

### `engines/`

- `base_engine.py` — `BaseEngine` ABC + `EngineType` enum (the `DataEngine` interface).
- `pandas_engine.py`, `polars_engine.py`, `spark_engine.py` — implementations.
- `engine_selector.py` — `select_engine` routing: forced preference → memory/size
  estimate → `<2 MB` pandas, `≤500 MB` polars, else spark.
- `recommend.py` — pure heuristics: `recommend_engine`, `engine_capabilities`,
  `engine_comparison_report`.
- `engines/__init__.py` — re-exports `BaseEngine`, `EngineType`, `select_engine`,
  `recommend_engine`, `engine_capabilities`, `engine_comparison_report`.

### `workflow/`

- `state.py` — `WorkflowState` (pydantic, the typed graph state).
- `graph.py` — `build_graph` (LangGraph), `clear_graph_cache`, stage precedence.
- `nodes.py` — `make_node` adapter wrapping an agent.
- `router.py` — conditional edges (`route_after_upload`, `route_after_etl`,
  `route_after_validation`).
- `sampling_node.py` — `create_sampling_node` (pre-flight sampling/resource estimate;
  wired in the `run_pipeline` path only — see NEW-11).

### `agents/` (11 agents, each `agents/<name>/agent.py`)

| Agent | Responsibility |
|---|---|
| `upload` | file existence/size checks, format detection, load |
| `etl` | cleaning (nulls, dtypes, encoding) |
| `validation` | engine-coupled dataframe validation |
| `eda` | profiling via `data/profilers` |
| `target_detection` | target column + task detection |
| `feature_engineering` | FE pipeline + transform recipe |
| `model_selection` | candidate HPO + best model |
| `evaluation` | metrics computation |
| `explainability` | SHAP explanation service |
| `reporting` | markdown/HTML/JSON report building |
| `storage` | persist artifacts via `services/storage.py` |

`agents/base.py` — `AgentResult`, `Tool`, `BaseAgent` protocol, `_StubAgent`.
`agents/compose.py` — `compose_agents` (canonical composition root; the deprecated
`_compose_agents` in `__init__.py` delegates here).

### `ml/`

- `automl/` — `auto_selector.py` (model catalog + `recommend_models` +
  `build_recommendation_report` + `estimate_training_cost`), `trainer.py`
  (`train_models`, adaptive trials/time, `DEFAULT_RANDOM_STATE = 42`).
- `target_detection/` — `detector.py` (`detect_target`, `_score_column`,
  `validate_target_safety`), `analysis.py`.
- `task_detection/` — `detector.py` (`detect_task`, supervised/unsupervised scoring).
- `feature_engineering/` — `transform.py` (transform recipe + `apply_transform_recipe`),
  `engineer.py`, `construction.py`.
- `evaluation/` — `metrics.py` (`evaluate_model`, per-task metric sets, MLflow graceful
  degradation), `report.py`.
- `explainability/` — `service.py` (explainer registry: Tree→Linear→Permutation→Kernel),
  `shap_explainer.py`, `summary.py`.
- `clustering/` — `algorithms.py` (kmeans, DBSCAN, agglomerative + internal scores).
- `anomaly/` — `detector.py` (isolation forest, LOF).
- `reports/` — `builder.py` (markdown + HTML), `io.py` (JSON report, run report).
- `preflight/` — `memory.py`, `estimator.py` (resource estimation), `sampler.py`
  (strategies), `config.py`.

### `services/`

- `storage.py` — `save_artifact`, `save_artifacts` (18-file artifact set), `_package_version`.
- `data_resolution.py` — `ResolvedData`.

### `utils/`

- `dtypes.py`, `resources.py` (memory/time/size estimation, formatting).

### `interfaces/cli/`

- `app.py` — Typer app; 12 commands: `run`, `info`, `version`, `capabilities`,
  `doctor`, `analyze`, `validate`, `profile`, `train`, `explain`, `report`, `compare`.
  UTF-8 stdio shims; `_fail`/`_require_file` helpers. Thin consumer of the SDK.
- Entry point `phronesisml` registered in `pyproject.toml [project.scripts]`.

## Pipeline Stage Order (`_stages.py:31`)

```
upload → etl → validation → eda → target_detection → feature_engineering →
model_selection → evaluation → explainability → reporting → storage
```

Per-operation slices (`_STAGES_*`): `analyze`=1–4, `clean`=1–2, `validate`=1–3,
`detect_target`=1–5, `engineer`=1–6, `select_model`/`evaluate`=1–8, `explain`=1–9,
`report`=1–10, `train`=all 11, `cluster`/`detect_anomalies`=all minus
`explainability`/`storage`, `detect_task`=1–5.

## Model Catalog (`ml/automl/auto_selector.py`)

| Task | Candidates |
|---|---|
| classification | logistic_regression, random_forest, gradient_boosting |
| regression | linear_regression, random_forest, gradient_boosting |
| clustering | kmeans, agglomerative (DBSCAN exists in `algorithms.py` but not catalogued) |
| anomaly_detection | isolation_forest, local_outlier_factor |
| ambiguous | logistic_regression, linear_regression, random_forest, gradient_boosting |

All sklearn; HPO via small grids; adaptive `max_trials` (10–50) / `max_time` (15–120 s).

## Artifact Set (`services/storage.py:175`)

`evaluation.json, metrics.json, training.json, model.json, feature_metadata.json,
target_detection.json, resource_estimation.json, engine_selection.json, eda.json,
validation.json, shap.json, pipeline.json, run_metadata.json, report.md, report.html,
config.json, logs.txt` + `model.joblib` (binary, when trained) → `Phronesis_artifacts/<run_id>/`.

## Tests (`tests/`, 21 files)

`test_artifact_storage`, `test_curve_metrics`, `test_data_eda`, `test_data_etl`,
`test_data_io`, `test_data_validation`, `test_determinism`, `test_evaluation_report`,
`test_explainability`, `test_explanation_summary`, `test_feature_construction`,
`test_interfaces`, `test_model_recommendation`, `test_preflight`, `test_regressions`,
`test_regressions_v030` (6 xfail, QA), `test_report_io`, `test_resources_engines`,
`test_run_report`, `test_sdk_extended`, `test_target_analysis`.

## Documentation

- **User docs (`docs/`):** index, getting-started, architecture, design-decisions,
  examples, troubleshooting, limitations, api; guides/ (simple-api, advanced-api,
  incremental, cli); root_cause/ (NEW-01…04, 08 fixed; NEW-09…14 unfixed QA RCAs).
- **Engineering docs (`project_docs/`, 30 files):** audits (PUBLIC_API_AUDIT,
  ARCHITECTURE_AUDIT, PACKAGING_AUDIT, CODEBASE_INTEGRITY, DUPLICATION, DEPENDENCY,
  MASTER_FUNCTION_MATRIX, API_Contracts, AI_QUALITY_GATE, UV_MIGRATION,
  INSTALLATION/BUILD/CI_VALIDATION, SDK_FUNCTIONAL_VERIFICATION), planning (Roadmap,
  IMPLEMENTATION_ROADMAP, Release_Process, Decision_Log, Known_Issues), state
  (project_state.json), templates.

## Packaging / CI

- hatchling wheel (`packages=["phronesisml"]`), sdist excludes CSVs/tests/docs/project_docs.
- Extras: `cli`, `spark`, `mlflow`, `excel`, `docs`, `dev`, `all`.
- CI (`ci.yml`): auto-format job, lint (ruff + `uv lock --check`), test matrix
  (py3.11/3.12/3.13 × pip/uv), typecheck (mypy 3.11), build (pip + uv + twine + wheel
  import smoke), PyPI publish on `v*` tags.
- `docs.yml` publishes the mkdocs site.
