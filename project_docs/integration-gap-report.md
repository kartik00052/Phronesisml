# PhronesisML Full-Stack Integration Gap Report

**Phase 3 — Pre-implementation audit.** Date: 2026-09-20.
Scope: map every broken boundary between the PhronesisML SDK (backend ML core),
a to-be-built web API layer, and the existing React frontend, and specify the
monitored target architecture before any implementation begins.

---

## 1. Audit summary (what exists today)

### 1.1 Python SDK (`phronesisml/`) — capability rich, not servable
- Complete 11-stage LangGraph pipeline, canonical order in
  `phronesisml/_stages.py:31` (`upload → etl → validation → eda →
  target_detection → feature_engineering → model_selection → evaluation →
  explainability → reporting → storage`).
- Real loaders: CSV / XLSX (multi-sheet auto-selection) / Parquet / JSON /
  JSONL / TSV via `data/loaders/file_loader.py::load_file`; engine-agnostic
  (pandas / polars / spark), 2 GB size guard, 10k-row chunked CSV reads.
- Profile: `data/profilers/stats.py::profile_dataset` → the exact `data_profile`
  JSON contract the frontend already renders.
- Target detection, ETL cleaning, feature engineering (with serializable
  transform recipe), model recommendation + HPO trainer, evaluation incl.
  ROC/PR curves, SHAP explainability (`ml/explainability/service.py`), report
  builders (Markdown / HTML / JSON), and a 17-file + `model.joblib` artifact
  suite (`services/storage.py::save_artifacts`, written under
  `<base_dir>/<run_id>/`).
- Pre-flight sampling with resource estimation (`workflow/sampling_node.py`,
  `ml/preflight/*`).
- **Gaps found:**
  1. **No HTTP / API layer, no database, no WebSocket** — the SDK is a
     programmatic library only.
  2. **No progress/streaming callback** — execution is a single
     `graph.ainvoke`; progress is only observable via module logs
     (verified by grep). Live UI progress requires a runner that iterates the
     graph node-by-node (`graph.astream(stream_mode="updates")`) and emits
     real events.
  3. **run_id / status are owned by the SDK** (`sdk.py:527`); a servable
     backend must supply `run_id` + `status` itself via the initial
     `WorkflowState` and drive the graph directly.
  4. **No per-run plan of record** — no run index, no event log, no artifact
     registry; run metadata only lives in `run_metadata.json` inside the
     artifact directory. No cross-run querying, stats, or concurrency control.
  5. **Default artifact base dir** is the CWD (`./Phronesis_artifacts`) — must
     be overridable per deployment via `StorageAgent(base_dir=...)` /
     `compose_agents(agent_overrides={"storage": {...}})`.
  6. `health()`/`capabilities()` exist but cover the SDK only (no
     DB/storage/web checks).

### 1.2 Frontend (`frontend/`) — complete UI, demo-only data path
- Full run workspace (overview / pipeline / data / models / explainability /
  reports / artifacts / logs), datasets registry, new-run wizard, compare page —
  all TypeScript + React Query + Zustand (UI state).
- Transport layer is real (`src/api/client.ts::apiRequest`) but **every domain
  module fans out to `src/mocks/handlers.ts` `demo*` functions when
  `isDemoMode()` is true**, and demo mode is the default when no
  `VITE_API_BASE_URL` is set.
- **Gaps found:**
  1. Real-mode URL paths use `/api/...` (top-level, no version); the target
     contract is `/api/v1/...`.
  2. **No upload function exists** — the wizard only picks seeded datasets
     (`data-source-step.tsx`); `apiRequest` forces `Content-Type: application/json`
     which breaks multipart uploads.
  3. **No WebSocket / SSE** anywhere — live run progress is a `setTimeout`
     store simulator + react-query polling of demo handlers.
  4. Error normalization assumes a flat payload
   (`{error: string, error_type, message, context}`); the target contract is
     the nested `{error: {code, message, details}}` envelope.
  5. `ExplainabilityView.beeswarm`/`samples` are officially labelled
     "demo render only" — real mode must not fabricate SHAP points.
  6. `apiRequest` has a hard 60 s timeout and reads JSON for all responses —
     fine for JSON contracts, must not break multipart or large artifact reads.

