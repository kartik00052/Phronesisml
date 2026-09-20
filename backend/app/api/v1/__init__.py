"""API v1 router aggregate. Mounts every domain router under the
``/api/v1`` prefix; the WebSocket endpoint lives at ``/api/v1/ws/...``.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1 import (
    artifacts,
    datasets,
    engine,
    explainability,
    health,
    models,
    pipeline,
    reports,
    runs,
    stats,
    ws,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(health.capabilities_router, prefix="/capabilities", tags=["capabilities"])
api_router.include_router(engine.router, prefix="/engine", tags=["engine"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(pipeline.router, prefix="/runs", tags=["pipeline"])
api_router.include_router(models.router, prefix="/runs", tags=["models"])
api_router.include_router(explainability.router, prefix="/runs", tags=["explainability"])
api_router.include_router(artifacts.router, prefix="/runs", tags=["artifacts"])
api_router.include_router(reports.router, prefix="/runs", tags=["reports"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(ws.router, prefix="", tags=["ws"])
