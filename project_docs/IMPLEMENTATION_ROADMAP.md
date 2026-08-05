# PhronesisML — Architecture Review & Implementation Roadmap (v0.2.2 → v1.0)

> **Deliverable type:** Documentation-only architecture review + implementation roadmap.
> **Version reviewed:** `0.2.2`
> **Date:** 2026-08-04
> **Repo:** `https://github.com/kartik00052/PhronesisML`
> **Evidence basis:** `AUDIT_REPORT.md` (21-section clean-room production audit), `PROJECT_KNOWLEDGE_BASE.md`, full source + docs read. Findings are referenced by their audit IDs (BUG-01…BUG-05, ISSUE-06…08).
> **Constitution compliance:** this roadmap is aligned with `INSTRUCTIONS.md` — SDK-first, offline-first, deterministic, transparent, modular, resource-aware; preserves LangGraph/`WorkflowState`/DI/composition-root/protocol-agents/engine abstraction (§6); introduces no mandatory cloud/LLM/GPU dependency (§5, §8); protects lazy imports, graph/engine caching, resource estimation, and pre-flight sampling (§9). Roadmap items that can change observable behavior are delivered **non-breaking (additive/opt-in) by default**; any genuinely breaking change requires explicit per-item approval (§17).
> **Boundaries honored:** no source, tests, configuration, or infrastructure files were modified. Every "current capability" claim below is grounded in code or a reproduced run; speculative items are explicitly labeled `Not verified`.

**Label legend:**
- `VERIFIED` — empirically reproduced/observed during the audit (host Python 3.11.9 and/or clean-room 3.13 wheel).
- `INFERRED` — established by reading code/configuration with high confidence, not executed at runtime.
- `NOT VERIFIED` — stated in docs/CI/metadata but not confirmed (out of scope or not re-run).

---

## 1. Executive Summary

PhronesisML v0.2.2 is a genuinely inspectable, offline-first **ML-engineering SDK** (11-stage LangGraph pipeline over a pandas/polars/spark engine abstraction, bounded HPO, SHAP explainability, Markdown/HTML reporting, local artifact storage). Its core SDK path is clean, deterministic, and passes its own gates: ruff clean, `mypy --ignore-missing-imports` clean, pytest 83/83, and a built wheel that installs and runs end-to-end on a clean Python 3.13 venv across CLI and SDK (REST also verified at the time; removed in v0.3.0).

It was **not yet production-safe** in three specific ways at audit time, all verified (items 1 and 3 are still relevant):

1. **Correctness contract on ambiguous targets is broken (BUG-02).** The pipeline can silently deliver a *classifier* for a continuous target and then report *regression* metrics (`rmse=28.92`, `r2=-0.81` on a logistic-regression model). This is the flagship defect and the highest-leverage Phase-1 fix.
2. **The REST API blocked its own event loop during jobs (BUG-03).** `/health` timed out for the full ~125 s of a `/train` job. *(Obsolete — the REST layer was removed in v0.3.0.)*
3. **Feature engineering mutates upstream workflow state (BUG-01)** and leaks an `outlier_flag` column into model features; plus two public-contract defects (BUG-04 `best_params` always `{}` through SDK/API, BUG-05 report header `None`) and one documentation issue (ISSUE-06 README drift). ISSUE-07 (soft HPO time ceiling) is still relevant; ISSUE-08 (Docker `[excel]`) is obsolete with the Docker image.

**Strategic recommendation.** Treat the next releases as: **Phase 1 — correctness hardening** (fix BUG-01…05 + ISSUE-06…08 with regression tests), **Phase 2 — beta surfaces** (schema/data-drift validation, model-recommendation with *why*, local experiment tracking, richer reporting), **Phase 3 — v1.0** (model registry, ONNX export, local serving, spark hardening). The roadmap below gives a ranked feature plan, breaking/non-breaking change taxonomy, concrete API/folder/LangGraph suggestions, and a release timeline. All priority-1 items are correctness fixes that preserve the public API.

---

## 2. Current Architecture Overview

**Layering (verified by reading the tree):**