### 1.3 Verification & tooling
- `verify_phronesisml.py`, `FULLSTACK_VERIFICATION_REPORT.md`: **absent**
  (only `test_phronesis.py` + `tests/`).
- Environment: `uv` managed, `.python-version` 3.12, `uv.lock` committed.
  `fastapi/uvicorn/sqlalchemy/alembic/python-multipart/websockets` were added
  to a new `web` extra in `pyproject.toml` and synced before implementation.
- `tests/` cover the SDK (data IO, EDA, ETL, target, feature construction,
  AutoML trainer, evaluation, explanation summary, artifact storage, report
  IO, regressions). No API / integration coverage exists.

---

## 2. Target architecture

```
React (presentation only)
   │  /api/v1/*  REST                                 WS /api/v1/runs/{id}/events
   ▼
FastAPI adapter layer (backend/app)                     ── owns HTTP, DB, WS, job scheduling
   │  services → phronesisml SDK (engine authoritative:
   │            engine selection, target detection, EDA, ETL, feature engineering,
   │            model selection, evaluation, SHAP — never re-implemented here)
   ▼
WorkflowState → compile(pipeline) → astream(node-by-node) → events/artifacts
   ▼
SQLite (SQLAlchemy)  +  storage/{datasets,runs,artifacts,reports}
```

Rules:
- The SDK owns **all ML intelligence**; FastAPI wires + serves it.
- The React app never re-implements AutoML; it renders backend values only.
- Large data never crosses the wire: previews limit rows, charts use
  server-side aggregates, artifact/report payloads are truncated on read.

---

## 3. Boundary matrix (frontend → endpoint → service → SDK → artifact/db)

| Frontend screen / hook | API endpoint (target) | Backend service | SDK capability | Artifact / DB |
|---|---|---|---|---|
| `useHealth` / top bar | `GET /api/v1/health` | `health_service` | `phronesisml.health()` + DB/storage prober | DB reachability + storage writability |
| `useCapabilities` / settings | `GET /api/v1/capabilities` | `capabilities_service` | `phronesisml.capabilities()` + dynamic dependency probe | frozen response |
| datasets registry (`pages/datasets.tsx`) | `GET /api/v1/datasets` (paged) | `dataset_service.list` | — | `datasets` table |
| dataset detail sheet | `GET /api/v1/datasets/{id}` | `dataset_service.get` | `load_file` + `profile_dataset` + `validate_dataframe` at upload | `datasets` row + `storage/datasets/<id>/profile.json` |
| upload (new, wizard + page) | `POST /api/v1/datasets` (multipart) | `dataset_service.upload` | `load_file`, `profile_dataset`, `detect_format`, `list_excel_sheets` | dataset file + metadata + preview |
| `recommendEngine` (wizard) | `POST /api/v1/engine/recommend` | `engine_service.recommend` | `select_engine` thresholds (PANDAS_MAX_BYTES / max_memory) | computed response |
| run list / dashboard | `GET /api/v1/runs`, `GET /api/v1/runs/recent`, `GET /api/v1/stats` | `run_service` / `stats_service` | — | `runs` table (indexed) + `model_results` |
| new-run wizard submit | `POST /api/v1/runs` | `run_service.create` (+ `workers.runner`) | `config`, `select_engine`, `compose_agents`, `build_graph`, `astream` | `runs` row (queued) → events |
| run detail (layout) | `GET /api/v1/runs/{id}` | `run_service.get` | — | `runs` row + `run_events` replay |
| live progress (overview/pipeline) | `WS /api/v1/runs/{id}/events` + `GET /api/v1/runs/{id}/pipeline/progress` | `websocket.manager` / `pipeline_service` | per-node `astream` events | `run_events` + `pipeline_stages` |
| pipeline view | `GET /api/v1/runs/{id}/pipeline`, `/pipeline/stages` | `pipeline_service` | stage state from runner | `pipeline_stages` table |
| data / EDA / ETL tab | `GET /api/v1/runs/{id}/dataset` | `dataset_service.for_run` | `data_profile`, `transform_log`, `validation_report` from state | run artifact `eda.json`, `validation.json`, `transform_log` (DB), `feature_metadata.json` |
| models tab | `GET /api/v1/runs/{id}/models`, `/models/{type}` | `model_service` | `cv_results`/`best_pipeline`, `evaluation_report` | `training.json`, `model.json`, `evaluation.json` |
| explainability tab | `GET /api/v1/runs/{id}/explainability` | `explainability_service` | `explanation_report` | `shap.json` (importance only in real mode; beeswarm/samples are demo-only and not fabricated) |
| reports tab | `GET /api/v1/runs/{id}/report?format=markdown\|html\|json` | `report_service` | `build_report` / `build_html_report` / `build_json_report` | `report.md`, `report.html`, `pipeline.json` |
| artifacts tab | `GET /api/v1/runs/{id}/artifacts`, `/artifacts/{name}/content` | `artifact_service` | `list_artifacts` | `storage/runs/<run_id>/` scan → `artifacts` table |
| run logs | `GET /api/v1/runs/{id}/logs` | `run_service.logs` | runner log capture | `logs.txt` artifact + `runs.logs` |

