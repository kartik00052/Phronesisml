# PhronesisML — Project Capability Report

> Read-only audit (Step 20 of the v0.3.0 release-planning audit). Extracts the complete
> public API and capability surface of the codebase as it exists on `main` today and
> assesses release readiness. **No code was modified.** QA facts from the 12-phase pass
> (see `project_docs/SDK_FUNCTIONAL_VERIFICATION.md`) are embedded throughout.
> Companion structure report: `project_docs/REPOSITORY_STRUCTURE.md`.

---

## 1. Executive Summary

PhronesisML v0.3.0 is a **SDK-first, CLI-first, offline-first** automated ML lifecycle
SDK. The full pipeline (upload → ETL → validation → EDA → target detection → feature
engineering → model selection → evaluation → explainability → reporting → storage) runs
entirely locally, orchestrated as a LangGraph of 11 cooperating agents over a typed
`WorkflowState`. It exposes three interfaces over one logic core: a **Simple API**
(23 sync + 23 async functions), an **OOP `Phronesis` class**, and a **12-command CLI**.

The complete 12-phase QA pass leaves the baseline intact — **`312 passed, 6 xfailed`
in 525.66s** — and pins **6 confirmed, unfixed defects** (NEW-09…NEW-14) with
recommended fixes and required regression tests. None of the six is a show-stopper for
the SDK; the highest-impact one (NEW-09, string-categorical predict crash) blocks the
promised string-categorical UX and should be fixed before tagging `v0.3.0`. Overall
**release readiness ≈ 82%** (see §24); the build/test/packaging machinery is solid and
CI-validated, but a few documented gaps and the six confirmed defects should be
addressed (or explicitly deferred) before a public tag.

## 2. Repository Overview

- **Identity:** `phronesisml` v0.3.0 (formerly AetherML); MIT license; author Kartik Sharma.
- **Versioning:** single-sourced `__version__ = "0.3.0"` read by hatchling (dynamic version).
- **State:** `main` branch; `v0.3.0` tag **NOT yet created** (tags stop at v0.2.1). QA
  changes are uncommitted (6 modified source/docs files, 3 new QA docs + regression
  suite + datasets untracked).
- **Lifecycle history (CHANGELOG):** 0.1.x → 0.2.0 rename to PhronesisML → 0.2.1/0.2.2
  stabilization → 0.3.0 decommissions the REST API and adds unsupervised flows +
  extended SDK surface + packaging/uv migration.
- **Size:** ~101 package `.py` files; 21 test files; ~30 project docs; benchmarks,
  scripts, and demo datasets present.

## 3. Architecture

- **Layered:** SDK → LangGraph workflow → agents → services/data/ml → engines → storage.
  Layers depend inward; agents get dependencies via constructor injection
  (`agents/compose.py:25` is the canonical composition root; `_compose_agents` in
  `__init__.py:224` is a deprecated delegation wrapper).
- **State:** typed pydantic `WorkflowState` flows through the graph; routers add
  conditional edges (`workflow/router.py`).
- **Deterministic by design:** `DEFAULT_RANDOM_STATE = 42` (`trainer.py:63`),
  `ExplainConfig.random_seed = 42` (`service.py:56`), `SamplingConfig.random_state = 42`.
  QA Phase 8 confirmed: 3× balanced runs on heart → byte-identical summary.
- **Offline-first:** no network calls in core; optional extras (mlflow, spark) are opt-in.

## 4. Public API Surface

`phronesisml/__init__.py` `__all__` exports **79 symbols**:

| Group | Count | Members |
|---|---|---|
| Simple API functions | 46 | 23 sync + 23 async (`analyze`, `clean`, `validate`, `detect_target`, `detect_task`, `cluster`, `detect_anomalies`, `engineer`, `select_model`, `evaluate`, `recommend`, `explain`, `report`, `train`, `profile`, `predict`, `compare`, `save`, `restore`, `load`, `version`, `capabilities`, `health`) |
| Result types | 11 | `AnomalyResult`, `CleanResult`, `ClusteringResult`, `DatasetProfile`, `ExplainResult`, `FeatureResult`, `ModelResult`, `TaskDetectionResult`, `TargetResult`, `TrainResult`, `ValidationResult` |
| OOP API | 14 | `Phronesis`, `AnomalyReport`, `ClusteringReport`, `DatasetSummary`, `EDAReport`, `EvaluationMetrics`, `ExplanationReport`, `FeatureReport`, `ModelInfo`, `TaskInfo`, `TargetInfo`, `ValidationReport`, `ModelComparison`, `SavedRun` |
| Advanced | 8 | `PhronesisConfig`, `SamplingConfig`, `PhronesisError`, `ConfigurationError`, `WorkflowError`, `WorkflowState`, `run_pipeline`, `__version__` |