```
phronesisml/
├── data/           loaders, transformers/cleaning, validators/checks, profilers/stats
├── utils/          dtypes and misc helpers
├── engines/        base_engine (cached collect), pandas, polars (LazyFrame), spark (local[*]), selector
├── agents/         12 protocol-based agents + compose.py composition root
├── ml/             preflight (sampler/memory/estimator), target_detection, task_detection,
│                   feature_engineering, automl (auto_selector, trainer), evaluation/metrics,
│                   explainability (service + shap_explainer), clustering, anomaly, reports
├── services/       storage (artifact layout), data_resolution
├── workflow/       state (pydantic + field-ownership map), graph (build + cache), router, nodes, sampling_node
├── interfaces/     cli/app
├── sdk.py          OOP Phronesis + run_pipeline
├── simple.py       simple 23-function API (sync + async)
└── _result_builders.py, _stages.py
```

**Key verified properties:**
- Protocol-based agents, constructor-injected composition root (`agents/compose.py`); composition happens in exactly two places (`__init__.py` + `sdk.py`).
- `AgentResult(success, data, error, error_type, error_message, error_context)` contract; "agents MUST NOT raise for expected failures" is held across audited agents.
- `WorkflowState` pydantic model with an explicit field-ownership map; graph caching keyed by `(agent_names, stages, agent_ids)`; cached-compile speedup claimed `544×` in `benchmarks/baseline.json` (`NOT VERIFIED` this audit — not re-benchmarked).
- Engine abstraction with auto-selection: **<2 MB pandas, 2–500 MB polars, >500 MB spark** (`engines/engine_selector.py`); `collect()` always returns a pandas DataFrame; polars path is memory-efficient (LazyFrame); spark defaults to `local[*]`.
- Engines are a genuine design strength **except** the pandas identity-cache interaction with in-place FE mutation (BUG-01).

**Design tension to carry into the roadmap.** Engine-neutral code (`engineer.py`, `trainer.py`) assumes `collect()` returns a private copy. The pandas identity-cache violates that assumption. Any future engine work must not deepen this aliasing trap.

---

## 3. Current Capabilities (verified)

| Capability | Status | Evidence |
|-----------|--------|----------|
| File ingestion: CSV, TSV, JSON, JSONL, XLSX, XLS, Parquet | `VERIFIED` | `data/loaders/`; XLSX/XLS need `[excel]` (openpyxl/xlrd); Parquet via pyarrow (core) |
| Excel sheet listing / best-sheet selection | `VERIFIED` | `list_excel_sheets`, `select_best_sheet` |
| ETL cleaning (nulls, types, dedup) + validation checks + profiling stats | `VERIFIED` | `data/transformers`, `data/validators`, `data/profilers` |
| Pre-flight resource checks + sampling (9 `SamplingMode`s; 50k/250k/1M row thresholds) | `VERIFIED` (read) | `ml/preflight/`; not triggered in audit runs (small data) |
| Target detection (name signals, cardinality heuristics, `AMBIGUITY_THRESHOLD=0.6` with drift warning) | `VERIFIED` | `ml/target_detection/detector.py` |
| Task detection (classification/regression/clustering/anomaly/ambiguous) | `VERIFIED` | `ml/task_detection/detector.py` (distinct module) |
| Feature engineering: null handling, encoding, scaling, variance+correlation selection, IQR outlier flag | `VERIFIED` (with BUG-01) | `ml/feature_engineering/engineer.py` |
| Rule-based model candidates per task type + bounded HPO (`max_trials` hard, `max_time_seconds` soft — ISSUE-07) | `VERIFIED` | `ml/automl/auto_selector.py`, `ml/automl/trainer.py` |
| Stratified split for classification, random otherwise | `VERIFIED` | `trainer.py:340` |
| Per-task evaluation metrics (classification/regression/clustering/anomaly); MLflow w/ graceful degradation | `VERIFIED` | `ml/evaluation/metrics.py` |
| SHAP explainability (tree/linear/permutation/kernel registry; max_samples=100, max_features=50, deterministic sampling) | `VERIFIED` | `ml/explainability/` |
| Clustering (KMeans/DBSCAN/Agglomerative, silhouette selection, max_k) + anomaly (isolation_forest/LOF, 10,000-row LOF cap) | `VERIFIED` | `ml/clustering/`, `ml/anomaly/` |
| Markdown + HTML report generation | `VERIFIED` (with BUG-05) | `ml/reports/builder.py` |
| Local artifact storage (`<base>/<run_id>/`) | `VERIFIED` | `services/storage.py` |
| Public surfaces: OOP SDK, 23-fn simple API (sync+async), `run_pipeline`, CLI (13 commands incl. `run`/`info`/`analyze`/`validate`/`train`/`evaluate`/`compare`/`explain`) | `VERIFIED` | `sdk.py`, `simple.py`, `interfaces/` |
| Packaging: wheel + extras (`cli/spark/mlflow/excel/dev/all`), `py.typed`; CI on 3.13 (format/lint/mypy/pytest) | `VERIFIED` | `pyproject.toml`, `.github/workflows/ci.yml` |
| Spark engine, MLflow active tracking | `NOT VERIFIED` | require pyspark+JVM / mlflow install, out of audit scope |

