# Phronesis ML — Full-Stack Audit Findings

**Audit date:** 2026-11-14
**Audit base commit:** `b113652` (`fix(engines): decode non-UTF-8 CSV/TSV uploads and add sample datasets`)
**Scope:** backend ↔ frontend connectivity, CORS, API/schema contracts, pandas/engine behavior, LangGraph & agentic workflows, uploads, runs, artifacts, config, deployment.
**Live targets:** backend `https://phronesisml-backend.onrender.com` (v0.3.1), frontend `https://frontend-snowy-nine-40.vercel.app`.

**Legend — Severity**
- **P1 / High** — user-visible broken feature or correctness bug.
- **P2 / Medium** — wrong/degraded output, silent no-op, or inconsistency with real impact.
- **P3 / Low** — latent risk, cosmetic, type-only, or ops note.
- **INFO** — verified-good or informational; no action.

**Status tags:** `[FIXED]` applied this session · `[OPEN]` not yet changed · `[OPS]` dashboard/infra action · `[INFO]` no action · `[VERIFY]` reported, needs confirmation.

---

## 0. Summary

| ID | Severity | Area | Status |
|----|----------|------|--------|
| C1 | P1 | Report builder — validation section empty | FIXED |
| C2 | P1 | Report builder — EDA section missing rows/cols | FIXED |
| C3 | P1 | Report builder — model-selection shows "Candidate N" | FIXED |
| F1 | P2 | Frontend accepts `.txt`, backend rejects (415) | FIXED |
| C4 | P2 | Preflight cardinality checks are silent no-ops (key mismatch) | OPEN |
| C5 | P2 | Numeric-target ID check no-op (missing `n_unique`) | OPEN |
| C10 | P2 | Sampling/encoded-feature estimate undercounts one-hot expansion | OPEN |
| C6 | P2 | `data.max_file_size_bytes` not wired into SDK `run_pipeline` | OPEN |
| C8 | P2 | `fillna(None)` raises when `null_strategy="fill"` w/o value | OPEN |
| C7 | P3 | Preflight-blocker router branch is effectively dead | OPEN |
| F2 | P3 | `ModelRankingRow.status` union missing `"candidate"` | FIXED |
| F3 | P3 | WS base URL defaults to localhost only | OPEN |
| C9 | P3 | Spark path unusable for >500 MB (always collects to pandas) | OPEN |
| F4 | P3 | Backend rejects formats the loader supports (`.pq/.ndjson/.feather/.arrow`) | INFO |
| O1 | OPS | Sample datasets not seeded on Render until `SEED_SAMPLE_DATASETS=1` | OPS |
| O2 | OPS | Render free tier wipes uploads/runs/artifacts on redeploy | OPS |
| O4 | OPS | Rotate the PAT used for push | OPS |
| V1–V6 | INFO | Connectivity/CORS/upload/run/artifact checks passed | INFO |

---

## 1. Changes Already Applied (this session)

Three files modified (currently **uncommitted**, see `git status`):

1. **`phronesisml/ml/reports/builder.py`** — report content fixes
   - `_build_validation_section`: now reads the real `validate_dataframe` keys
     (`passed`, `shape`, `duplicate_rows`, `null_columns`, `empty_columns`) while
     still supporting a legacy `checks` list if present.
   - `_build_eda_section`: now reads `shape.rows` / `shape.columns` (profiler output),
     plus `numeric_columns` / `categorical_columns`, keeping legacy `n_rows`/`n_cols`
     fallbacks.
   - `_build_model_selection_section`: now reads `name` (from `candidate_to_dict`)
     as well as `model_type`, and `score` as well as `mean_cv_score`.
   - **Verification:** unit check printed correct output for validation/EDA/model
     sections; `pytest tests/test_interfaces.py tests/test_run_report.py tests/test_report_io.py` → all pass.

2. **`frontend/src/components/datasets/upload-dataset-dialog.tsx`** — removed `.txt`
   from `ACCEPT` so the picker matches backend `ALLOWED_EXTENSIONS`
   (`.csv,.tsv,.xlsx,.xls,.parquet,.json,.jsonl`).

3. **`frontend/src/types/model.ts`** — added `"candidate"` to
   `ModelRankingRow["status"]` union to match the backend value emitted by
   `model_service._row_to_rank`.

> Note: the report builder is the function the backend actually uses for a run's
> `report.md`/`report.html` (`backend/app/workers/runner.py:438`,
> `phronesisml/services/storage.py:343-347`), so C1–C3 were user-visible in the
> run Report tab.

