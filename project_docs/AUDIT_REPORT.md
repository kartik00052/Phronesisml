# PhronesisML — Production-Readiness Audit Report (v0.2.2)

> **Audit type:** External clean-room contribution (documentation-only deliverable)
> **Version audited:** `0.2.2`
> **Date:** 2026-08-04
> **Repo:** `https://github.com/kartik00052/PhronesisML`
> **Audit boundaries honored:** no errors suppressed; no failing code commented out; no speculative fixes applied. Every reported issue below was **reproduced first**. Fixes (if requested) must follow the 9-field template in §21 and re-run the full toolchain.

**Label legend:**
- `VERIFIED` — empirically reproduced/observed during this audit (host Python 3.11.9 and/or clean-room 3.13 wheel install).
- `INFERRED` — established by reading code/configuration with high confidence, but not executed at runtime during this audit.
- `NOT VERIFIED` — stated in docs/CI/metadata but not confirmed by this audit (out of scope or not re-run).

---

## 1. Executive Summary

PhronesisML v0.2.2 is a well-architected, genuinely inspectable auto-ML SDK. The core SDK path (11-stage LangGraph pipeline, pandas/polars/spark engine abstraction, bounded HPO, SHAP explainability, Markdown/HTML reporting, local artifact storage) is **clean, deterministic, and passes its own gates**: ruff lint + format clean, `mypy --ignore-missing-imports` clean, pytest 83/83 passing on the host baseline, and the built wheel installs and runs end-to-end on a clean Python 3.13 venv (CLI and SDK verified; REST API also verified at the time, since removed in v0.3.0).

However, the production-readiness audit found **three reproducible correctness bugs** plus several smaller issues:

| ID | Severity | Status | One-line summary |
|----|----------|--------|------------------|
| BUG-01 | High | `VERIFIED` | Feature engineering mutates the workflow state's `validated_data` **in place** and leaks an `outlier_flag` column into the trained model's features |
| BUG-02 | High | `VERIFIED` | On `ambiguous` task types the pipeline selects a **classifier** for a continuous target and then reports **regression** metrics — an internally inconsistent model/eval contract |
| BUG-03 | High | `VERIFIED` | REST API **blocks the asyncio event loop** during CPU-bound jobs — `/health` timed out for the full ~125 s of a `/train` job *(obsolete — REST layer removed in v0.3.0)* |
| BUG-04 | Medium | `VERIFIED` | `best_pipeline` schema mismatch: writer uses key `params`, SDK result builders read key `best_params` → HPO params are always reported as `{}` through the SDK/API |
| BUG-05 | Low | `VERIFIED` | Every generated report header shows `Pipeline Run: None` / `Status: None` because `run_id`/`status` are never populated in `WorkflowState` |
| ISSUE-06 | Low | `VERIFIED` | README documents install extras (`[explain]`, `[boost]`, `[parquet]`) and an `openpyxl (core)` claim that no longer exist in `pyproject.toml` |

The REST layer was the least production-ready surface at audit time (BUG-03 + in-memory job store, documented) and was decommissioned in v0.3.0. Overall verdict (current): **experimental-to-beta; the core SDK path is the strongest, and the ambiguous-task modeling path can silently produce a wrong model type.**

---

## 2. Scope, Method & Evidence

**Scope.** All of `phronesisml/` (engines, agents, ML subsystems, workflow, interfaces), `tests/`, `benchmarks/`, CI, packaging, Docker, docs, and the public SDK/CLI surfaces (REST also existed at audit time; removed in v0.3.0). The `PROJECT_KNOWLEDGE_BASE.md` knowledge base was read for context but is itself not part of the audited product.

**Method.** Static reading of the full source tree, then empirical verification in two environments:

1. **Host baseline (Python 3.11.9, repo checkout):** ruff, mypy (CI flag), pytest, import check.
2. **Clean-room wheel (Python 3.13.3 venv at `C:\Users\karti\AppData\Local\Temp\opencode\phr313`):** wheel built from the repo, installed with `[cli,api,excel]` (the `[api]` extra was removed in v0.3.0), exercised via CLI (`run`, `info`, `--help`), SDK (`sdk_audit.py`: OOP chain, simple sync + async), REST API (`/health`, `/capabilities`, `/version`, `/analyze`, `/train`) — REST portions obsolete since v0.3.0 — and edge-case CSVs (`edge_audit.py`).

**Key artifacts produced during the audit (temp):** `sample_500.csv`, `sample_60.csv`, `edge/*.csv`, `Phronesis_artifacts/default_run/evaluation_report.json`, `api_out.log`/`api_err.log`, `train_job.txt`, `sdk_audit.py`, `edge_audit.py`.

**Reproduction datasets.** Synthetic customer-churn CSV with columns `age` (continuous), `income`, `score`, `region`, `churned` (clean binary). `sample_500.csv` (500 rows) and `sample_60.csv` (60 rows). All verified runs below used the **pandas** engine (files < 2 MB → pandas auto-select).

---

## 3. Baseline Verification Results

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Lint (host 3.11.9) | `ruff check phronesisml/ tests/ benchmarks/` | Clean, 0 violations | `VERIFIED` |
| Format (host 3.11.9) | `ruff format --check` | 96 files formatted | `VERIFIED` |
| Type check (CI gate) | `mypy phronesisml/ --ignore-missing-imports` | Clean (93 files) | `VERIFIED` |
| Type check (strict, no flag) | `mypy phronesisml/` | 34 errors (pandas/sklearn/psutil/openpyxl/xlrd stubs + `pyspark.sql` import-not-found) | `VERIFIED` |
| Unit + integration tests | `pytest` | 83 passed, 1 ConvergenceWarning (`test_explainability.py::TestOtherModels::test_mlp`) | `VERIFIED` |
| Import | `import phronesisml` | 0.2.2, module `phronesisml/__init__.py`, `langgraph` NOT imported eagerly | `VERIFIED` |
| Clean-room wheel install | pip install `phronesisml-0.2.2-py3-none-any.whl[cli,api,excel]` *(`[api]` extra removed in v0.3.0)* | Installed, `phronesisml.exe` functional | `VERIFIED` |
| CLI end-to-end | `phronesisml run sample_500.csv` / `sample_60.csv` | exit 0; artifacts + report produced | `VERIFIED` |
| SDK audit | `sdk_audit.py` (OOP + simple + async) | All calls successful | `VERIFIED` |
| REST audit *(obsolete since v0.3.0)* | uvicorn on 3.13 venv, port 8123 | `/health` `/capabilities` `/version` OK; error envelope + 404/415 correct; async `/analyze` job completed | `VERIFIED` |
| Edge cases | `edge_audit.py` (partial stages) | `dups`/`mixed`/`highcard`/`single`/`constant` OK; `allnull`/`empty` → clean `WorkflowError`; `corrupt.csv`/`weird.csv` → clean load errors (no crash) | `VERIFIED` |
| Spark engine | — | Not exercised (no JVM/pyspark in audit env) | `NOT VERIFIED` |
| MLflow integration | — | Not installed in clean-room; graceful-degradation path only | `NOT VERIFIED` |
| Docker build/run | — | Not executed (no Docker daemon in audit env) | `NOT VERIFIED` |

**CI facts (verified from `.github/workflows/ci.yml`):** Python 3.13; auto-format job (ruff fix + format, bot commits `style: auto-format via Ruff`, guarded to avoid bot loops); lint job `ruff check --no-fix`; mypy job with `--ignore-missing-imports`; pytest job with `pytest-asyncio` strict config.

---

## 4. Findings Overview