---

## 4. Current Tasks (implemented pipeline stages)

The graph runs **11 stages** in order (`workflow/graph.py`, `_FULL_PIPELINE_STAGES` — matches docs):

1. **upload** — file load, format detection, encoding
2. **etl** — cleaning: nulls, types, dedup
3. **validation** — data checks
4. **eda** — profiling stats
5. **target_detection** — pick target + task hint
6. **feature_engineering** — encode/scale/select/outlier flag (BUG-01)
7. **model_selection** — candidates → HPO → `best_pipeline` (BUG-02, BUG-04)
8. **evaluation** — per-task metrics + caveats (BUG-02)
9. **explainability** — SHAP explanations
10. **clustering** / **anomaly** — unsupervised tracks (routed conditionally)
11. **report** — Markdown/HTML artifact (BUG-05)

**Routing:** conditional routers (`proceed` / `__end__`, `workflow/router.py`); storage has no router; pre-flight/sampling node can be inserted (`workflow/sampling_node.py`); fail-fast on `AgentError`, partial results preserved on `AgentNotImplementedError` (`workflow/nodes.py`).

**CLI surface** (`phronesisml run <file>`, `phronesisml info`, plus `analyze`/`validate`/`profile`/`train`/`evaluate`/`explain`/`report`/`compare`/`version`/`capabilities`/`doctor`): exits 0 on success and clean `WorkflowError`; invalid-arg exit code 2 not re-verified.

---

## 5. Current Workflow (how a run flows end-to-end)

1. **User** invokes CLI `run`, SDK `Phronesis().run()`, or simple `train()`.
2. **Upload/ETL/Validation/EDA** stages produce `validated_data` + metadata in `WorkflowState`.
3. **Target detection** sets `target_column`, `task_type` (classification/regression/ambiguous/…), and a caveat when ambiguous.
4. **Feature engineering** produces `feature_cols` (BUG-01 aliasing + `outlier_flag` leak).
5. **Model selection** runs bounded HPO over the task's candidate pool and stores `best_pipeline` (BUG-04 key mismatch).
6. **Evaluation** computes metrics from `task_type` + target cardinality (BUG-02 metric/model mismatch) and optionally logs to MLflow (degrades gracefully).
7. **Explainability / clustering / anomaly** enrich `state`.
8. **Report** renders Markdown + HTML into the artifact store under `<base>/<run_id>/` (BUG-05 `run_id=None` → `"default_run"` fallback).
9. **Result builders** map `WorkflowState` → SDK result models (BUG-04 `{}` params).

**Operational caveats:** runs execute synchronously in-process; long pipelines occupy the calling thread/process.

---

## 6. Missing Features (gap analysis vs. the "honest, offline-first ML engineering" vision)

| Gap | Why it matters | Evidence |
|-----|----------------|----------|
| **Schema/constraint validation** (column types, ranges, allowed values) | `validation` stage checks data quality but not a declared schema; users can't enforce contracts | `data/validators/checks.py` |
| **Data versioning / lineage** | Artifact layout is `<base>/<run_id>/` but no content hashing, dataset registry, or provenance chain | `services/storage.py` |
| **Drift detection** (training vs. serving) | No concept of reference/current comparison anywhere | absent from code |
| **Model recommendation with a WHY** | Selection is rule-based; users get a model name but no plain-language rationale | `auto_selector.py` (rule tables only) |
| **User-configurable HPO search space** | `max_trials`/`max_time_seconds` exist; no per-model param grids | `trainer.py` |
| **Custom feature transformers / pipeline serialization** | FE is a fixed chain; no way to persist a trained pipeline for serving | `ml/feature_engineering/` |
| **Model registry / artifact versioning** | Only the latest `evaluation.json` + model dict in state; no versioned registry | `services/storage.py` |
| **Export formats** (ONNX, PMML) and saved model weights | Report + JSON only; no serialized estimator artifacts for deployment | `ml/reports/`, `services/storage.py` |
| **Local experiment tracking** | MLflow optional; no lightweight built-in run comparison | `ml/evaluation/metrics.py` (MLflow optional) |
| **Serving story** | Nothing beyond CLI/SDK local execution; no `serve` subcommand yet | — |
| **Benchmark gate in CI** | `benchmarks/` exist but are not enforced in CI | `.github/workflows/ci.yml` |