---

## 4. Identified, prioritized gaps (work plan)

1. **Backend web layer absent** → build FastAPI adapter (`backend/app`) with
   `/api/v1` routers, middleware (CORS, X-Request-ID, exception envelope,
   security headers, request logging with secrets masked), Pydantic schemas.
2. **No run scheduling / execution boundary** → implement `workers/runner.py`:
   a dedicated thread per run with its own asyncio loop; drives the SDK graph
   via `astream(stream_mode="updates")`; real per-node events; reconstructs
   final state; re-renders report with terminal status; indexes artifacts.
3. **No run/event persistence** → SQLite + SQLAlchemy + Alembic
   (`datasets`, `runs`, `run_events`, `pipeline_stages`, `artifacts`,
   `model_results`). Events persisted first, then broadcast — reconnect
   replays from `after=<seq>`.
4. **No live transport** → WebSocket manager (thread-safe publish onto the
   asyncio loop); single canonical stage-state enum shared across DB / WS /
   frontend.
5. **No upload** → multipart upload endpoint with extension/MIME/content
   validation, 2 GB cap via config, engine-selected load + profile + preview
   + validation persisted; XLSX multi-sheet surfaced.
6. **Frontend never talks to the real backend** → point api modules at
   `/api/v1`, add `uploadDataset` (XHR progress), add `websocket.ts` client
   with reconnect/heartbeat, normalize the nested error envelope, keep mocks
   strictly behind `VITE_DEMO_MODE=true`
7. **Verification** → `verify_fullstack.py` (exit 0/1) over the running stack
   producing `FULLSTACK_VERIFICATION_REPORT.md` with a compatibility matrix
   (CSV/XLSX/Parquet/large × upload/ETL/EDA/target/features/models/eval/SHAP/
   reports/artifacts/events × backend/API/frontend/E2E) using Iris in three
   formats + medium/large synthetic datasets.

---

## 5. Confirmed non-goals (honest behaviour)
- Per-row SHAP beeswarm/sample attribution is **not fabricated** in real
  mode; the explainability screen shows real global SHAP importance + report
  and clearly notes row-level demo renderings are unavailable for real runs.
- Engine recommendation is an SDK-derived advisory; the pipeline always asks
  `select_engine` at run time.
- No progress percentages are invented; progress is derived only from
  completed node indexes.

---

## 6. Completion pass — final targeted fixes (Phase 4)

Final sweep closing the last BROKEN/PARTIAL items on the checklists across
backend, frontend, SDK delegation and verification.

### Backend
- **Health probes (real, not derived)** — `health_service.health()` now
  performs a live DB probe (`session_scope` + `SELECT 1`) and a storage
  writeability probe (mkdir + `.healthcheck` under `data_storage_dir` /
  `run_storage_dir`). Response carries `database: {reachable, error?}` and
  `storage: {writable, paths, error?}`; `status` degrades when either fails.
  `_sdk_version()` fallback corrected to `0.0.0+unknown` instead of a
  hard-coded `0.3.1`. `HealthReport` schema extended to match.
- **Run list filters** — `GET /api/v1/runs` accepts `taskType`, `sort` and
  `order` (`^(asc|desc)$`) and passes them to `run_service.list_runs`
  (`repositories.list_runs` already supported them). New
  `test_list_runs_filters_and_sorts` covers asc/desc, status and taskType.