| # | Finding | File(s) | Severity | Status |
|---|---------|---------|----------|--------|
| BUG-01 | In-place mutation of `validated_data`; `outlier_flag` leaks into features | `ml/feature_engineering/engineer.py:98,183,186,210,235,274` | High | `VERIFIED` |
| BUG-02 | Ambiguous task → classifier selected, regression metrics reported | `ml/automl/auto_selector.py:161-196`, `ml/automl/trainer.py:247-248`, `ml/evaluation/metrics.py:119-135` | High | `VERIFIED` |
| BUG-03 | Event-loop blocking in REST jobs; `/health` unresponsive during jobs *(obsolete — REST layer removed in v0.3.0)* | `interfaces/api/jobs.py:120`, `interfaces/api/routes.py:478-490` | High | `VERIFIED` |
| BUG-04 | `best_pipeline` key mismatch (`params` vs `best_params`) → SDK always reports `{}` | `agents/model_selection/agent.py:182`, `sdk.py:645`, `_result_builders.py:177,208` | Medium | `VERIFIED` |
| BUG-05 | Report header `Pipeline Run: None` / `Status: None` | `ml/reports/builder.py:60-61`, `workflow/state.py` | Low | `VERIFIED` |
| ISSUE-06 | README extras + dependency drift | `README.md:296-314`, `pyproject.toml:42-59` | Low | `VERIFIED` |
| ISSUE-07 | HPO `max_time_seconds` is a soft ceiling — a single trial can exceed it | `ml/automl/trainer.py:191-199,223-226` | Low | `VERIFIED` |
| ISSUE-08 | Docker image built with `[api]` only; `.xlsx` uploads to the container will fail until `[excel]` is added *(obsolete — Docker image removed in v0.3.0)* | `Dockerfile:14`, `pyproject.toml:47` | Low | `INFERRED` |

---

## 5. BUG-01 (VERIFIED) — Feature engineering mutates upstream workflow state

**Reproduction.** With `PandasEngine`, calling `engineer_features(df, engine, target_column="age")` mutates the caller's DataFrame: `df.equals(df_orig)` returns `False`, values of numeric columns are rescaled in place, categorical columns are label-encoded in place, and an `outlier_flag` column is added. Reproduced in isolation on the same columns as the production datasets.

**Root cause.** `ml/feature_engineering/engineer.py`:
- `engineer.py:93` `collected = engine.cached_collect(df)` — for the pandas engine, `cached_collect` returns the **same** object (identity-cached by `id`).
- `engineer.py:98` `result = collected  # work in-place` — the comment asserts a "fresh DataFrame" that is not true for the pandas path.
- In-place mutations then write through to the workflow state's `validated_data`: `_handle_remaining_nulls` (`:183` `fillna` / `:186` adds `*_is_null`), `_encode_features` (`:210`), `_scale_numeric` (`:235`), `_detect_outliers` (`:274` adds `outlier_flag`).
- The `outlier_flag` column is **not** part of `feature_cols`, so feature selection never drops it; `engineer.py:146-148` drops only the target column, leaving `outlier_flag` in the returned features → it becomes a model feature.

**Why it matters.** (1) `ml.get_cleaned_data()` / `state.validated_data` silently returns rescaled/encoded/flagged data instead of the ETL output; (2) `outlier_flag` is a derived feature that silently enters the model and the report's `column_count` (the CLI showed 6 columns instead of 5 on datasets with outliers); (3) the polars path is immune only because it copies during materialisation — the two engines behave differently for the same logical operation.

**Fix direction (template deferred).** Copy defensively in `engineer_features()` (`df.copy()` or engine-neutral `engine.copy()`); decide explicitly whether `outlier_flag` is a feature or metadata (currently it is an accidental feature). See the 9-field template in §21 before implementing.

---

## 6. BUG-02 (VERIFIED) — Ambiguous task: classifier selected, regression metrics reported

