# PhronesisML — Container Deployment

Runs the full-stack application (FastAPI backend + Vite/React frontend served
by Nginx) in containers with persistent SQLite + filesystem storage. This is a
**single-node, single-process** deployment — fine for evaluation, demos,
staging, and small internal workloads. See
[Production limitations](#production-limitations) before exposing it publicly.

```
Browser ──► frontend (Nginx :80)
            ├── React static bundle (Vite production build)
            └── /api/* ──► backend (FastAPI :8000)   HTTP + WebSocket
                              ├── SQLite  → /app/data      (named volume)
                              └── storage → /app/storage   (named volume)
```

## 1. Prerequisites

- **Docker**. On macOS this means **Docker Desktop** (Docker Engine +
  `docker compose` plugin), which is *not* installed on this machine by
  default. Install it from https://docs.docker.com/desktop/, then verify:

  ```bash
  docker --version
  docker compose version
  docker info
  ```

- No `.env` is required — every variable has a working default. Copy
  `.env.example` → `.env` only to override.

## 2. Environment

`docker-compose.yml` substitutes `${NAME:-default}` values from an optional
root `.env` file. Relevant variables (all documented in `.env.example`):

| Variable            | Default               | Meaning                                    |
| ------------------- | --------------------- | ------------------------------------------ |
| `FRONTEND_PORT`     | `8080`                | Host port for the web UI (Nginx :80)       |
| `CORS_ORIGINS`      | *(empty)*             | Allowed origins; empty = same-origin only  |
| `MAX_UPLOAD_SIZE_MB`| `2048`                | Matches Nginx `client_max_body_size`       |
| `SEED_SAMPLE_DATASETS` | `1`                 | Seed bundled sample datasets at startup    |
| `DATABASE_URL`      | `sqlite:////app/data/phronesisml.db` | SQLite path on the data volume (set to a `postgresql://` URL for Supabase) |
| `AUTH_MODE`         | `disabled`           | `disabled` = single-tenant dev; `supabase` = JWT-authenticated |
| `SUPABASE_URL`      | *(empty)*             | Backend Supabase project URL (needed for JWT issuer/JWKS) |
| `SUPABASE_JWT_SECRET` | *(empty)*           | Server-only HS256 secret (or set `SUPABASE_JWKS_URL` for RSA) |
| `SUPABASE_JWKS_URL` | *(empty)*             | Server-only JWKS endpoint when not using the shared secret |
| `VITE_SUPABASE_URL` | *(empty)*             | Frontend Supabase URL (build-time, public) |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | *(empty)* | Frontend publishable key (build-time, public) |
| `VITE_API_BASE_URL` | `/api/v1`             | Frontend API base (build-time)             |
| `VITE_WS_BASE_URL`  | `/api/v1`             | Frontend WebSocket base (build-time)       |
| `VITE_DEMO_MODE`    | `false`               | `true` uses the in-browser mock data layer |

## 3. Build

```bash
docker compose build
```

Builds both images: `phronesisml-backend:local` and `phronesisml-frontend:local`.

Equivalent standalone builds (same result):

```bash
docker build -f Dockerfile .           # backend
docker build -f frontend/Dockerfile .  # frontend (nginx)
```

Notes:

- The backend image installs the SDK from `pyproject.toml` + `uv.lock`
  (`uv sync --extra web --frozen`) on `python:3.12-slim`, runs as a
  non-root user, and starts the **single** uvicorn process. Do not scale to
  multiple backend workers: the app serialises SQLite writes with an
  in-process lock (`backend/app/db/database.py`).
- The frontend images `VITE_*` variables **at build time** (Vite bakes
  `import.meta.env` into the bundle). To change them, edit `.env`, delete the
  built frontend image, and rebuild.
- `.dockerignore` keeps `storage/`, `data/`, `node_modules/`, venvs, and
  caches out of the build context; those paths are volumes at runtime.

## 4. Start

```bash
docker compose up -d
docker compose ps
```

The UI is then available at **http://localhost:8080** (or
`http://localhost:${FRONTEND_PORT}`). The backend is reachable inside the
Compose network at `backend:8000` and is **not** published to the host by
default; all traffic flows through Nginx on the single origin.

## 5. Health verification

```bash
# Backend (the app's own endpoint checks DB, storage, and dependencies):
curl http://localhost:8080/api/v1/health
# → {"status":"ok","version":"0.3.1",...}

# Frontend static response:
curl -I http://localhost:8080/
```

Your browser session: the data page should list seeded sample datasets, and a
live run on the *Runs → New Run* wizard updates over WebSocket
(`/api/v1/ws/runs/{run_id}`) through the Nginx proxy.

## 6. Logs

```bash
docker compose logs -f          # both services
docker compose logs -f backend  # FastAPI / uvicorn
docker compose logs -f frontend # Nginx access + error
```

## 7. Database migration