- **Run detail sanitization** — `run_to_dict` scrubs `warnings`/`logs` via
  `_scrub_text` (root/storage dirs → `<storage-root>`, home → `~`) and the
  error via `_sanitized_error` (traceback dropped, message/type/context
  values scrubbed), matching the SDK-adjusted error surface.
- **Dataset upload orphan cleanup** — `upload_dataset` now deletes the
  registered row **and** `rmtree`s the partial upload directory on any
  inspection or post-write failure via best-effort `_cleanup_upload`
  (no half-indexed datasets or orphan dirs survive a rejected upload).
- **Prediction single-source-of-truth** — `prediction_service.predict`
  loads the model + feature metadata through the SDK's
  `SavedRun.from_directory` (the same loader the CLI / demo use) instead of
  hand-loading `model.joblib` + `feature_metadata.json`. Feature subsetting,
  `_coerce`, probability output and error codes (`RunNotFound`,
  `ModelUnavailable`, `ModelLoadFailed`, `EmptySamples`,
  `PredictionFailed`) are preserved. Artifact-dir resolution keeps the
  traversal guard.

### Frontend
- **Engine limits centralized** — new `src/config/engine-limits.ts` mirrors
  the SDK constants (`PANDAS_MAX_BYTES` = 2 MiB, `POLARS_MAX_BYTES` = 500
  MiB) with `engineFromBytes`, `formatByteSize` and `engineReason`. The
  demo wizard handler, upload router, `store.inferEngine` and every seeded
  dataset/run `engineReason` phrase are now derived from these constants —
  the "2 MB / 500 MB" copy can no longer drift from real routing.
- **Demo recents parity** — `demoRecentRuns` returns 8 rows, matching the
  documented recent-runs limit.
- **Dashboard datasets count** — the registered-datasets card and empty-state
  now prefer authoritative `stats.totalDatasets` over the (paginated) list
  page length.
- **Health UI** — `HealthReport` models `database`/`storage`; `demoHealth`
  emits them; `ConnectionStatus` degraded tooltip reports
  "Database unreachable" / "Storage not writable" alongside missing deps.
- **Live pipeline DAG** — `PipelineDag` syncs ReactFlow node/edge state on
  every `stages` update (polled during active runs) instead of freezing on
  the first snapshot.
- **Artifact truncation** — removed the dead `truncated ? content : content`
  ternary and added an honest "Preview truncated" warning banner.

### Explicitly kept honest
- **Explainability** keeps its honest 404/`ErrorState` path in real mode —
  SHAP row-level beeswarm/sample attribution is not fabricated (see
  §5 non-goals); the UI already renders clear unavailable/empty states.

### Verification (all green)
- SDK + backend: `pytest` → **341 passed, 3 deselected** (integration);
  `pytest -m integration` → **3 passed**; `ruff check` clean; `ruff format`
  applied to the 3 remaining files (`README.md`, `verify_phronesisml.py`,
  `backend/app/main.py`).
- `python verify_phronesisml.py` → **ALL 30 PASS**.
- Frontend: `tsc`, `eslint`, `vitest` (14 files / **64 tests**), demo-mode
  Playwright e2e (`happy-path`) → **5 passed, 2 skipped** (real-backend
  specs are opt-in via `E2E_REAL_BACKEND=true`).

---

## 7. Final runtime acceptance — real backend + frontend (Phase 5)

Controlled live run of the real application (`VITE_DEMO_MODE=false`) against a
real dataset with full lifecycle + restart + cleanup exercises. Three fixable
defects were found and fixed; everything else was verified working.

### Defects found & fixed (smallest change only)

1. **Run Logs endpoint/tab dead in real mode**
   - Symptom: `GET /api/v1/runs/{id}/logs` returned `[]` and the workspace
     Logs tab showed "No logs yet", while the SDK's real `logs.txt` existed on
     disk for every completed run.
   - Root cause: `run_service.run_logs` only returned the DB `runs.logs`
     column, which the worker never populates (the SDK writes `logs.txt` as a
     run artifact instead).
   - Fix: `backend/app/services/run_service.py` — fall back to reading
     `storage/runs/{run_id}/logs.txt` when the DB column is empty (file lines,
     blank lines stripped). New regression test
     `backend/tests/test_runs.py::test_run_logs_falls_back_to_logs_txt`.
   - Verification: `/logs` now returns the real run log lines; UI Logs tab
     renders them.