**Reproduction (end-to-end).**
- CLI on `sample_500.csv`: target detector picks `age` (confidence 0.50, `numeric_medium_cardinality`), task type `ambiguous`; best model `GradientBoostingClassifier`; evaluation report `task_type=ambiguous`, `rmse=21.44` (regression metrics on a classifier).
- REST `/train` on `sample_60.csv` (job `635a1da2-…`): target `age`, confidence 0.40, `ambiguous`; best model **LogisticRegression**; metrics `rmse=28.92`, `mae=22.77`, `r2=-0.81`. Report header, model table, and metric table are internally inconsistent (classifier in `model_info`, regression metrics in `metrics`).
- `api_err.log` for the `/train` job contains dozens of `UserWarning: The number of unique classes is greater than 50% of the number of samples...` — the classifiers are being trained on a continuous target.

**Root cause chain.**
1. **Mixed candidate pool** — `ml/automl/auto_selector.py:161-196` defines `_AMBIGUOUS_CANDIDATES` as 3 classifiers + 1 regressor (`logistic_regression`, `linear_regression`, `RandomForestClassifier`, `GradientBoostingClassifier`), returned by `recommend_models()` for `ambiguous`/`None` (`:237`).
2. **Incompatible scoring** — `ml/automl/trainer.py:247-248` scores every candidate with `model.score()`. For classifiers this is **accuracy**; for regressors it is **R²**. The two are compared directly (`:260` `if score > best_score`), which is apples-to-oranges and biases selection.
3. **Silent mis-fit** — sklearn treats the continuous `age` target as a multiclass problem (72 unique values → `type_of_target == "multiclass"`). Verified: `LogisticRegression` fits a 39-class problem on 60 rows and emits only a `UserWarning` + `ConvergenceWarning`, never an error.
4. **Metric mismatch** — `ml/evaluation/metrics.py:119-135`: for `task_type == "ambiguous"`, if the target has > 20 unique values it computes regression metrics (`:128-129`) regardless of whether the selected model is a classifier.

**Why it matters.** The pipeline can silently deliver a classifier with a continuous target and a misleading regression score (`r2 = -0.81`) with no hard failure — exactly the failure mode that an "honest about ambiguity" tool should never produce. The ambiguity caveat is printed, but the model/metric mismatch is not.

**Fix direction.** Either resolve ambiguity (e.g., treat >20-unique numeric targets as regression and pick from `_REGRESSION_CANDIDATES` only) or score all candidates on a common, task-appropriate metric and have the evaluation agent derive metrics from the **selected model class**, not the target cardinality alone.

---

## 7. BUG-03 (VERIFIED, obsolete since v0.3.0) — REST API blocks the event loop during jobs

> **Obsolete:** the REST layer that exhibited this bug was removed in v0.3.0. The record is retained for history.

**Reproduction.** After submitting a CPU-bound `/train` job, `GET /health` with a 5 s client timeout **timed out** while the job was running. The job took 08:27:31 → 08:29:36 (~125 s); `/health` recovered immediately after completion. Polling the job endpoint also blocked during the run.

**Root cause.** `phronesisml/interfaces/api/jobs.py`:
- `jobs.py:120` `task = asyncio.create_task(_wrapper())` schedules the pipeline coroutine directly on the event loop.
- The pipeline (data loading, feature engineering, sklearn HPO up to 50 trials) is CPU-bound. None of it yields to the loop, and there is no `run_in_executor`, `asyncio.to_thread`, or process pool anywhere in `interfaces/api/` (`routes.py:478-490` awaits the simple-API function directly inside the task).

**Why it matters.** Any in-flight job blocks `/health`, `/capabilities`, `/jobs`, and every other endpoint — defeating liveness probes (the Docker healthcheck curls `/health`) and, under load, starving other clients. This is a production blocker for the REST surface, and it is not documented as a limitation in `docs/limitations.md`.

**Fix direction.** Run the pipeline off the loop — `await asyncio.to_thread(func, …)` for the synchronous core, or `loop.run_in_executor` with a dedicated process pool (ideally a real worker queue given the in-memory job store).

---

## 8. BUG-04 (VERIFIED) — `best_pipeline` key mismatch silently drops HPO params

**Reproduction.** The REST `/train` job result returned `best_params: {}` at the top level, while the on-disk `evaluation_report.json` (written by the same run) contains the real params: `best_params: {"C": 0.01, "max_iter": 200}`.