The backend auto-creates/upgrades the schema on startup via `init_db`
(`backend/app/db/database.py`). Alembic migrations are also available and run
against the **same mounted database**:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

Migration config: `alembic.ini` (`script_location = backend/alembic`) resolves
`DATABASE_URL` from the backend settings at runtime.

To migrate a **Supabase PostgreSQL** database instead of SQLite, point the
backend at the database (not via the frontend image) and run Alembic from the
repository:

```bash
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db> \
  docker compose run --rm backend alembic upgrade head
```

or, for a locally run backend:

```bash
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db> \
  .venv/bin/alembic -c backend/alembic.ini upgrade head   # repo root
```

The chain `0001_initial → 0002_user_ownership → 0003_rls_policies` is
non-destructive (additive columns; RLS is applied only on PostgreSQL). See
`project_docs/supabase.md` for the full Supabase setup.

## 8. Persistent storage

Named volumes make application data survive rebuilds and restarts:

| Volume               | Mount point         | Contents                                  |
| -------------------- | ------------------- | ----------------------------------------- |
| `phronesisml-data`   | `/app/data`         | SQLite DB (`phronesisml.db`)              |
| `phronesisml-storage`| `/app/storage`      | `datasets/`, `runs/`, `artifacts/`, `reports/` |

To inspect or back up:

```bash
docker volume ls | grep phronesisml
docker run --rm -v phronesisml-data:/data -v phronesisml-storage:/storage alpine ls -R /data /storage
```

## 9. Stopping

```bash
docker compose down          # stop + remove containers (volumes persist)
docker compose down -v       # ALSO delete the named volumes (destructive!)
```

## 10. Rebuilding

```bash
docker compose build --no-cache backend    # backend only
docker compose up -d                       # recreate changed containers
```

For `VITE_*` / frontend changes, rebuild the frontend image too:

```bash
docker compose build frontend
docker compose up -d
```

## 11. Troubleshooting

- **Backend unhealthy** — `docker compose logs backend`, then check
  `docker compose exec backend python -c "import phronesisml; print(phronesisml.__version__)"`.
  SQLite on a shared/network disk is unsupported; keep `/app/data` on the
  named volume.
- **Browser shows "Failed to fetch" for API calls** — the frontend bundle was
  built with `VITE_API_BASE_URL`/`VITE_WS_BASE_URL` pointing at an origin the
  browser cannot reach (e.g. leftover `http://localhost:8000`). Rebuild with
  the relative `/api/v1` values.
- **Empty lists / missing data** — `SEED_SAMPLE_DATASETS=0` was set, or the
  storage/db volumes were recreated (`down -v`).
- **401 / auth errors** — depends on `AUTH_MODE`. With `disabled` (default)
  the API needs no token, so a 401 means an extra layer (e.g. SSO gateway) was
  added. With `AUTH_MODE=supabase`, every `/api/v1/**` and run WebSocket
  requires a valid Supabase access token; a 401 means the browser has no
  session (login is required) or the token is expired/invalid. Check that
  `VITE_SUPABASE_URL`/`VITE_SUPABASE_PUBLISHABLE_KEY` were baked into the
  frontend image and that `SUPABASE_URL` (plus a JWT secret or JWKS URL) are
  set on the backend.

## 12. Hosted production deployment (Vercel + Render + Supabase)

The recommended public topology runs the same application on managed
infrastructure — no self-hosted Postgres or storage:

```
Browser
  ├── ► https://<vercel-domain>            Vercel (static SPA)
  │                                     React+Vite bundle, rootDir=frontend,
  │                                     vercel.json rewrites all routes to
  │                                     /index.html (React Router HTML5 history)
  │
  ├── ► https://<render-app>.onrender.com/api/v1/**   Render (Web Service)
  ├── ► wss://<render-app>.onrender.com/api/v1/ws/**   single uvicorn on $PORT
  │                                     Dockerfile; persistent disk -> /app/storage
  └── ► Supabase Auth + PostgreSQL        JWT (email/password) + DATABASE_URL
```

Configuration lives in the repo:

- `render.yaml` — Render Blueprint for the backend. The service binds
  `AUTH_MODE=supabase`, `SEED_SAMPLE_DATASETS=0` (the sample `data/` files are
  not copied into the image), and a **persistent disk** named
  `phronesisml-storage` mounted at `/app/storage` (10 GB) which covers the four
  filesystem storage directories (`datasets/`, `runs/`, `artifacts/`,
  `reports/`). `healthCheckPath: /api/v1/health` matches the app's own
  no-auth, no-ML health probe (DB `SELECT 1` + storage writability + deps).
- `frontend/vercel.json` — catch-all rewrite so deep links like `/runs/...`
  load the SPA instead of 404ing. Vercel project **Root Directory** must be
  `frontend/` (the repo root has no package.json).

### Environment for the hosted backend (Render environment variables)