Lazy loading: heavy symbols resolve on first access via `_LAZY_IMPORTS`/`__getattr__`
(`__init__.py:144`, `:212`) so `import phronesisml` stays light.

## 5. SDK (OOP API)

`Phronesis(data_path, engine=None, config=None, ...)` — stage-by-stage control with
auto-train-before-use:

- **Lifecycle:** `load()` → `run(mode="balanced")`; `_run_stages` honors stage slices.
- **Stage methods:** `clean(null_strategy)`, `validate()`, `eda()`, `detect_target()`,
  `engineer_features()`, `recommend_model(cv, model_type)`, `train(cv, model_type)`,
  `evaluate()`, `explain()`, `detect_task()`, `cluster()`, `detect_anomalies()`.
- **Outputs:** `summary()`, `profile()`, `analyze()`, `target()`, `report()`,
  `generate_report(format="markdown")`.
- **Accessors:** `get_data()`, `get_cleaned_data()`, `get_features()`, `get_model()`.
- **Production surface:** `predict(data, already_engineered=False)` (saved-recipe
  transform), `compare(model_types)`, `save(directory)`, classmethod `restore(directory)`,
  `version()`, `capabilities()`, `health()`.
- **Aliases:** `engineer()`→`engineer_features`, `select_model()`/`recommend()`→
  `recommend_model`.
- **Properties:** `data_path`, `config`, `state`, `elapsed`; `__repr__`/`_repr_html_`.
- **`SavedRun`:** `from_directory`, `predict` — offline inference from a saved artifact dir.
- **Dataclass reports** carry `as_dict()` (`ModelComparison`), `best_model` property, etc.
- **Verified behaviors (QA):** auto-train before `explain`/`compare`/`predict` is
  intended; `predict(dict-of-scalars)` raises a raw pandas error (UX note); full
  `capabilities()` dict enumerates 26 SDK methods, 6 task types, 4 explainers, 11 stages.

## 6. Simple API

Functional wrapper over the SDK (each is one stage-slice + a typed frozen result):
`analyze/profile` → `DatasetProfile`, `clean` → `CleanResult`, `validate` →
`ValidationResult`, `detect_target` → `TargetResult`, `engineer` → `FeatureResult`,
`select_model`/`recommend` → `ModelResult`, `evaluate` → `ModelResult`, `explain` →
`ExplainResult`, `train` → `TrainResult`, `cluster` → `ClusteringResult`,
`detect_anomalies` → `AnomalyResult`, `detect_task` → `TaskDetectionResult`,
`predict` → `list`, `compare` → `ModelComparison`, `save`/`restore`/`load` →
`SavedRun`, `version`/`capabilities`/`health` → scalars/dicts. Every function has a
matching `_async` twin. Doc-drift caveat: docs say "12 functions" but the real surface
is 23 (+ async) — see NEW-14.

## 7. CLI

Typer app `phronesisml` (thin consumer of the SDK), 12 commands:

| Command | Purpose |
|---|---|
| `run` | full pipeline (flags: `-e/--engine`, `-n/--nulls`, `-v/--verbose`) |
| `analyze` / `profile` | profiling (alias pair) |
| `validate` | validation report |
| `train` | full ML pipeline, report best model (`--cv`, `--model/-m`) |
| `explain` | SHAP feature importance |
| `report` | markdown report, `-o/--output` file write |
| `compare` | model ranking (`-m/--model` repeatable, `--cv`) |
| `info` / `version` | version + installed components |
| `capabilities` | SDK capability inventory |
| `doctor` | offline dependency/self checks (exit 1 on missing core) |

Known issues (QA): `compare` without `-m` crashes (`'NoneType' object is not iterable`,
`app.py:403`) — **NEW-10**; no `evaluate` command (SDK/simple have it) — **NEW-12**;
docs claim 2–4 commands, real surface is 12 — **NEW-14**.