---

## 2. Findings — Frontend

### F1 — `.txt` offered by UI but rejected by backend `[FIXED]` (P2)
- **Files:** `frontend/src/components/datasets/upload-dataset-dialog.tsx:20` (`ACCEPT`),
  `backend/app/services/dataset_service.py:22` (`ALLOWED_EXTENSIONS`),
  `phronesisml/data/loaders/file_loader.py:27-33` (`_FORMAT_EXTENSIONS`).
- **Problem:** `ACCEPT` included `.txt`; neither backend allow-list nor loader
  format map supports it → HTTP 415 `UnsupportedFormat`.
- **Fix applied:** removed `.txt` from `ACCEPT` (minimal alignment; no new backend behavior).
- **Alternative (needs decision):** add `.txt` support to backend allow-list + loader
  (tab/comma delimited) instead. See "Decisions Needed".

### F2 — `ModelRankingRow.status` union missing `"candidate"` `[FIXED]` (P3)
- **Files:** `backend/app/services/model_service.py:75` emits `status:"candidate"`;
  `frontend/src/types/model.ts:103` union was `"ready"|"running"|"failed"`.
- **Impact:** type-only. `run-models.tsx:41-42` only branches on `"running"`/`"failed"`,
  so no runtime crash; non-best scored rows simply render no badge.
- **Fix applied:** added `"candidate"` to the union.

### F3 — WebSocket base URL defaults to localhost only `[OPEN]` (P3)
- **File:** `frontend/src/api/websocket.ts:30-35`.
- **Problem:** if `VITE_WS_BASE_URL` is unset, it falls back to
  `ws://localhost:8000/api/v1`. It does **not** derive the WS origin from
  `VITE_API_BASE_URL`.
- **Impact:** currently **mitigated** — `VITE_WS_BASE_URL` is set on Vercel and the
  deployed bundle contains the backend host (verified). Latent risk if the env var is
  ever dropped.
- **Suggested fix (low risk):** fall back to `import.meta.env.VITE_API_BASE_URL`
  (http→ws) before the localhost default.

### F4 — Backend rejects formats the loader supports `[INFO]` (P3)
- **Files:** `file_loader.py:27-33` supports `.pq`, `.ndjson`, `.feather`, `.arrow`;
  `dataset_service.py:22` `ALLOWED_EXTENSIONS` omits them.
- **Impact:** none today — the UI doesn't offer those either. Informational only.

### F5 — HTTP API contract `[INFO]` (P1-check)
- All frontend calls in `frontend/src/api/*.ts` resolve to existing backend routes with
  correct methods. WebSocket path `/api/v1/ws/runs/{runId}` matches. **No mismatch.**

---

## 3. Findings — Backend / API

### B1 — Report sections empty/degraded `[FIXED]` — see C1–C3 (P1)
The run Report tab is rendered from `report.md`/`report.html`, both produced via
`phronesisml/ml/reports/builder.py`. Key mismatches made sections empty. Fixed above.

### B2 — Live dataset list empty on Render `[OPS]` (P2)
- **Files:** `backend/app/config.py` (seed flag), `dataset_service.BUNDLED_SAMPLES`.
- **Problem:** samples are seeded only when `SEED_SAMPLE_DATASETS == "1"`, which is a
  Render dashboard env var, not repo config. Until set, `/api/v1/datasets` returns `[]`.
- **Action:** set `SEED_SAMPLE_DATASETS=1` in the Render dashboard (see Ops).

### B3 — CORS `[INFO]` (verified good)
- Live `OPTIONS /api/v1/datasets` with `Origin: https://frontend-snowy-nine-40.vercel.app`
  returned `200` with:
  `access-control-allow-origin: https://frontend-snowy-nine-40.vercel.app`,
  `access-control-allow-credentials: true`,
  `access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT`,
  `access-control-allow-headers: content-type,authorization`. No change needed.

### B4 — Health/version `[INFO]`
- `GET /api/v1/health` → `200`, version `0.3.1`.

---

## 4. Findings — Core Pipeline / ML / Workflow

### C1 — Validation report section always empty `[FIXED]` (P1)
- **File:** `phronesisml/ml/reports/builder.py` `_build_validation_section`.
- **Root cause:** read `report["checks"]`, but `validate_dataframe`
  (`phronesisml/data/validators/checks.py:47-87`) returns
  `shape`, `dtypes`, `column_names`, `null_counts`, `null_columns`, `empty_columns`,
  `duplicate_rows`, `passed` — there is no `"checks"` key.