2. **Restore of a cancelled run immediately re-cancelled it**
   - Symptom: UI Restore on a cancelled run flipped
     `queued → cancelled`. `RESTORE_TRANSITIONS= ["queued","cancelled"]`.
   - Root cause: `RunWorker.cancel()` added the id to `WORKER._cancelled`, but
     `restore_run` never cleared it, so the worker's cooperative cancellation
     check fired on the first graph step of the re-queued run.
   - Fix: `backend/app/workers/runner.py` adds `clear_cancel()`; `restore_run`
     calls it before `WORKER.launch`. `test_cancel_restore_delete` now asserts
     the restored run actually executes to `completed`/`failed` (poll window
     widened to 60 s to stay stable under a concurrent full suite).
   - Verification: UI restore now observed `cancelled → running → completed`
     (18 `artifact.created` + `run.completed` on the WS stream).

3. **Duplicate `node_sampling` React keys**
   - Symptom: deterministic console warning
     "Encountered two children with the same key `node_sampling-queued`" (the
     pipeline stage list legitimately contains `node_sampling` 5× — one
     pre-flight sampling node before EDA/FE/model-selection/explainability/
     reporting).
   - Fix: unique keys in the two stage list renderers —
     `frontend/src/components/run/activity-feed.tsx` (indexed event ids) and
     `frontend/src/components/pipeline/pipeline-stepper.tsx` (`${id}-${index}`).
   - Verification: warning gone from the console on the next live run.

### What was verified working (not changed)

- Real-mode served, no mock leakage (no demo banner; `isDemoMode()` false;
  every dashboard/dataset/run read hit `/api/v1`).
- Health + probes (`database.reachable`, `storage.writable`), `/capabilities`
  honest (xgboost/lightgbm/catboost reported `installed=false`).
- Dataset upload via UI (real CSV → DB row + storage file + profile/preview/
  validation, no orphans); invalid/empty upload → HTTP 422 envelope.
- Full 11-stage SDK pipeline from a UI-launched run (~12 s, iris);
  WS replay (`last_seq`) + live `pipeline.stage` / `artifact.created` /
  `run.completed` events; live DAG + polling; refresh/reconnect preserved
  state.
- Real trained model (LogisticRegression), real SHAP LinearExplainer feature
  importance (sampled, honest), run-specific Markdown/HTML reports, 18
  artifacts; artifact content endpoint + path traversal blocked (404).
- Prediction via SDK `SavedRun` loader: per-row class + probability +
  features; error states `RunNotFound`/`EmptySamples`/`ModelUnavailable`.
- Cancel (worker flag + event + UI), Restore (artifacts invalidated, re-run),
  Delete run/dataset (DB row + storage dir removed, UI navigates away) — all
  through the real UI.
- 404 run → graceful frontend error; upload/422 → handled error state.
- Backend restart: in-flight run reconciled to `failed` with the honest
  "Interrupted — backend restarted" error; no run auto-starts; data intact.
- Frontend restart: app reloads against the same data.
- DB↔storage consistency: every completed run has its artifact dir, failed
  runs correctly have none, deleted resources fully removed.

### Retention note
One acceptance run (`run_08289721a85a4313`) with its full artifact suite and a
duplicate that was created then deleted were the only new rows; the duplicate
was removed. One pre-existing orphan dataset dir
(`storage/datasets/ds_e8d18954047b45f7`, dated before this pass) was left
untouched. An empty `storage/runs/run_test` dir created by this session's
tooling was removed.

### Final gates (this pass)
- Backend `pytest` → **342 passed, 3 deselected**; `pytest -m integration` →
  **3 passed**; `ruff check` clean; `ruff format --check` → 197 files ok.
- `python verify_phronesisml.py` → **ALL 30 PASS**.
- Frontend: `typecheck` clean, `lint` clean, `vitest` **64 passed**,
  `build` ok.
- Playwright e2e: real-backend (`E2E_REAL_BACKEND=true`) **2 passed**; demo
  (`happy-path`) **5 passed**.
- Servers (backend :8000, frontend :5173, preview :4173) stopped by PID;
  ports released; temp logs/pid files removed.