## 8. ML Capability Matrix

| Capability | Supported | Notes |
|---|---|---|
| Task detection | classification / regression / clustering / anomaly_detection / ambiguous / analytics | `detect_task` + target detector |
| Auto target detection | ✅ | heuristic scoring, safety validation, overridable |
| Models (sklearn) | 12 catalogued | see §10 |
| HPO | ✅ grid search | adaptive 10–50 trials, 15–120 s budgets, hard/soft ceilings |
| Metrics | per-task | classification (acc/prec/rec/F1/CM/ROC-AUC/PR), regression (RMSE/MAE/R²), clustering (silhouette/DB/CH), anomaly (contamination) |
| MLflow tracking | opt-in extra | graceful degradation when unavailable |
| Unsupervised flows | ✅ clustering + anomaly detection | wired end-to-end in 0.3.0 |
| Cost estimation | ✅ heuristic | low/medium/high |
| Determinism | ✅ | seeded by default (42) |
| String-categorical pipeline | ❌ **NEW-09** | predict/restore→predict crashes on string categoricals |
| Sampling / resource pre-flight | ⚠️ **NEW-11** | only wired in `run_pipeline` path, SDK `build_graph` omits it |

## 9. Data Pipeline Coverage

| Stage | Coverage | Where |
|---|---|---|
| Upload | file checks, format detection, CSV/TSV/JSON/JSONL/Parquet/Excel, dir/zip/multi, encoding detection, streaming | `data/io.py`, `data/loaders/file_loader.py`, `agents/upload` |
| ETL | nulls (drop/fill/flag), dtype casting, categorical encoding, dedupe, outlier removal, normalize/standardize, datetime, one-hot, splits | `data/etl.py`, `data/transformers/cleaning.py` |
| Validation | schema/type/quality, missing/dupes/constraints/uniques, datetime/categorical/numeric checks, target/feature checks, `validate_dataset` | `data/validation.py`, `validators/checks.py` |
| EDA | stats, correlations, missing matrix, distributions, target distribution, outliers, skew, type/quality reports | `data/eda.py`, `data/profilers/stats.py` |
| Target detection | `_score_column` heuristic, ID exclusion, safety | `ml/target_detection/detector.py` |
| Feature engineering | transform recipe (impute/encode/scale/select), outlier flag, min-features guard | `ml/feature_engineering/*` |
| Sampling | 8 strategies (auto/random/stratified/time/head/diversity/anomaly/text) | `ml/preflight/sampler.py` |
| Engine routing | forced override + size-based auto-select | `engines/engine_selector.py` |
| Training | split, per-task metric, HPO | `ml/automl/trainer.py` |
| Evaluation | per-task metrics, ambiguity caveats | `ml/evaluation/metrics.py` |
| Explainability | Tree→Linear→Permutation→Kernel routing, row/feature caps, fallback | `ml/explainability/service.py` |
| Reporting | markdown + HTML + JSON, run report | `ml/reports/{builder,io}.py` |
| Storage | 18-file artifact set, joblib model, run metadata | `services/storage.py` |

Edge cases verified in QA: all-null CSV → ETL null-drop → clean reports "zero rows
(empty)"; corrupted CSV + duplicate columns load permissively (exit 0) — both accepted,
documented behaviors.

## 10. Engine / Model / Dataset Support

- **Engines (3):** pandas (<2 MB), polars (≤500 MB), spark (extra, `local[*]`). Capability
  matrix + recommendation reports in `engines/recommend.py`. QA: heart → pandas,
  BankChurners → pandas, diabetes → polars (all correct by size).
- **Formats:** CSV/TSV, JSON/JSONL, Parquet, Excel (extra), Feather/Arrow, dir/zip.
- **Models:** logistic_regression, random_forest, gradient_boosting (classification);
  linear_regression, random_forest, gradient_boosting (regression); kmeans,
  agglomerative (clustering; DBSCAN present but uncatalogued); isolation_forest,
  local_outlier_factor (anomaly).
- **QA datasets at root:** `heart.csv` (1025 rows), `BankChurners.csv` (1.5 MB),
  `diabetes_prediction_dataset.csv` (3.8 MB); curated demos in `data/`.