- **Effect:** rendered `_No validation checks recorded._`.
- **Fix:** read the real keys (kept `checks` support for compatibility).

### C2 — EDA report section missing rows/columns `[FIXED]` (P1)
- **File:** `builder.py` `_build_eda_section`.
- **Root cause:** read `n_rows`/`n_cols`/`null_percentage`; profiler
  (`phronesisml/data/profilers/stats.py:55-64`) emits `shape:{rows,columns}`,
  `numeric_columns`, `categorical_columns`, `dtypes`, no `null_percentage`.
- **Effect:** only "Column Types: N columns" appeared.
- **Fix:** read `shape.rows`/`shape.columns` + numeric/categorical counts, legacy fallbacks kept.

### C3 — Model-selection section shows "Candidate N" `[FIXED]` (P1)
- **Files:** `builder.py` `_build_model_selection_section` vs
  `phronesisml/ml/automl/auto_selector.py:347-354` `candidate_to_dict`.
- **Root cause:** reader used `c.get("model_type")` and `c.get("mean_cv_score")`;
  candidates are serialized with only `name`, `estimator_path`, `param_space`, `tags`.
- **Effect:** every candidate rendered as `Candidate 1`, `Candidate 2`, … and no scores.
- **Fix:** read `name`/`score` with `model_type`/`mean_cv_score` fallbacks.

### C4 — Preflight cardinality checks are silent no-ops `[OPEN]` (P2)
- **Files:** `phronesisml/ml/target_detection/detector.py:431, 444, 458, 489`
  (and `phronesisml/ml/preflight/estimator.py:179`).
- **Root cause:** readers do `summary.get("n_unique", 0)`, but the profiler
  (`stats.py:98-117`) emits `cardinality` for categorical summaries and
  `_profile_numeric` (`stats.py:74-95`) emits no `n_unique` at all.
- **Effect:** high-cardinality categorical detection, target-ID blocker, and the
  one-hot memory estimate always see `0` → checks silently pass / undercount.
- **Suggested fix (see plan):** make the profiler the single source of truth by adding
  an `n_unique` field to both `_profile_categorical` and `_profile_numeric` (keeping
  `cardinality` for compatibility), rather than editing many readers.

### C5 — Numeric-target ID check no-op `[OPEN]` (P2)
- **File:** `detector.py:457-464`.
- **Root cause:** same as C4 — `profile_numeric[...].get("n_unique")` never exists.
- **Fix:** resolved by the C4 profiler change.

### C10 — Sampling ignores one-hot expansion `[OPEN]` (P2)
- **Files:** `phronesisml/workflow/sampling_node.py:87-98`,
  `phronesisml/ml/preflight/estimator.py:166-185`.
- **Root cause:** same key mismatch (`n_unique` vs `cardinality`) → `estimated_new_features`
  is ~0, so `requires_sampling`/memory estimates undercount categorical blow-up.
- **Fix:** resolved by the C4 profiler change; add a regression test for a wide-cardinality frame.

### C6 — `data.max_file_size_bytes` not enforced by SDK `run_pipeline` `[OPEN]` (P2)
- **Files:** `phronesisml/configs/settings.py:70-76` (field),
  `phronesisml/__init__.py:304` (`WorkflowState(data_path=...)` — no size passed),
  `phronesisml/agents/upload/agent.py:65-67` (falls back to `DEFAULT_MAX_FILE_SIZE_BYTES` = 2 GB),
  `backend/app/workers/runner.py:307` (backend **does** wire `settings.max_upload_bytes`).
- **Impact:** SDK/CLI path ignores the configured limit (uses 2 GB); backend path honors
  `MAX_UPLOAD_SIZE_MB`. Inconsistent enforcement.
- **Suggested fix (low risk):** in `run_pipeline`, set
  `WorkflowState(data_path=data_path, max_file_size_bytes=config.data.max_file_size_bytes)`.

### C7 — Preflight-blocker router branch effectively dead `[OPEN]` (P3)
- **Files:** `phronesisml/workflow/router.py:91-100`,
  `phronesisml/workflow/nodes.py:82-89`,
  `phronesisml/agents/target_detection/agent.py:174-194`.