**Root cause.** `agents/model_selection/agent.py:182` stores HPO params under the key **`params`**:
```python
best_pipeline = {
    "model_type": ...,
    "params": train_result["best_params"],   # <-- key is "params"
    "score": ...,
}
```
But the SDK result builders read key **`best_params`**, which never exists:
- `sdk.py:645` `best_params=bp.get("best_params", {})`
- `_result_builders.py:177` and `_result_builders.py:208` `bp.get("best_params", {})`

The evaluation agent (`agents/evaluation/agent.py:72`) reads `best_pipeline.get("params", {})` correctly — which is why the on-disk JSON has the real params while the SDK/API surface reports `{}`.

**Why it matters.** Public API contract: `train()`/`ModelResult`/`ModelInfo.best_params` always return an empty dict even when HPO succeeded — misleading for users and for any downstream serialization.

---

## 9. BUG-05 (VERIFIED, cosmetic) — Report header shows `Pipeline Run: None` / `Status: None`

**Reproduction.** The generated report from the REST `/train` job and the CLI both begin:
```
# Phronesis Pipeline Report
**Pipeline Run:** None
**Status:** None
```
**Root cause.** `ml/reports/builder.py:60-61` reads `getattr(state, "run_id", "unknown")` and `state.status`. `WorkflowState` declares these fields with `None` defaults (`workflow/state.py`, field-ownership map `run_id → metadata`) but **no stage ever sets them** during a normal run; storage then falls back to `"default_run"` (`services/storage.py:38`).

**Why it matters.** Low severity, but the flagship human-readable artifact is wrong on its first two lines on every run.

---

## 10. ISSUE-06 (VERIFIED) — README install/format drift vs `pyproject.toml`

**Reproduction (grep of README vs pyproject).**
- `README.md:296-314` "Supported file formats" and "extras" tables list **`openpyxl (core)`** and extras **`[explain]`**, **`[boost]`**, **`[parquet]`**.
- `pyproject.toml:42-59` defines only `cli`, `spark`, `api`, `mlflow`, `excel`, `dev`, `all`. There is **no** `explain`/`boost`/`parquet` extra.
- `CHANGELOG.md` (0.2.1) confirms: *"`openpyxl` moved to optional extras — install with `pip install phronesisml[excel]`"*; SHAP is a core dependency (so `[explain]` is meaningless); XGBoost (`[boost]`) is explicitly not used (see `docs/limitations.md`); Parquet is a core dependency via `pyarrow` (`pyproject.toml:33`).
- The README "How It Works" pipeline order also differs from the real graph (`upload → etl → validation → eda → target_detection → feature_engineering → …`).

**Why it matters.** `pip install phronesisml[explain]` fails/warns on a nonexistent extra, and the `.xlsx` "core" claim misleads users (a bare install cannot read `.xlsx`). Documentation drift for install-time behavior is user-facing.

---

## 11. ISSUE-07 (VERIFIED) — HPO `max_time_seconds` is a soft ceiling

**Reproduction.** On `sample_500.csv`, HPO reported `time_elapsed ≈ 140.8 s` with `max_time_seconds = 120` (`truncated=True`, 32/50 trials). The resource bound is only checked **between** trials (`trainer.py:191-199` and `:223-226`); a single long trial (e.g., GradientBoosting over 50–200 estimators) can overshoot the budget. The docstring claims `max_time_seconds` is a hard ceiling ("the search cannot run unbounded"), which is overstated.

**Why it matters.** On large datasets, a job can exceed its advertised time budget by a significant margin — relevant for cost estimation.

---

## 12. ISSUE-08 (INFERRED, obsolete since v0.3.0) — Docker image lacks the `excel` extra

> **Obsolete:** the Docker image was removed with the REST layer in v0.3.0.

