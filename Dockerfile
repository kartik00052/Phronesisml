# ── Build stage ──────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# System deps needed at build time (polars, shap native libs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
# Install package with API extras only (no dev/test deps in image)
COPY phronesisml/ phronesisml/
RUN pip install --no-cache-dir --prefix=/install ".[api]"


# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

LABEL maintainer="Kartik Sharma <kartiksharma18852@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/kartik00052/PhronesisML"

# Minimal runtime deps (libgomp for sklearn, libstdc++ for polars)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy full source code
WORKDIR /app
COPY . .

# Non-root user
RUN groupadd -r phronesisml && useradd -r -g phronesisml -d /app phronesisml && \
    chown -R phronesisml:phronesisml /app
USER phronesisml

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "phronesisml.interfaces.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