- **QA per-dataset results:** heart → RandomForestClassifier acc **1.0**, TreeExplainer
  (12 features), predict OK (numeric); BankChurners → GradientBoostingRegressor R² 0.66
  (score 0.6281); diabetes → GradientBoostingRegressor score 0.2345; **both string
  datasets FAIL predict** (NEW-09).

## 11. SHAP Explainability Matrix

| Explainer | Route condition | Verified (QA Phase 6) |
|---|---|---|
| TreeExplainer | forest/boosting/tree/xgb/lgbm/catboost/extra tree/histgradient, or `feature_importances_` (non-SVC) | ✅ RandomForest → TreeExplainer |
| LinearExplainer | linear/logistic/ridge/lasso/elastic/sgd/… | ✅ LogisticRegression → LinearExplainer |
| PermutationExplainer | model-agnostic default | ✅ fallback path |
| KernelExplainer | absolute fallback on routing/failure | ✅ code path |

Guards: `max_samples=100` (hard ceiling), `max_features=50` (variance cap), deterministic
sampling seed 42; supervised/unsupervised routing handled by the agent.

## 12. Reporting Matrix

- **Markdown report** (`ml/reports/builder.py`): narrative, summary, validation, EDA,
  target detection, FE, model selection, evaluation, explainability, notes.
- **HTML report:** `build_html_report` (markdown→HTML pipeline).
- **JSON report / run report** (`ml/reports/io.py`): `build_json_report`,
  `build_run_report`, `write_report`, metrics tables, recommendations.
- **CLI:** `report` writes `-o` markdown; `run`/`train` print summaries.
- **Doc drift (NEW-14):** docs repeatedly reference a phantom `evaluation_report.json`
  artifact that storage does not produce (real file is `evaluation.json`).

## 13. Artifact Matrix (`services/storage.py:175`)

| Artifact | Always written | Trained pipeline | Notes |
|---|---|---|---|
| `evaluation.json`, `metrics.json` | ✅ (placeholder) | ✅ real | |
| `training.json`, `model.json` | ✅ (placeholder) | ✅ real | |
| `feature_metadata.json` | ✅ | ✅ | |
| `target_detection.json` | ✅ | ✅ | |
| `resource_estimation.json` | ✅ placeholder | **always placeholder** | **NEW-11** (never populated) |
| `engine_selection.json` | ✅ | ✅ | |
| `eda.json`, `validation.json` | ✅ | ✅ | |
| `shap.json` | ✅ placeholder | ✅ (supervised) | |
| `pipeline.json`, `config.json`, `run_metadata.json` | ✅ | ✅ | |
| `report.md`, `report.html` | ✅ | ✅ | HTML wrapped in try/except |
| `logs.txt` | ✅ | ✅ | deterministic transform log |
| `model.joblib` | ❌ | ✅ | binary, when trained |

Stored under `Phronesis_artifacts/<run_id>/`; `save()` uses the same service for a
self-contained run directory.

## 14. Packaging

- **Build:** hatchling; `dynamic = ["version"]`; wheel ships `phronesisml` + `py.typed`;
  sdist excludes CSVs/tests/docs/project_docs/benchmarks.
- **Artifacts:** `dist/phronesisml-0.3.0-py3-none-any.whl` (213,333 B) and
  `phronesisml-0.3.0.tar.gz` (330,888 B) already built; QA `twine check` clean.
- **Extras:** `cli`, `spark`, `mlflow`, `excel`, `docs`, `dev`, `all`. Note:
  `capabilities()` reports `extras` without `docs` (minor inconsistency).
- **Entry point:** `phronesisml = phronesisml.interfaces.cli.app:app`.
- **CI build gate:** `python -m build` + `uv build` + `twine check` + wheel import smoke
  test; PyPI publish on `v*` tags with OIDC.
- **Lint/type:** ruff (E/F/I/N/UP/B/SIM/ANN, py311 target, line 100); mypy strict on 3.11.

## 15. uv Compatibility

- **First-class:** `uv.lock` tracked and resolvable for win32, darwin-arm64, linux
  (`pyproject.toml [tool.uv] environments`); darwin-x86_64 excluded due to shap/numba
  numpy pin conflict.