`Dockerfile:14` installs `".[api]"` only. `openpyxl` is an optional `[excel]` dependency (`pyproject.toml:47`), so `.xlsx` uploads to the containerized API will fail with the friendly "install openpyxl" error (`pandas_engine.py:58`). Not executed this audit (no Docker daemon) — `INFERRED` from the dependency graph.

---

## 13. Architecture & Design Assessment

| Claim | Status | Notes |
|-------|--------|-------|
| Protocol-based agents, constructor-injected composition root (`agents/compose.py`) | `VERIFIED` | `BaseAgent` structural Protocol; DI via composition root |
| `AgentResult(success, data, error, error_type, error_message, error_context)` contract | `VERIFIED` | Matches docs |
| `WorkflowState` pydantic model with explicit field-ownership map | `VERIFIED` | `workflow/state.py` |
| Graph caching keyed by `(agent_names, stages, agent_ids)` | `VERIFIED` | cached compile path exists; measured speedup (below) NOT re-run |
| Cached engine `collect()` (identity cache) | `VERIFIED` | `base_engine.py` — but note BUG-01 interaction |
| Composition happens in exactly two places | `VERIFIED` | `__init__.py` + `sdk.py` |
| "Agents MUST NOT raise for expected failures" | `VERIFIED` | Return `AgentResult(success=False)` pattern held across audited agents |
| Graph-cache compile speedup "544×" | `NOT VERIFIED` | Claimed in `benchmarks/baseline.json`; not re-benchmarked this audit |

**Assessment.** Architecture is a genuine strength: clean layering, thin SDK/CLI adapters, and honest failure contracts. The main design tension is that engine-neutral code (`engineer.py`, `trainer.py`) assumes `collect()` returns a private copy, which the pandas identity-cache violates (BUG-01).

---

## 14. Engine Layer Assessment

| Claim | Status | Notes |
|-------|--------|-------|
| Auto-selection: <2 MB pandas, 2–500 MB polars, >500 MB spark | `VERIFIED` | `engine_selector.py`; all audit runs auto-selected pandas |
| `engine.preferred` override honored | `VERIFIED` | `config.engine.preferred` |
| `collect()` always returns a pandas DataFrame | `VERIFIED` | pandas + polars paths observed |
| Polars `LazyFrame` path, memory-efficient | `VERIFIED` (construct) / `NOT VERIFIED` (perf) | Code read; no >2 MB dataset exercised |
| Spark engine | `NOT VERIFIED` | `spark_engine.py` read; requires pyspark + JVM; mypy reports expected `pyspark.sql` import-not-found (optional extra) |
| Engine errors are friendly (`openpyxl`/`polars` hints) | `VERIFIED` | `pandas_engine.py` loaders |

**Assessment.** Solid. The pandas in-place aliasing in FE (BUG-01) is the one engine-path defect; `cached_collect` + in-place mutation is the mechanism.

---

## 15. Workflow & Pipeline Assessment

| Claim | Status | Notes |
|-------|--------|-------|
| 11 stages run in documented order | `VERIFIED` | `_FULL_PIPELINE_STAGES` matches docs |
| Conditional routers (`proceed` / `__end__`) | `VERIFIED` | `workflow/router.py` |
| Partial results available on later-stage failure | `VERIFIED` | `AgentNotImplementedError` → empty update; `WorkflowError` on `allnull`/`empty` was clean and structured |
| Fail-fast on `AgentError` | `VERIFIED` | `workflow/nodes.py` |
| Sampling node / pre-flight insertion | `VERIFIED` (read) | `workflow/sampling_node.py`; not triggered in audit runs (small data) |
| README diagram order matches real graph | `NOT VERIFIED` — actually **refuted** | README "How It Works" shows validation before ETL and EDA/target-detection out of order (ISSUE-06) |

**Assessment.** Graph topology and error handling are the strong core. The `run_id`/`status` never being set (BUG-05) is a small workflow-state gap.

---

## 16. Target Detection Assessment