- **Root cause:** on blockers the agent returns `AgentResult(success=False, …)` →
  the node wrapper (`nodes.py:61-69`) raises `AgentError` before any state update, so
  `state.preflight_blockers` is never set and `route_after_target_detection` never sees
  it. Additionally, `nodes.py:84` looks for a nested `metadata["preflight"]` key, while the
  agent writes top-level `metadata["preflight_warnings"]/["preflight_blockers"]`.
- **Impact:** blockers still stop the run — but via exception, not graceful routing;
  the router branch and part of the metadata propagation are dead code.
- **Suggested fix (needs care):** standardize one metadata shape and either remove the
  dead branch or route on it. Deferred (touches error semantics).

### C8 — `fillna(None)` raises when filling nulls `[OPEN]` (P2)
- **File:** `phronesisml/data/transformers/cleaning.py:28-71`
  (`fill_value` default `None`, line 31; `result[target_cols].fillna(fill_value)` line 71).
- **Evidence:** `pandas` → `ValueError: Must specify a fill 'value' or 'method'.`
- **Trigger:** only when `null_strategy="fill"` is selected without a `fill_value`.
  Default strategy is `"drop"`, so not hit by default.
- **Suggested fix:** if `strategy == "fill"` and `fill_value is None`, raise a clear
  `DataTransformError` (or choose a documented default) instead of a raw pandas error.

### C9 — Spark path can't actually stream large files `[OPEN]` (P3)
- **Files:** `phronesisml/data/loaders/file_loader.py:221-225` (always `engine.collect()`
  to pandas), `phronesisml/data/validators/checks.py:50,62` (`engine.shape`/`engine.dtypes`
  force materialization).
- **Impact:** for >500 MB inputs the Spark engine is selected but the loader/validators
  pull everything into pandas — the memory advantage is lost. Large refactor; out of scope now.
- **Status:** `[VERIFY]` — mechanism confirmed by reading code; full-scale behavior not load-tested.

### C11 — Minor: validation "empty columns" line only when non-empty `[INFO]` (P3)
- Cosmetic; the count line is omitted when there are no empty columns. Intentional-ish.

### C12 — Report sections that were already correct `[INFO]`
- Target detection, feature engineering, evaluation (`metrics`, `ambiguity_caveat`),
  explainability (`feature_importance`, `explainer_type`, `sampled`), and notes sections
  read keys that match the produced state. No change needed.

---

## 5. Findings — Config

### G1 — Unused/loosely-wired config `[OPEN]`
- `DataConfig.max_file_size_bytes` (`settings.py:70-76`) is not propagated to
  `WorkflowState` by the SDK path (see C6). Backend path wires it separately.
- `PANDAS_MAX_BYTES = 2 MB` (`settings.py:32`) is the pandas-vs-polars routing threshold;
  `DEFAULT_MAX_MEMORY_BYTES = 500 MB` (`settings.py:35`) is the spark threshold.
- `DEFAULT_MAX_FILE_SIZE_BYTES = 2 GB` (`settings.py:38`) equals backend
  `MAX_UPLOAD_SIZE_MB = 2048`, so the two defaults agree by value.

---

## 6. Findings — Deployment / Ops

### O1 — Sample datasets not seeded on Render `[OPS]`
Set `SEED_SAMPLE_DATASETS=1` in the Render dashboard. (Repo-level env vars don't apply;
`render.yaml` does not force it.) Without it the live app shows zero datasets.

### O2 — Ephemeral storage on Render free tier `[OPS]`
512 MB RAM / 0.1 vCPU / ephemeral disk: uploaded datasets, runs, models, and artifacts
are wiped on spin-down or redeploy. Only bundled samples survive (re-seeded each start).
Not a code bug; set expectations accordingly.

### O3 — Vercel env vars `[INFO]`
Required and currently present: `VITE_API_BASE_URL`, `VITE_WS_BASE_URL`
(= `https://phronesisml-backend.onrender.com/api/v1`), `VITE_AUTH_MODE=disabled`,
`VITE_DEMO_MODE=false`. The deployed bundle was confirmed to contain the backend host.
Recommend deleting unused non-`VITE_` vars (especially any `SUPABASE_JWT_SECRET`).

### O4 — Rotate the push PAT `[OPS]`
A fine-grained PAT was used for the last push and was pasted in plaintext. Rotate it at
https://github.com/settings/personal-access-tokens.

---

## 7. Verified-Good (no action)

- **V1** `GET /api/v1/health` → 200, version `0.3.1`.
- **V2** CORS preflight → 200 with correct ACAO/credentials/methods/headers (see B3).
- **V3** Frontend build served; entry bundle `assets/index-Dgv_B59N.js` references the
  backend base URL.
