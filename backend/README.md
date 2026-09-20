# PhronesisML Web Backend

FastAPI HTTP + WebSocket adapter for the PhronesisML SDK. It exposes the full
pipeline lifecycle — dataset upload, run orchestration, live progress events,
model leaderboards, artifacts, reports, explainability, and prediction — to
the React frontend.

## Quickstart

```bash
# from the repository root
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

- API + interactive docs: <http://localhost:8000/docs>
- All HTTP and WebSocket routes live under **`/api/v1`**.
- SQLite schema is bootstrapped automatically on startup (`init_db`).

### Environment

| Variable              | Default                                  |
| --------------------- | ---------------------------------------- |
| `DATABASE_URL`        | `sqlite:///<root>/data/phronesisml.db`   |
| `DATA_STORAGE_DIR`    | `<root>/storage/datasets`                |
| `RUN_STORAGE_DIR`     | `<root>/storage/runs`                    |
| `ARTIFACT_STORAGE_DIR`| `<root>/storage/artifacts`               |
| `REPORT_STORAGE_DIR`  | `<root>/storage/reports`                 |
| `MAX_UPLOAD_SIZE_MB`  | `2048`                                   |
| `CORS_ORIGINS`        | `http://localhost:5173`                  |
| `REQUEST_LOG`         | `1`                                      |

## API surface (`/api/v1`)

**System**
- `GET /health` — service + dependency status (snake_case keys).
- `GET /capabilities` — mirrors `phronesisml.capabilities()` (task types,
  engines, explainers, pipeline stages, sdk methods, CLI commands).

**Datasets**
- `POST /datasets` (multipart `file`) / `POST /datasets/upload` (alias) —
  streamed upload to disk; returns `{ dataset: Dataset }`.
- `GET /datasets?page&pageSize&search` — paged summaries.
- `GET /datasets/{id}` — full dataset detail.
- `GET /datasets/{id}/preview?page&pageSize` / `schema` / `eda`.
- `DELETE /datasets/{id}`.

**Engines**
- `POST /engine/recommend` `{ bytes, rows?, cols? }` → `EngineRecommendation`.

**Runs**
- `POST /runs` (wizard payload, `RunRequest`) → `Run` (201).
- `GET /runs?page&pageSize&status&datasetId&search`, `GET /runs/recent`.
- `GET /runs/{id}` — full run detail (camelCase per frontend contract).
- `POST /runs/{id}/cancel`, `POST /runs/{id}/restore`, `DELETE /runs/{id}`.
- `GET /runs/{id}/logs` → `string[]`.
- `GET /runs/{id}/dataset` → `Dataset | null`.
- `POST /runs/{id}/predict` `{ samples: object[] }` → `PredictionResponse`.

**Pipeline (per run)**
- `GET /runs/{id}/pipeline`, `/pipeline/stages`, `/pipeline/progress`.

**Models**
- `GET /runs/{id}/models`, `GET /runs/{id}/models/{modelType}`.

**Explainability / Report / Artifacts / Stats**
- `GET /runs/{id}/explainability`.
- `GET /runs/{id}/report?format=markdown|html|json`.
- `GET /runs/{id}/artifacts`, `GET /runs/{id}/artifacts/{name}/content`.
- `GET /stats` — dashboard aggregates (`engineBreakdown`, `taskBreakdown`).

**WebSocket**
- `WS /ws/runs/{runId}?last_seq=N` — replays persisted events after `N`,
  then streams live `{ type, run_id, seq, status, stage, summary, payload, ts }`
  frames (`replay.done`, `pipeline.stage`, `run.started/completed/failed/cancelled`,
  `model.completed`, `artifact.created`). Heartbeat (`ping`) every 30 s.

### Error envelope

Every non-2xx response (including handler and unmatched-route 404s) is:

```json
{ "error": { "code": "RunNotFound", "message": "RunNotFound" } }
```

Machine-readable semantic codes (`DatasetNotFound`, `NotFound`, `FileTooLarge`,
`RunNotFound`, …) are preserved in `error.code`.

## Schemas

`backend/app/schemas/` are Pydantic DTOs that mirror the **frontend TypeScript
contract** at `frontend/src/types/*.ts` (mixed camelCase/snake_case per file by
design — the TS types are the source of truth for the wire format).

## Alembic

Migrations are wired to the same `Base.metadata` used by the runtime models:

```bash
.venv/bin/alembic upgrade head   # apply all migrations
.venv/bin/alembic current        # show current revision
.venv/bin/alembic revision --autogenerate -m "change"   # next migration
```

`backend/alembic/env.py` reads `DATABASE_URL` through `get_settings()`.

## Tests

```bash
# fast contract + dataset + run tests (no model training)
.venv/bin/python -m pytest backend/tests

# full-pipeline integration (trains real models; opt-in marker)
.venv/bin/python -m pytest backend/tests -m integration

# standalone E2E smoke script (verbose HTTP assertions)
.venv/bin/python backend/tests/e2e_smoke.py
```

Integration tests use an isolated temp DB + storage (see
`backend/tests/conftest.py`) so they never touch `data/phronesisml.db`.

## Architecture

- `app/api/v1/` — FastAPI routers (thin: validate → service → DTO).
- `app/services/` — business logic + SDK integration per resource.
- `app/db/` — SQLAlchemy models, repositories (write-lock serialised), `init_db`.
- `app/workers/runner.py` — one thread per run, drives `graph.astream` and
  persists each stage completion as real events; artifacts saved to
  `RUN_STORAGE_DIR/<run_id>` via the SDK's `save_artifacts`.
- `app/ws/hub.py` — thread-safe event relay to connected WebSocket clients.