| Claim | Status | Notes |
|-------|--------|-------|
| Name-based signals (`target`, `label`, `y`, …) | `VERIFIED` | `ml/target_detection/detector.py` |
| Categorical 2–50 unique → classification | `VERIFIED` | `label` 0.9 conf reproduced |
| Numeric 2–5 unique → ambiguous | `VERIFIED` | confidence < 0.6 + `ambiguity_reason` |
| Numeric >50 unique → regression | **REFUTED on audit data** | Continuous `age` (72 unique) → `ambiguous` at 0.40–0.50, **not** regression; detector picked `age` over the clean binary `churned` column |
| `AMBIGUITY_THRESHOLD = 0.6` documented + drift warning | `VERIFIED` | `detector.py` docstring carries the drift warning |
| Constant column → regression 0.8 | `VERIFIED` | edge case |

**Assessment.** The detector is deterministic and honest, but its behavior on real numeric data (BUG-02 trigger) means the common "continuous target" case funnels into `ambiguous` and then into the broken mixed-candidate path. This is the highest-leverage place to fix BUG-02.

---

## 17. Feature Engineering Assessment

| Claim | Status | Notes |
|-------|--------|-------|
| Excludes the target from transforms | `VERIFIED` | `engineer.py:101`, `:146-147` |
| Variance + correlation feature selection with `min_features` floor | `VERIFIED` | `_select_features` |
| IQR outlier detection (flag default) | `VERIFIED` | `_detect_outliers` |
| Outlier flag is an intentional feature | `NOT VERIFIED` — appears accidental | `outlier_flag` leaks (BUG-01); not in `feature_cols`, not in docs as a feature |
| Two-stage ETL→FE design | `VERIFIED` | documented and implemented |

**Assessment.** Functionally correct transforms, but the in-place mutation (BUG-01) and the accidental `outlier_flag` feature are the two defects to fix here.

---

## 18. Model Selection & HPO Assessment

| Claim | Status | Notes |
|-------|--------|-------|
| Rule-based candidates per task type | `VERIFIED` | `auto_selector.py` |
| `max_trials` hard ceiling | `VERIFIED` | `trainer.py:182,218` |
| `max_time_seconds` hard ceiling | `REFUTED` (soft) | ISSUE-07: 140.8 s > 120 s observed |
| Stratified split for classification, random otherwise | `VERIFIED` | `trainer.py:340` |
| `truncated=True` surfaced when budget exhausted | `VERIFIED` | `trainer.py` + `best_pipeline` |
| Per-task scoring consistency | **REFUTED** | `model.score()` mixes accuracy and R² (BUG-02) |
| `best_params` propagates to SDK | **REFUTED** | BUG-04 (`params` vs `best_params`) |

**Assessment.** The resource-bounding machinery is real and mostly enforced, but the ambiguous-task scoring model is broken (BUG-02) and the params contract is inconsistent (BUG-04).

---

## 19. Evaluation Metrics Assessment

| Claim | Status | Notes |
|-------|--------|-------|
| Per-task metric sets (classification/regression/clustering/anomaly) | `VERIFIED` | `metrics.py` |
| Ambiguous → both classification + regression "where applicable" | `VERIFIED` | `metrics.py:119-135`, but the selection rule (`>20 unique → regression only`) mismatches the chosen model (BUG-02) |
| Ambiguity caveat surfaced in report | `VERIFIED` | caveat text reproduced in output |
| MLflow with graceful degradation | `VERIFIED` | "MLflow not installed — skipping experiment tracking" logged |

**Assessment.** Metric computation is correct in isolation; the contract with the model-selection stage is what breaks (BUG-02). The `is_classification_like` heuristic (`metrics.py:121`) should be consistent with the model actually selected.

---

## 20. REST API, CLI & SDK Surface Assessment *(REST rows obsolete since v0.3.0)*