---

## 7. Weaknesses, Design Issues & Technical Debt

Prioritized (P1 = correctness, P2 = quality, P3 = ops):

- **P1 — BUG-02:** `ambiguous` task mixes 3 classifiers + 1 regressor in the candidate pool (`auto_selector.py:161-196`), scores them with `model.score()` (accuracy vs R² apples-to-oranges, `trainer.py:247-248`), sklearn silently fits multiclass on continuous targets, and `metrics.py:119-135` reports regression metrics for >20-unique targets regardless of the selected model class. **Reproduced end-to-end** (classifier with `r2=-0.81`). *The signature defect.*
- **P1 — BUG-01:** in-place mutation of `validated_data` via identity-cached `collect()` (`engineer.py:98,183,186,210,235,274`); `outlier_flag` leaks into features (`engineer.py:146-148` drops only target). Pandas/polars engines behave differently for the same logical operation.
- **P1 — BUG-03 (obsolete since v0.3.0):** REST CPU-bound jobs blocked the event loop (`jobs.py:120`, `routes.py:478-490`); `/health` unresponsive during jobs. The REST layer was removed in v0.3.0.
- **P2 — BUG-04:** `best_pipeline["params"]` vs readers `get("best_params", {})` → HPO params always `{}` through SDK/API (`sdk.py:645`, `_result_builders.py:177,208`).
- **P2 — BUG-05:** `run_id`/`status` never populated in `WorkflowState` → report header `None` (`builder.py:60-61`).
- **P2 — ISSUE-07:** `max_time_seconds` is a soft ceiling (140.8 s observed vs 120 s configured); docstring overstates it as a hard bound.
- **P3 — ISSUE-06:** README extras (`[explain]`/`[boost]`/`[parquet]`), `openpyxl (core)`, and "How It Works" order drift vs `pyproject.toml` and the real graph (fixed in working tree).
- **P3 — ISSUE-08 (obsolete since v0.3.0):** Docker installed `".[api]"` only → `.xlsx` failed in the container (`INFERRED`). Docker image removed in v0.3.0.
- **P3 — Test gaps:** no regression tests for BUG-02 path, no benchmark gate in CI.
- **P3 — Strict-mypy debt:** 34 errors without `--ignore-missing-imports` (third-party stubs + `pyspark.sql` import-not-found).
- **Not verified risks:** Spark path, MLflow active path, "544×" graph-cache benchmark.

---

## 8. Improvement Opportunities

High-leverage, non-breaking where possible:

1. **Fix ambiguity resolution at the detector/selector boundary** — the single highest-value change (kills BUG-02 for the common continuous-target case). Options: (a) route >20-unique numeric targets to regression before selection; (b) score all ambiguous candidates on a common, task-appropriate metric; (c) derive evaluation metrics from the *selected model class*.
2. **Make `collect()`'s aliasing contract explicit and safe** — engine-neutral defensive copy in `engineer_features()`; decide whether `outlier_flag` is a feature or metadata (currently accidental).
3. ~~**Move REST jobs off the event loop** — superseded: REST removed in v0.3.0 (BUG-03).~~
4. **Normalize the `best_pipeline` schema** — single writer + readers (`params` vs `best_params`), with a round-trip test (BUG-04).
5. **Populate `run_id`/`status` from a single stage** (e.g., upload or a new run-metadata agent) (BUG-05).
6. **Add a schema-validation agent + `validate_schema()` public function** (feature request from §6).
7. **Add a "model recommendation rationale" block** to evaluation/report (plain-language WHY).
8. **Add data-drift check API** (`reference` vs `current` frames) reusing the existing profiler/metrics machinery.
9. **Add built-in lightweight run ledger** (compare last N runs) with MLflow still optional.
10. **Harden HPO timing** — per-trial deadline or interruptible fit so `max_time_seconds` is a hard ceiling (ISSUE-07).
11. **Pin extras in README** (ISSUE-06).
12. **Add a benchmark gate to CI.**

---

## 9. New Modules (proposed)

