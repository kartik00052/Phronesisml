# PhronesisML — Supabase Authentication & PostgreSQL

PhronesisML ships with **two runtime modes**, switched by `AUTH_MODE`:

| Mode            | `AUTH_MODE` | Database     | Auth                           |
| --------------- | ----------- | ------------ | ------------------------------ |
| Local / dev     | `disabled`  | SQLite       | Single-tenant `local-dev` id   |
| Supabase deploy | `supabase`  | Supabase PostgreSQL | Supabase Auth (email/password), JWT |

Both modes share the **same code path** — only token resolution differs
(`backend.app.auth.deps.get_current_user`). Ownership isolation is enforced
server-side in both modes; the token only changes *which* user you are.

## Architecture

```
React (Supabase JS -> session JWT)
   │  Authorization: Bearer <access-token>
   ▼
FastAPI (get_current_user -> verify_token vs JWT secret / JWKS)
   │  require_owned_run / require_owned_dataset  (404 = hidden)
   ▼
SQLAlchemy ──► Supabase PostgreSQL
   ▲
RLS = defense-in-depth only (the app never uses browser-side table access)
```

- The **React app never reads application tables directly.** It only logs in
  via `supabase-js` to obtain a session token and forwards it to FastAPI.
- The backend uses the **postgres user / a privileged role** (bypasses RLS);
  RLS policies exist so a leaked anon/authenticated key cannot read other
  users' rows straight over the wire.
- The authenticated identity always comes from the **verified JWT `sub`** —
  never from a client-supplied `user_id`/`email`/`owner_id`. Foreign
  resources return **404 (hidden)**, never 403 or a "exists" hint.

## Required environment variables

### Backend (server-only — never shipped in the frontend bundle)

| Variable              | Required for `supabase`? | Meaning                                   |
| --------------------- | ------------------------ | ----------------------------------------- |
| `AUTH_MODE`           | yes (`=supabase`)        | Enables JWT verification                  |
| `SUPABASE_URL`        | yes                      | Project URL; derives issuer + JWKS URL    |
| `SUPABASE_JWT_SECRET` | one of secret / JWKS     | Server-side HS256 shared secret           |
| `SUPABASE_JWKS_URL`   | one of secret / JWKS     | JWKS endpoint for RSA/EdDSA projects      |
| `DATABASE_URL`        | yes                      | `postgresql://…` to the Supabase database |
| `SUPABASE_JWT_ISSUER` / `SUPABASE_JWT_AUDIENCE` | optional | Explicit overrides; default audience `authenticated` |

### Frontend (public, baked into the Vite build)

| Variable                        | Meaning                       |
| ------------------------------- | ----------------------------- |
| `VITE_SUPABASE_URL`             | Same project URL              |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Public publishable key (`sb_publishable_…`) |

Only these two `VITE_*` values are passed to the frontend Docker build
(`docker-compose.yml` → `frontend/Dockerfile`). Server-only values
(`DATABASE_URL`, `SUPABASE_JWT_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`) must
never appear in the frontend build arguments.

There is currently **no** `SUPABASE_SERVICE_ROLE_KEY` usage in the backend —
management/cleanup via the admin API would need one, but the app itself does
not use it.

## Database migration

The backend auto-creates/upgrades the schema on startup via `init_db`, but a
Supabase deployment should use Alembic explicitly so `0003_rls_policies`
(PostgreSQL-only RLS) is applied:

```bash
# Offline (from the repo root)
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db> \
  .venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/alembic -c backend/alembic.ini current

# Or inside the container
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db> \
  docker compose run --rm backend alembic upgrade head
```

Migration chain (non-destructive, additive):

```
0001_initial ──► 0002_user_ownership ──► 0003_rls_policies
                    (+user_id on datasets/runs,          (RLS on PostgreSQL only;
                     indexes)                              no-op on SQLite)
```

`0003` enables RLS on the tenant tables, creates owner-scoped policies
(`datasets_owner_all`, `runs_owner_all`, child-table select policies scoped
through `runs.user_id`), and revokes `anon` access while granting `SELECT` to
`authenticated`. It deliberately does **not** add `FORCE ROW LEVEL SECURITY`
so the backend's own (privileged) connection is never locked out.