- **V4** Non-UTF-8 (Windows-1252) CSV/TSV upload accepted (201); accents/`£` preserved.
- **V5** Full 11-stage runs (wine→classification, diabetes→regression) produce correct
  artifacts (`model.joblib`, `report.html`, `shap.json`, …) and `/models`, `/predict` work.
- **V6** `pytest backend/tests tests`, `ruff`, frontend `typecheck`/`lint`/`test`/`build`
  all pass.

---

## 8. Correction Plan (prioritized, minimal-risk)

**Phase 1 — DONE (this session, uncommitted)**
- Report builder key reads (C1–C3), frontend `.txt` (F1), status union (F2).
- Re-verify: `pytest tests/test_interfaces.py tests/test_run_report.py tests/test_report_io.py`;
  then full suite + frontend checks; then commit + push.

**Phase 2 — Recommended next (low risk, one root cause)**
- Fix the profiler key contract for C4/C5/C10 by adding `n_unique` to
  `_profile_categorical` **and** `_profile_numeric` in `stats.py` (keep `cardinality`).
  This single change repairs target-ID detection, high-cardinality warnings, and
  sampling/one-hot memory estimation without touching each reader.
- Add regression tests: a high-cardinality categorical frame (expect a warning),
  an ID-like target (expect a blocker), and a wide-cardinality sampling estimate.
- Verify: `pytest tests/` (esp. `test_preflight.py`, `test_model_recommendation.py`,
  `test_resources_engines.py`).

**Phase 3 — Config wiring (low risk)**
- In `run_pipeline` (`phronesisml/__init__.py:304`) pass
  `max_file_size_bytes=config.data.max_file_size_bytes` into `WorkflowState`.
- Verify: a unit test that a tiny configured limit rejects an over-size file via SDK.

**Phase 4 — Robustness (small, isolated)**
- F3: WS base fallback to `VITE_API_BASE_URL`.
- C8: guard `strategy=="fill"` with `fill_value is None` → clear `DataTransformError`.
- C7: standardize preflight metadata shape (or delete dead branch) — do carefully; touches
  error semantics, so land separately with tests.

**Phase 5 — Larger, needs explicit approval**
- C9: true streaming for the Spark path (>500 MB). Significant refactor; do not attempt
  without sign-off and a load test.

**Ops (independent of code)**
- O1 set `SEED_SAMPLE_DATASETS=1`; O2 accept ephemeral storage; O4 rotate PAT.

---

## 9. Decisions / Status

1. **Phase 2 profiler change (C4/C5/C10):** **DECISION — report only, do NOT change code.**
   The `cardinality` vs `n_unique` mismatch stays documented, not patched.
2. **`.txt` uploads:** **UNRESOLVED.** Currently `.txt` was removed from the UI `ACCEPT`
   so the picker matches the backend. Open question: keep it out, or add real backend
   support for `.txt`? Both options are documented in F1.
3. **Commit Phase 1:** **NOT committing.** The three edits below remain local/uncommitted
   and are captured in this report only.

**Current uncommitted local edits (Phase 1 — applied, not committed):**
```
phronesisml/ml/reports/builder.py                                   (validation/EDA/model-selection sections)
frontend/src/components/datasets/upload-dataset-dialog.tsx         (ACCEPT: removed .txt)
frontend/src/types/model.ts                                        (status union: +"candidate")
```
> If you prefer a pure documentation-only state, these three edits can be reverted with
> `git checkout -- phronesisml/ml/reports/builder.py frontend/src/components/datasets/upload-dataset-dialog.tsx frontend/src/types/model.ts`.
> Say the word and I will revert them.

---

## 10. Consolidated Error List (flat — every issue found)

Everything below is a defect/risk observed during the audit, regardless of severity or
whether it was changed. Use this as the single checklist.