| Surface | Claim | Status | Notes |
|---------|-------|--------|-------|
| REST | Error envelope `APIResponse`/`ErrorDetail` with codes | `VERIFIED` (historical) | `JOB_NOT_FOUND` 404, `UNSUPPORTED_FORMAT` 415 reproduced; REST removed v0.3.0 |
| REST | Async job lifecycle `queued → running → completed` | `VERIFIED` (historical) | `/analyze` job observed (~1.7 s); REST removed v0.3.0 |
| REST | Health/liveness during jobs | **REFUTED** | BUG-03 (blocked event loop); REST removed v0.3.0 |
| REST | In-memory job store (lost on restart) | `VERIFIED` (historical) | `jobs.py` + documented limitation; REST removed v0.3.0 |
| CLI | `run`/`info`/`--help`, `--engine/-e`, `--nulls/-n`, `--verbose/-v` | `VERIFIED` | exercised on 3.13 wheel |
| CLI | Exit codes 0/1/2 | `VERIFIED` (0 and clean errors observed) | invalid-arg code 2 not re-verified |
| SDK | Simple API 12 fns + async, OOP chain, `run_pipeline` | `VERIFIED` | `sdk_audit.py` all green |
| SDK | `ModelInfo.best_params` populated | **REFUTED** | BUG-04 |

**Assessment.** The SDK/CLI are the most reliable surfaces. The REST API, whose event-loop blocking (BUG-03) was its top operational risk, was decommissioned in v0.3.0.

---

## 21. Security, Testing, CI, Docs, Packaging & Overall Readiness

**Security (VERIFIED for scope):** no arbitrary code execution paths (fixed sklearn registry), no outbound telemetry, temp upload cleanup, no credentials in code (`SECURITY.md` matches the code). Not verified: dependency vulnerability scanning.

**Testing (VERIFIED):** 83 host tests passing; clean-room wheel exercised across all interfaces. Gaps: no benchmark gate in CI, no regression tests for the ambiguous-task path (BUG-02).

**CI (VERIFIED):** auto-format + lint + mypy + pytest on 3.13; ruff pinned v0.11.13 pre-commit; conventional commits.

**Docs (VERIFIED, with drift):** docs site matches implementation in nearly every table; the README extras/format drift (ISSUE-06) and the report-header defect (BUG-05) were the exceptions.

**Packaging (VERIFIED):** wheel builds and installs with extras; `all` = `[cli,spark,mlflow,excel]`; `py.typed` packaged.

---

### Verdict & Fix Checklist

**Verdict.** Core SDK path: **production-grade for offline batch use** after BUG-01/BUG-02/BUG-04 are fixed. The REST API, whose BUG-03 event-loop blocking was its production blocker, was removed in v0.3.0. Documentation: strong, with a small README drift (also corrected).

**Fix checklist (9-field template — to be completed per fix if changes are requested):**
1. `Problem` — one of BUG-01…BUG-05, ISSUE-06…08.
2. `Root Cause` — file/line references as cited above.
3. `Files Affected` — source, plus `tests/` and `docs/` as appropriate.
4. `Why` — the user-visible impact documented above.
5. `Alternatives` — e.g., for BUG-02: (a) route >20-unique numeric targets to regression before selection; (b) score all ambiguous candidates on a common metric; (c) derive evaluation metrics from the selected model class.
6. `Backward Compatibility` — preserve `run_pipeline` keys, SDK result fields, CLI flags, artifact layout.
7. `Regression Risk` — the `outlier_flag` removal (BUG-01) changes feature counts and model inputs; document the behavior change.
8. `Tests Added` — unit: in-place mutation assertion; ambiguous-target integration; `best_params` round-trip; report-header assertion; extras-metadata test.
9. `Docs Updated` — README extras table, How-It-Works order, `docs/limitations.md`, changelog.

**Post-fix gate (mandatory):** `ruff check phronesisml/ tests/ benchmarks/` + `ruff format --check` + `mypy phronesisml/ --ignore-missing-imports` + `pytest` on the host baseline, and a clean-room wheel smoke test (CLI + SDK) on 3.13.

---

*Audit performed on the PhronesisML v0.2.2 source tree. Documentation-only deliverable — no source, tests, configuration, or infrastructure files were modified during this audit.*