## Runtime notes

- **Local/unit tests** keep `AUTH_MODE=disabled` + SQLite; the `supabase`
  code path is covered hermetically by `backend/tests/test_supabase_auth.py`
  (minted HS256 tokens, no real project needed): missing/invalid/expired →
  401, identity from `sub`, 404 isolation for datasets/runs/artifacts/
  reports/prediction, and the WebSocket 4401/4404 matrix.
- **Live verification** against a real project additionally requires either
  an auto-confirmed signup or access to confirmation emails — see the
  section below.

## Live verification status

Live verification against the configured project is only possible when a real
authenticated session can be produced. The project currently requires **email
confirmation for signup** (`mailer_autoconfirm: false`), so obtaining a JWT
session requires confirming the verification email; the anon/publishable key
cannot create a confirmed session on its own. See the final-pass report for
what was verified (configuration endpoint reachable, hermetic auth suite) and
what was **NOT RUN** (live signup/login, live PostgreSQL/Alembic/RLS).

## Hosted deployment status (Vercel + Render + Supabase)

Tracked separately from feature code so "verified in CI/hermetic tests" is never
confused with "verified against a live deployment".

### IMPLEMENTED (in the repo, not yet deployed)

- **psycopg driver routing** — `backend/app/config.py` gained
  `normalize_database_url()`: a bare `postgresql://`/`postgres://` URL is
  rewritten to `postgresql+psycopg://` everywhere an engine or Alembic is
  created (`database.py`, `alembic/env.py`). The project pins `psycopg[binary]`
  (psycopg 3); SQLAlchemy's default for the bare scheme is psycopg2, which is
  **not** installed. Supabase's project database URL can now be used verbatim.
- **Fresh-DB-safe migrations** — `0002_user_ownership` is idempotent
  (inspects the live schema and adds `user_id`/indexes only if missing). This
  matters because `0001` builds from *current* ORM metadata, so a brand-new
  database already contains `user_id`. Verified locally: a fresh SQLite DB runs
  `upgrade head` → `0003_rls_policies (head)`, and a legacy 0001-only DB also
  reaches head.
- **Render-ready image** — `Dockerfile` CMD now serves `uvicorn` on the
  `PORT` environment variable (fallback `8000`) and the `HEALTHCHECK` probes
  the same port.
- **Deploy configs** — `render.yaml` (web service, health path
  `/api/v1/health`, persistent disk at `/app/storage`, secrets kept
  `sync: false` as dashboard-only values) and `frontend/vercel.json` (SPA
  catch-all rewrite; Vercel project Root Directory = `frontend/`).

### VERIFIED (hermetic / local)

- Alembic upgrade chains: fresh + legacy, both end at head; exit 0.
- Driver mapping check: `create_engine(...).dialect.driver == "psycopg"`.
- Full suites pass: backend `pytest` (58 passed / 3 deselected), `ruff check`
  and format on changed files, frontend `typecheck`/`lint`/tests (64)/`build`,
  and the SDK `backend/tests/e2e_smoke.py` (ALL PASS).
- Secret audit: no service-role key, no `DATABASE_URL`, no JWT secret in the
  frontend sources or production bundle; server-only env names absent from
  `frontend/`.

### LIVE-VERIFIED: NOT RUN (requires a real deployed environment)

- `docker build`/`docker compose up` runtime verification (no Docker daemon
  in this environment).
- Alembic/RLS against a live Supabase PostgreSQL database (no `DATABASE_URL`
  available here; must be run once as part of the first deploy).
- Real email/password signup + confirmed JWT session against the deployed app
  (the project requires **email confirmation** — `mailer_autoconfirm: false` —
  and signup returned HTTP 429 `over_email_send_rate_limit` during this pass).
- Cross-timezone datetime semantics (tz-aware values into
  `timestamp without time zone`) — expected to round-trip; confirm on live PG.