| # | Where | Error / risk | Severity | Changed? |
|---|-------|--------------|----------|----------|
| E1 | `phronesisml/ml/reports/builder.py` `_build_validation_section` | Reads `report["checks"]` which never exists → validation section renders empty | P1 | Yes (local) |
| E2 | `phronesisml/ml/reports/builder.py` `_build_eda_section` | Reads `n_rows`/`n_cols`/`null_percentage`; profiler emits `shape.rows/columns` → rows/cols missing | P1 | Yes (local) |
| E3 | `phronesisml/ml/reports/builder.py` `_build_model_selection_section` | Reads `model_type`/`mean_cv_score`; candidates carry only `name` → shows "Candidate N", no scores | P1 | Yes (local) |
| E4 | `frontend/.../upload-dataset-dialog.tsx:20` + `dataset_service.py:22` + `file_loader.py:27` | UI offers `.txt`, backend rejects it → 415 | P2 | Yes (local) |
| E5 | `phronesisml/data/profilers/stats.py:98-117` vs `detector.py:431,444,489` + `estimator.py:179` | Profiler emits `cardinality`; readers use `n_unique` → high-cardinality check + one-hot estimate are silent no-ops | P2 | No (report only) |
| E6 | `stats.py:74-95` vs `detector.py:458` | `_profile_numeric` has no `n_unique`; numeric-target ID check reads `n_unique` → no-op | P2 | No (report only) |
| E7 | `phronesisml/workflow/sampling_node.py:87-98` + `estimator.py:166-185` | Same key mismatch → sampling/encoded-memory estimate undercounts categorical expansion | P2 | No (report only) |
| E8 | `phronesisml/__init__.py:304` + `agents/upload/agent.py:65-67` + `settings.py:70-76` | `data.max_file_size_bytes` not passed into `WorkflowState`; SDK path falls back to 2 GB default (backend path wires it separately) | P2 | No |
| E9 | `phronesisml/data/transformers/cleaning.py:31,71` | `fillna(fill_value)` with default `fill_value=None` → `ValueError` when `null_strategy="fill"` and no value given | P2 | No |
| E10 | `frontend/src/types/model.ts:103` vs `model_service.py:75` | Backend emits `status:"candidate"` not in the TS union | P3 | Yes (local) |
| E11 | `phronesisml/workflow/router.py:91-100` + `nodes.py:82-89` + `target_detection/agent.py:174-194` | Preflight-blocker router branch dead: blockers raise `AgentError` before state update; `nodes.py` looks for nested `metadata["preflight"]` that isn't produced | P3 | No |
| E12 | `frontend/src/api/websocket.ts:30-35` | WS base defaults to `ws://localhost:8000` only; no fallback to `VITE_API_BASE_URL` (currently masked by env var) | P3 | No |
| E13 | `phronesisml/data/loaders/file_loader.py:221-225` + `validators/checks.py:50,62` | Spark engine selected for >500 MB but loader/validators always collect to pandas → no streaming | P3 | No |
| E14 | `dataset_service.py:22` vs `file_loader.py:27-33` | Backend allow-list omits `.pq/.ndjson/.feather/.arrow` that the loader supports (UI doesn't offer them either) | P3 | No |
| E15 | Render dashboard | Sample datasets not seeded until `SEED_SAMPLE_DATASETS=1` → live list empty | OPS | No |
| E16 | Render free tier | Ephemeral storage wipes uploads/runs/models/artifacts on redeploy | OPS | No |
| E17 | Git auth | Push PAT used in plaintext → rotate | OPS | No |

**Not errors (verified working):** health 200 v0.3.1; CORS preflight correct; API route
contract matches frontend; WS path matches; non-UTF-8 upload works; full 11-stage runs
produce correct artifacts; tests/lint/build pass. (See Section 7.)

---

## 11. Suggested Fix Map (for when you decide to change code)

- **E1–E3:** already implemented locally (Section 1). Keep or revert.
- **E4:** keep UI aligned (done) **or** add backend `.txt` support — pending decision.
- **E5–E7:** one change in `stats.py` — add `n_unique` to `_profile_categorical` and
  `_profile_numeric` (keep `cardinality`). Repairs E5, E6, E7 together.
- **E8:** one line in `run_pipeline` — pass `max_file_size_bytes=config.data.max_file_size_bytes`.
- **E9:** guard `strategy=="fill" and fill_value is None` with a clear `DataTransformError`.
- **E10:** already added `"candidate"` to the union (done).
- **E11:** standardize preflight metadata shape; then keep or delete the router branch.
- **E12:** fall back to `VITE_API_BASE_URL` (http→ws) in `getWsBaseUrl`.
- **E13:** larger refactor — defer, needs approval + load test.
- **E14–E17:** no code change (INFO/OPS).

---

## 12. Exact Files Touched This Session

```
phronesisml/ml/reports/builder.py                                   (validation/EDA/model-selection sections)
frontend/src/components/datasets/upload-dataset-dialog.tsx         (ACCEPT: removed .txt)
frontend/src/types/model.ts                                        (status union: +"candidate")
```