| Proposed module | Purpose | Reuses |
|-----------------|---------|--------|
| `phronesisml/ml/schema/` | Declared-schema validation (types/ranges/constraints) + `validate_schema()` public fn | `data/validators`, `data/profilers`, `utils/dtypes` |
| `phronesisml/ml/drift/` | Reference-vs-current distribution drift detection | `data/profilers/stats`, `ml/evaluation/metrics` |
| `phronesisml/ml/recommend/` | Model-recommendation engine producing candidates **with plain-language rationale** | `auto_selector`, `task_detection` |
| `phronesisml/ml/experiments/` | Local run ledger (compare last N runs); MLflow stays optional | `services/storage`, report builders |
| `phronesisml/interfaces/serve/` | Minimal local serving entry (load saved pipeline → predict) | future pipeline serialization |
| `phronesisml/ml/export/` | ONNX / versioned-pipeline export | `ml/automl/trainer` best model |

---

## 10. Ranked Feature List (Impact × Difficulty)

Scoring: Impact 1–5 (user value), Difficulty 1–5 (effort/risk). Ranked by Impact ÷ Difficulty.

| # | Feature | Impact | Difficulty | Phase | Notes |
|---|---------|--------|-----------|-------|-------|
| 1 | Fix ambiguous-task contract (BUG-02) | 5 | 2 | P1 | Detector+selector+metrics alignment |
| 2 | Defensive copy + `outlier_flag` decision (BUG-01) | 4 | 1 | P1 | Behavior change: feature counts |
| 3 | ~~Move REST jobs off event loop (BUG-03)~~ | ~~5~~ | ~~2~~ | ~~P1~~ | ~~Completed, then superseded — REST removed v0.3.0~~ |
| 4 | `best_params` round-trip (BUG-04) | 3 | 1 | P1 | Key normalization + test |
| 5 | Populate `run_id`/`status` (BUG-05) | 2 | 1 | P1 | Single stage sets both |
| 6 | Hard HPO time ceiling (ISSUE-07) | 3 | 2 | P1 | Per-trial deadline |
| 7 | README + Docker extras fix (ISSUE-06/08) | 2 | 1 | P1 | Docs (ISSUE-06); Docker obsolete v0.3.0 |
| 8 | Schema/constraint validation + public fn | 4 | 3 | P2 | New `ml/schema` |
| 9 | Model recommendation with WHY | 4 | 3 | P2 | New `ml/recommend` |
| 10 | ~~Durable job store + worker pool~~ | ~~4~~ | ~~4~~ | ~~P2~~ | ~~Obsolete — REST removed v0.3.0~~ |
| 11 | Data-drift check API | 3 | 3 | P2 | New `ml/drift` |
| 12 | Local run ledger / experiment compare | 3 | 3 | P2 | New `ml/experiments` |
| 13 | More report formats (PDF, structured JSON schema) | 2 | 2 | P2 | Extend `ml/reports` |
| 14 | Pipeline serialization + local serving | 4 | 4 | P3 | Prereq for deployment |
| 15 | ONNX export + model registry | 4 | 4 | P3 | New `ml/export` + storage extension |
| 16 | User-configurable HPO grids | 3 | 3 | P3 | Extend `trainer` |
| 17 | ~~REST auth / rate limiting~~ | ~~3~~ | ~~3~~ | ~~P3~~ | ~~Obsolete — REST removed v0.3.0~~ |
| 18 | Spark scale-out hardening + benchmarks | 3 | 4 | P3 | Needs JVM/pyspark CI |

---

## 11. Behavior-Affecting Changes (non-breaking by default; breaking only with explicit approval)

Per `INSTRUCTIONS.md` §8/§17, the Simple/OOP/Advanced SDK, CLI, return types, config models, and PyPI install must not break unless explicitly requested. Every item below is therefore **delivered non-breaking (additive/opt-in) by default**; only the two bug-fix *behavior* corrections (1 and 2) inherently change results for datasets that hit those bugs, and each is flagged in release notes. Any item marked *breaking* requires explicit per-item approval before landing.

1. **`outlier_flag` treatment (BUG-01 fix) — behavior correction.** If decided to be *metadata*, model feature counts and trained inputs change for datasets with outliers (they were trained on a leaked column). Delivered via an **opt-in config flag** (`include_outlier_flag: bool = False`), preserving current behavior for existing users until they opt in; `feature_cols`/`feature_metadata` documented.
2. **Task resolution for continuous targets (BUG-02 fix) — behavior correction.** Datasets whose `ambiguous` runs today produce a wrong classifier+regression-metrics pair will instead produce a correct, consistent model. This is the intended bug fix and does not change any public API surface.
3. **`best_pipeline` schema normalization (BUG-04 fix) — non-breaking.** Writer emits **both** `params` and `best_params` during a deprecation window; readers prefer `best_params` with `params` fallback. SDK/API response fields unchanged.
4. **`run_id` semantics (BUG-05 fix) — non-breaking.** Explicit `run_id`/`tags` are added as *optional* inputs; the `"default_run"` fallback stays so artifact paths remain deterministic for existing callers.
5. **Python support policy (Phase 3) — documentation-level.** Declares the supported matrix; no code change; any future drop of an interpreter is separately announced. *(would be breaking only for unlisted interpreters)*