| Variable | Example / note |
| --- | --- |
| `AUTH_MODE` | `supabase` |
| `DATABASE_URL` | Supabase **project database** `postgresql://<user>:<pass>@<host>:5432/<db>`. The bare `postgresql://` scheme is rewritten to the `psycopg` driver automatically (`backend/app/config.py::normalize_database_url`), so use the URL exactly as Supabase shows it — do **not** add `+psycopg` yourself. |
| `SUPABASE_URL` | Supabase project URL (also drives issuer/JWKS) |
| `SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL` | Server-only token verification (keep out of any frontend env) |
| `CORS_ORIGINS` | Comma-separated, **including the `https://` Vercel domain** (e.g. `https://phronesisml.vercel.app`). Wildcards are not used with authenticated requests; omit only if the SPA and API are same-origin. |
| `SEED_SAMPLE_DATASETS` | `0` (set by `render.yaml`) |
| storage dirs | Optional overrides (e.g. `DATA_STORAGE_DIR`...). Defaults resolve under the disk mount at `/app/storage/*`. |

The `sync: false` entries in `render.yaml` (`DATABASE_URL`, `SUPABASE_URL`,
`SUPABASE_JWT_SECRET`, `SUPABASE_JWKS_URL`, `CORS_ORIGINS`) are placeholders so
secrets never live in the repo — finalize their values in the Render dashboard
after the first deploy.

### Frontend build-time variables (Vercel)

Baked into the SPA bundle by Vite (all public):

| Variable | Value |
| --- | --- |
| `VITE_API_BASE_URL` | `https://<render-app>.onrender.com/api/v1` |
| `VITE_WS_BASE_URL` | `https://<render-app>.onrender.com/api/v1` (the client converts `http->ws`/`https->wss` automatically) |
| `VITE_SUPABASE_URL` | Same project URL as the backend |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_...` |
| `VITE_DEMO_MODE` | `false` |

Server-only values (`DATABASE_URL`, `SUPABASE_JWT_SECRET`, Supabase service-role
key) must never be added as Vercel variables.

### Migration on the hosted backend

Run Alembic once against the hosted database from the repo (after the backend
image's first deploy, `init_db` creates schema only if absent — an explicit
migration is still required to guarantee `0003_rls_policies` RLS on
PostgreSQL):

```bash
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db> \
  .venv/bin/alembic -c backend/alembic.ini upgrade head
```

The chain is additive and idempotent for both upgrade paths: a **fresh** DB
(`0001` already builds current ORM metadata including `user_id`) and a
**legacy** DB both reach `0003_rls_policies (head)`
(`0002` inspects the live schema and only adds what is missing).

### Hosted-topology limitations

- **Single instance.** The backend is one uvicorn process; run workers are
  in-process threads. Render handles failover via health checks, but do not
  scale to multiple instances — a second instance would run duplicate
  workers. On restart, `reconcile_interrupted_runs` marks `queued`/`running`
  runs as `failed` (honest state, no half-written rows).
- **Persistent disk only.** Uploaded datasets/models live on the `/app/storage`
  disk at "*Disk*" storage class; a disk delete loses datasets and run
  artifacts (except what is re-derivable). Back that directory up.
- **Secrets in dashboards.** Pointers above; never commit `.env`, `.env.*`,
  or secrets. `.env`, `.env.local` and their `frontend/` equivalents are
  gitignored.
- **PostgreSQL differences.** Queries and migration are PostgreSQL-compatible;
  tz-aware datetimes are written into `timestamp without time zone` columns and
  read back as-is — verified to match, but confirm on a live project before
  relying on cross-timezone semantics.

## 13. Production limitations

Documented behaviour of the *current* application — Docker does not remove
these:

- **Authentication depends on `AUTH_MODE`.** With the default
  `AUTH_MODE=disabled` the FastAPI surface is single-tenant and open (suitable
  for local/dev); do **not** expose that published port to the public internet
  without an auth gateway. For a public deployment set `AUTH_MODE=supabase`
  (Supabase Auth + PostgreSQL) so every endpoint and WebSocket validates a JWT
  and enforces per-user ownership (see `project_docs/supabase.md`).
- **SQLite / single node.** One process, one SQLite file, in-process write
  serialisation. Not horizontally scalable; the application enforces a single
  uvicorn worker for correctness. (Supabase deployments use their hosted
  PostgreSQL instead of the local SQLite file.)
- **No TLS.** Nginx listens on plain HTTP `:80`. Terminate TLS at an edge
  proxy/reverse-proxy with these settings *above* Nginx, or add a TLS
  termination layer first.
- **No cloud infra**: no object storage, message broker, or external DB was
  added — none is required by the current architecture.
- **Host networking caveat:** macOS Docker Desktop runs Linux containers in a
  VM; `localhost` inside containers differs from the macOS host. Always access
  the app via the published port (`http://localhost:8080`).