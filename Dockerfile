# syntax=docker/dockerfile:1

# ─── Build stage: install the locked SDK + web extras into a venv ──────────
# Uses `uv sync --extra web --frozen` so dependencies come from uv.lock
# (Python 3.12 matches .python-version and pyproject requires-python).
FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=3.12 \
    PIP_NO_CACHE_DIR=1

RUN pip install --no-cache-dir "uv>=0.5"

WORKDIR /app

# The lock pins every dependency; only the sources needed to build the
# project package are copied here (phronesisml SDK). `backend/` itself is
# copied in the runtime stage — it is not part of the built distribution.
COPY pyproject.toml uv.lock .python-version ./
COPY README.md ./
COPY phronesisml/ ./phronesisml/

RUN uv sync --extra web --frozen --no-dev

# ─── Runtime stage: FastAPI + SDK, non-root, no reload, no debug ──────────
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system phronesis \
    && useradd --system --gid phronesis --create-home phronesis

WORKDIR /app

# .venv first (editable SDK install references /app/phronesisml), then the
# backend package, config, and migration sources.
COPY --from=builder /app/.venv /app/.venv

COPY pyproject.toml uv.lock alembic.ini ./
COPY backend/ ./backend/
COPY phronesisml/ ./phronesisml/

# Persistent application directories (mounted as volumes in Compose).
RUN mkdir -p /app/data \
        /app/storage/datasets \
        /app/storage/runs \
        /app/storage/artifacts \
        /app/storage/reports \
    && chown -R phronesis:phronesis /app

USER phronesis

EXPOSE 8000

# The application's own health endpoint is the source of truth for database,
# storage, and dependency availability. The port follows $PORT (Render uses a
# per-service ephemeral port) and falls back to 8000 locally / in Compose.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["sh", "-c", "python -c \"import urllib.request,json,os; json.load(urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/v1/health', timeout=5))\""]

# Single process: the app serialises SQLite writes with an in-process lock
# (see backend/app/db/database.py), so multiple workers are not used.
# Render injects $PORT (defaulting to 8000 for local/Compose runs).
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]