---

## 12. Non-Breaking Changes

The bulk of the roadmap is additive and contract-stable:

- All BUG-01…05 / ISSUE-06…08 fixes that preserve `run_pipeline` keys, SDK result fields, CLI flags, and artifact layout.
- New optional public functions: `validate_schema()`, `check_drift()`, `compare_runs()`, `explain_models()` (recommendation rationale).
- New agents inserted via the existing routing table (composition-root-only wiring, no API change).
- New report formats, new `SamplingMode`s, new explainer kinds, new candidate models — all additive behind existing keys.
- README corrections, CI additions (benchmark gate), stricter mypy via `# type: ignore[import-untyped]` on third-party stubs.
- Schema-typed result models with `extra="ignore"` so older clients tolerate new fields.

---

## 13. Folder Structure Suggestions

Current layout is good; evolve, don't reshuffle:

```
phronesisml/
├── data/                  (unchanged)
├── engines/               (unchanged)
├── agents/                (+ new agent files for schema/drift/experiments via compose.py)
├── ml/
│   ├── preflight/         (unchanged)
│   ├── target_detection/  (unchanged)
│   ├── task_detection/    (unchanged)
│   ├── feature_engineering/   (+ pipeline serialization later)
│   ├── automl/            (auto_selector, trainer)
│   ├── evaluation/        (metrics)
│   ├── explainability/    (unchanged)
│   ├── clustering/  anomaly/  (unchanged)
│   ├── reports/           (unchanged)
│   ├── schema/            NEW — declared-schema validation
│   ├── drift/             NEW — reference-vs-current checks
│   ├── recommend/         NEW — model rationale
│   └── experiments/       NEW — local run ledger
├── services/
│   ├── storage.py         (+ registry paths: <base>/models/, <base>/runs/)
│   └── data_resolution.py (unchanged)
├── workflow/              (unchanged)
├── interfaces/
│   ├── cli/               (unchanged)
│   └── serve/             NEW — minimal local serving entry (Phase 3)
├── sdk.py  simple.py  _stages.py  _result_builders.py  (unchanged public names)
tests/
  + test_regressions.py    NEW — BUG-01…05 paths
benchmarks/                (+ gate script wired into CI)
```

---

## 14. Public API Surface Suggestions

Keep everything existing; add a small, coherent set:

- `Phronesis.run(...)` / `run_pipeline(...)` — unchanged signatures (P1 fixes only touch internals).
- New module `phronesisml.validate` (simple-API style):
  - `validate_schema(df, schema: dict) -> ValidationReport`
  - `infer_schema(df) -> dict`
- New module `phronesisml.drift`:
  - `check_drift(reference, current, features=...) -> DriftReport`
- New module `phronesisml.compare`:
  - `compare_runs(run_ids=[...]) -> RunComparison`
- Extend `ModelInfo`/`ModelResult` with `rationale: str | None` (recommendation WHY) and `pipeline: PipelineArtifact | None` (Phase 3).
- Add `run_id` (and optional `tags`) to `Phronesis.run()` — overrides default so artifact paths are predictable.
- Versioned, typed response models with `extra="ignore"` for forward compatibility.

**Contract stability rule for v1.0:** once a field ships in the SDK/API envelope, it is frozen; new fields are additive-only.

---

## 15. LangGraph Agent Architecture Suggestions

The current `BaseAgent` protocol + composition root + conditional routing is already idiomatic and healthy. Suggested evolution:

1. **Make routing data-driven.** Extend `_STAGE_ROUTERS` to a declarative table `(stage → next stage | condition fn | tool call)`; keep `router.py` generic. Storage gets a router so post-run artifacts trigger off the graph (kills the "storage has no router" gap).
2. **Add a run-metadata agent** (id, started/completed timestamps, status) that runs first and sets `run_id`/`status` in `WorkflowState` — fixes BUG-05 at the source.
3. **Add supervised (schema, drift, recommend, experiments) and unsupervised (clustering/anomaly) tracks** as subgraphs composed at the root; each exposes the same `AgentResult` envelope so failure semantics stay uniform.
4. **Formalize the cache key.** Document that graph caching is keyed by `(agent_names, stages, agent_ids)`; add a cache-invalidation test and a CI benchmark so the claimed `544×` speedup is re-measured and gated.
5. **Interruptible/checkpointable runs (Phase 3).** Use LangGraph checkpointing (where cheap) so a failing report stage can resume from the last good stage — preserves "partial results on later-stage failure" today, adds durability.