- `uv sync --all-extras`, `uv build`, `uv lock --check` all supported; CI runs an
  explicit uv leg (3.11/3.12/3.13) plus `uv run python test_phronesis.py`.
- QA fresh-install into a clean uv venv (py3.12.13) was successful; `import phronesisml`
  + full suite green in the qa-venv (py3.11.9).

## 16. pip Compatibility

- **First-class:** `pip install -e ".[dev]"` and plain `pip install phronesisml` both
  CI-validated; `requirements.txt` regenerated to mirror the locked resolutions.
- QA: clean pip-installed environment runs the full suite; CLI extra (`typer`+`rich`)
  required for `phronesisml` commands and raises a helpful ImportError otherwise.

## 17. Dependency Analysis

| Dependency | Range | Locked (requirements.txt) |
|---|---|---|
| pydantic | >=2.0,<3.0 | 2.13.4 |
| langgraph | >=0.2,<1.0 | 0.6.11 |
| pandas | >=2.0,<3.0 | 2.3.3 |
| polars | >=1.0,<2.0 | 1.43.2 |
| scikit-learn | >=1.3,<2.0 | 1.9.0 |
| numpy | >=1.24,<2.5 | 2.4.6 |
| shap | >=0.51,<0.53 | 0.52.0 (core dependency) |
| pyarrow | >=15.0 | 19.0.1 |
| joblib | >=1.3,<2.0 | 1.5.3 |

Extras pinned too; dev tooling: ruff/mypy/pytest(+asyncio,cov,xdist)/coverage/
pre-commit/build/twine. Supply-chain posture: dependency-pinned releases, MIT, no
network in core. QA health check reports all core deps installed (status "ok").

## 18. Test Coverage

- **Baseline:** `312 passed, 6 xfailed` in 525.66s (QA final, fresh installs both venvs).
- **21 test files** spanning storage, metrics/curves, data layers, determinism,
  evaluation, explainability, FE construction, CLI/UTF-8, model recommendation,
  preflight, regressions, reports, engines/resources, SDK extended surface.
- **`tests/test_regressions_v030.py`:** 6 strict `xfail` tests pinning NEW-09…NEW-14
  (each references the RCA doc).
- **Legacy diagnostic:** `test_phronesis.py` (8/8, run by CI on both pip and uv legs).
- Missing: no dedicated benchmark-as-test, no coverage % threshold in CI, no Windows
  CI leg (local-only QA covered Windows).

## 19. Documentation Coverage

- **User docs** (mkdocs, `docs/`): full guide set (getting started, simple/advanced API,
  CLI, incremental usage, architecture, design decisions, examples, troubleshooting,
  limitations, API reference) + `root_cause/` RCA library.
- **Engineering docs** (`project_docs/`, 30 files): audits (public API, architecture,
  packaging, duplication, dependency, function matrix, API contracts, integrity, AI
  quality gate, install/build/CI validation, SDK functional verification), planning
  docs, decision log, known issues, project state.
- **Drift (NEW-14):** phantom `evaluation_report.json` (KB:364,516; ROADMAP:136,318,395;
  AUDIT:44,141), CLI docs "2–4 commands" vs 12 real, simple API docs "12 functions" vs
  23 (+async), phantom params/attrs (`fill_value=`, `DatasetProfile.numeric_columns`,
  `CleanResult.shape`, `EvaluationMetrics.get()`, `WorkflowState.target_confidence`).

## 20. Repository Health

- ✅ mypy-clean (0 errors, 101 files); ruff-clean; pre-commit hooks configured.
- ✅ Determinism verified (3× heart runs identical).
- ✅ Full suite green + 6 pinned xfails; regressions strictly fail-visible.
- ✅ Dual pip/uv install paths validated; twine-clean dist artifacts exist.
- ✅ No secrets committed; `.gitignore` covers venvs, dist, mlruns, artifacts.
- ⚠️ `__pycache__` in `scripts/` is tracked-repo residue; QA CSVs at repo root are
  untracked by design; no `.github/workflows` found by glob because dot-dirs are hidden
  (they exist: `ci.yml`, `docs.yml`).
- ⚠️ README roadmap still says "version 0.2.0" badge; README claims clustering includes
  DBSCAN candidate (code catalog does not expose it).

## 21. Missing Capabilities

