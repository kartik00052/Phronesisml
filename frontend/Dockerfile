# syntax=docker/dockerfile:1

# ─── Build stage: lock-file install + production Vite build ───────────────
# Build context is the repository root (`docker build -f frontend/Dockerfile .`)
# so this stage can reach both `frontend/` and `nginx/nginx.conf`.
FROM node:22-alpine AS build

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_WS_BASE_URL=/api/v1
ARG VITE_DEMO_MODE=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_WS_BASE_URL=$VITE_WS_BASE_URL \
    VITE_DEMO_MODE=$VITE_DEMO_MODE

RUN corepack enable && corepack prepare pnpm@12.4.2 --activate

WORKDIR /build

# Install from the lock file before copying source (better layer caching).
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./

# `pnpm build` runs `tsc -b && vite build` (see frontend/package.json).
RUN pnpm build

# ─── Runtime stage: serve static build behind Nginx + reverse proxy ───────
FROM nginx:1.27-alpine

COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1