---

## 16. SDK Suggestions

- Fix `best_params` propagation (BUG-04) and add a unit test asserting round-trip equality with the on-disk `evaluation.json`.
- Surface `run_id`, `status`, and `rationale` in result models (BUG-05 + §14).
- Add `Phronesis.run(..., run_id=..., tags=...)` and a `phronesisml.compare.compare_runs()` companion.
- Keep the **simple API 23 functions** stable; add `validate_schema`/`check_drift` in the same style (sync + async twins).
- Add typing improvements: strict-mypy-friendly annotations with targeted `type: ignore[import-untyped]` for pandas/sklearn/psutil stubs.
- Document the engine-choice knobs (`engine.preferred`, engine-selector thresholds) in SDK docstrings.

---

## 17. REST API Suggestions *(superseded — REST removed in v0.3.0)*

The REST subsystem was decommissioned in v0.3.0; PhronesisML is SDK-first and CLI-first.
If a remote surface is ever reconsidered, prior suggestions were:

- **P1:** Offload pipeline execution with `asyncio.to_thread` (then a process-pool worker queue in P2) so `/health` never blocks (BUG-03). Add a concurrency probe test (submit long job, assert `/health` < 1 s).
- **P2:** Durable job store (SQLite or filesystem-backed) preserving the existing `/jobs/{id}` envelope; job retention + cleanup policy.
- **P2:** Request size/count limits, configurable allowed extensions (already `ALLOWED_EXTENSIONS`), and optional token auth + rate limiting for containerized deployment.
- **P3:** Model-serving endpoint (`POST /predict`) once pipelines are serializable; OpenAPI document frozen at v1.0.

---

## 18. CLI Suggestions

- Keep `run`/`info` and flags `--engine/-e`, `--nulls/-n`, `--verbose/-v` stable.
- Add: `--run-id`, `--schema <json>` (validates via §14 `validate_schema`), `--compare <run_ids...>`, `--export onnx|json`, and `--tags`.
- Standardize exit codes (0 success / 1 runtime+structured errors / 2 usage) and document them (`README` + `--help` epilog).
- Add `phronesisml serve` (Phase 3) as the local serving entry.

---

## 19. Production-Readiness Review

From `AUDIT_REPORT.md` §21 (verdict + fix checklist):

- **Core SDK path:** production-grade for offline batch use **after** BUG-01/BUG-02/BUG-04 are fixed.
- **Interfaces:** SDK and CLI are the canonical surfaces; the REST layer (the only surface that was not production-ready, BUG-03) was removed in v0.3.0.
- **Blockers to v1.0:** BUG-01…02 + the missing regression tests for those paths; a benchmark gate in CI; strict-mypy cleanup; README drift.
- **Security (verified for scope):** no arbitrary-code-execution paths (fixed sklearn registry), no telemetry, temp-upload cleanup, no secrets in code. Not verified: dependency vulnerability scanning.
- **Post-fix gate (from the audit, mandatory per change):** `ruff check phronesisml/ tests/ benchmarks/` + `ruff format --check` + `mypy phronesisml/ --ignore-missing-imports` + `pytest`, then a clean-room wheel smoke test (CLI + SDK) on 3.13.

---

## 20. Future Possibilities

Beyond v1.0, all additive, clearly separated by value, and consistent with the constitution (§20 final rule: deterministic, offline, resource-aware ML-engineering SDK).

**In-scope candidates:**

- **AutoML ensembling / stacking** on top of the per-task candidate pools (reuses `auto_selector` + `trainer`).
- **Pipeline explainability at the feature level** (SHAP dependence/partial-dependence plots) — natural extension of the existing `_EXPLAINER_REGISTRY`.
- **Spark/Dask scale-out benchmarks + memory regression suite** to justify the >500 MB engine path.
- **GitOps-friendly CI artifacts** (publish wheels + SBOM + vulnerability scan per release).
- **Distributed/ray execution** only if the worker pool in §17 proves the demand.

**Explicitly out of scope** (do not pass the §20 final rule / conflict with §8): multimodal ingestion (audio/image), vector-store/RAG tie-in, and any feature requiring a mandatory LLM, cloud, or GPU dependency.