- `evaluate` CLI command (SDK/simple have it) — **NEW-12**.
- String-categorical end-to-end support — **NEW-09**.
- Resource estimation actually populating `resource_estimation.json` in the SDK path —
  **NEW-11**.
- Formal published benchmark numbers (README explicitly defers to roadmap).
- Plugin system, S3/GCS/Azure storage backends, DuckDB engine, PDF reports, parallel
  agent branching, GUI, HITL checkpoints (all roadmap "planned").
- Reproducible-benchmark-as-test and coverage gate in CI.

## 22. Partially Implemented

- **Sampling/pre-flight:** full implementation exists (`ml/preflight/*`) but the SDK
  graph path omits the node — only `run_pipeline` wires it (**NEW-11**).
- **Clustering:** DBSCAN implemented (`_run_dbscan`) but not in the candidate catalog.
- **`capabilities()` extras list:** omits `docs` extra that pyproject declares.
- **Prediction UX:** `predict` with scalar dicts raises a raw pandas error; string
  categoricals crash in the transform recipe (**NEW-09**).
- **Docs vs public surface:** multiple drift points (**NEW-14**).

## 23. Technical Debt

1. **NEW-09** (High): `transform.py:116` `result[col].astype(float)` with empty
   `encoding_maps` crashes predict on string categoricals; fault chain
   `agents/etl/agent.py:115-116` → `agents/feature_engineering/agent.py:113` (recipe
   built from FE log only).
2. **NEW-10** (Med): CLI `compare` default `None` → `list(model) or None` crash
   (`interfaces/cli/app.py:403`).
3. **NEW-11** (Low): sampling node unwired in `sdk.py:514` `build_graph`; placeholder
   `resource_estimation.json` in every run.
4. **NEW-12** (Low): missing `evaluate` CLI command (exit 2).
5. **NEW-13** (Low): detector prose "2–5 unique values" vs code `range(3, 6)`.
6. **NEW-14** (Med): doc drift across KB/ROADMAP/AUDIT + phantom API claims.
7. Stage order triplication was already consolidated into `_stages.py` (NEW-03 fixed);
   `_FULL_PIPELINE_STAGES` is now the single source.
8. Minor: `__pycache__` residue in `scripts/`; README version badge stale.

## 24. Recommended Priorities (pre-tag)

1. **Fix NEW-09** (persist encoding maps from ETL into the recipe / emit one-hot
   columns) — unlocks string-categorical `predict`. High value, moderate effort.
2. **Fix NEW-10** (default `model` to a non-`None` sentinel in the CLI `compare`
   option). One-liner.
3. **Fix NEW-12** (add `evaluate` CLI command). Small.
4. **Fix NEW-11** (wire sampling node into `sdk.py build_graph`). Small.
5. **Fix NEW-13** (align prose/range). Trivial.
6. **Fix NEW-14** (docs cleanup for release). Mechanical.
7. Then `git tag v0.3.0` (CI gates: lint/typecheck/test/build/publish on `v*`).

## 25. Release Readiness

| Dimension | Score | Rationale |
|---|---|---|
| Functionality | 85% | Full supervised/unsupervised pipeline green; string-categorical UX broken |
| Public API stability | 90% | 79-symbol surface, single-sourced version, aliases complete |
| Quality gates | 90% | 312 passed + 6 pinned xfails; ruff/mypy/CI/twine all clean |
| Packaging | 95% | wheel+sdist built, twine clean, pip+uv both validated |
| Docs | 70% | Strong volume but NEW-14 drift misleads users |
| Determinism | 95% | Verified identical runs; seeded by default |

**Overall: ≈ 82%.** Safe to tag if NEW-09 + NEW-10 are fixed first (or explicitly
documented as deferred in the release notes); otherwise the advertised string-
categorical support and `compare` CLI will misbehave for users.

## Conclusion

PhronesisML v0.3.0 is a mature, well-engineered, offline-first ML lifecycle SDK with a
clean layered architecture, a rich and stable public surface, and CI-validated packaging.
The QA pass confirmed the baseline is intact and isolated exactly six remaining defects
(NEW-09…NEW-14), all documented with fix recipes and regression tests. With the two
medium/high-impact items resolved (or transparently deferred), the repository is ready
to tag `v0.3.0`.