---

## 21. Release Roadmap Overview

| Phase | Version target | Theme | Contents (by ID) |
|-------|----------------|-------|-------------------|
| Phase 1 | 0.3.x | Correctness hardening | BUG-01…05, ISSUE-06…08 + regression tests, CLI test suite, post-fix gate |
| Phase 2 | 0.4.x–0.5.x | Beta surfaces | Schema, recommend-with-WHY, drift, local run ledger, extra reports, README/API polish |
| Phase 3 | 1.0 | v1.0 ship | Pipeline serialization, local serving, ONNX + model registry, spark hardening, frozen API contract |

Each phase ends with: full toolchain green (ruff/format/mypy/pytest), clean-room wheel smoke test, `CHANGELOG.md` entry, docs sync (README + `docs/` + mkdocs).

---

## 22. Phase 1 — Stabilization & Correctness (target 0.3.x)

Milestone: **no known correctness bugs in the SDK core; SDK/CLI surfaces fully reliable.**

1. **BUG-02 — ambiguous-task contract.** Resolve ambiguity upstream (route >20-unique numeric targets to regression before selection) *and* make evaluation derive metrics from the selected model class; add integration test: continuous target → regressor → regression metrics, never classifier-with-regression-metrics.
2. **BUG-01 — defensive copy.** Engine-neutral copy in `engineer_features()`; decide `outlier_flag` = metadata (excluded from `feature_cols`); add an in-place-mutation assertion test; document the feature-count behavior change.
3. **BUG-03 — off the event loop.** *(Completed, then superseded: the REST layer was removed in v0.3.0.)*
4. **BUG-04 — params round-trip.** Normalize `best_pipeline` key; add round-trip test vs `evaluation.json`.
5. **BUG-05 — run metadata.** Run-metadata agent sets `run_id`/`status`; report header test.
6. **ISSUE-07 — hard time ceiling.** Per-trial deadline in `trainer.py`; adjust docstring to the actual contract.
7. **ISSUE-06 — README drift.** Extras tables, `openpyxl` claim, "How It Works" order.
8. **ISSUE-08 — Docker extras.** *(Obsolete — Docker image removed in v0.3.0.)*
9. **Testing/CI.** `tests/test_regressions.py` (BUG-01…05), benchmark gate script, mypy stub-ignores to cut the 34 strict errors.
10. **Gate.** Audit §21 post-fix gate + clean-room wheel smoke test.

---

## 23. Phase 2 — Beta Features & Surfaces (target 0.4.x–0.5.x)

Milestone: **users can validate, explain, and compare with confidence.**

1. **Schema validation** — `phronesisml.validate` module + `validate_schema()`/`infer_schema()` public functions; new schema agent wired via composition root.
2. **Model recommendation with WHY** — `ml/recommend`; `ModelInfo.rationale`; plain-language block in the report.
3. **Data-drift API** — `phronesisml.drift.check_drift()`; reuses profiler/metrics machinery.
4. **Local run ledger** — `ml/experiments` + `compare_runs()`; MLflow stays optional.
5. **Reporting** — PDF and structured-JSON report variants (additive).
6. **HPO UX** — expose configurable grids (non-breaking; additive to `trainer`).
7. **Docs & packaging** — docs site sync for every new module; `mkdocs` nav update.

---

## 24. Phase 3 — v1.0 and Beyond

Milestone: **deployable end-to-end with a frozen public contract.**

1. **Pipeline serialization** — persist the trained FE+model pipeline; versioned artifacts under `storage` registry paths.
2. **Local serving** — `phronesisml serve`; CLI is the deployment story.
3. **ONNX export + model registry** — `ml/export`; registry paths `<base>/models/<run_id>/`.
4. **Spark scale-out hardening** — JVM/pyspark CI job, memory regression suite, >500 MB benchmark.
5. **Python support policy + strict mypy** — declared matrix; zero strict-mypy errors via targeted stub ignores.
6. **CI release pipeline** — wheel build + SBOM + vulnerability scan + PyPI publish (extends the existing 3.13 matrix).
7. **v1.0 freeze** — public API contract frozen; additive-only thereafter; 1.0 release notes + migration guide.
8. **Beyond 1.0** — ensembling/stacking, per-feature explanation plots, distributed execution only on demonstrated demand (§20).

---

*Roadmap produced from the PhronesisML v0.2.2 source tree and the verified audit findings. Documentation-only deliverable — no source, tests, configuration, or infrastructure files were modified.*
