"""Health + capabilities routers (``/api/health``, ``/api/capabilities``)."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.health_schemas import CapabilitiesReport, HealthReport
from backend.app.services import health_service

router = APIRouter()
capabilities_router = APIRouter()


@router.get("", response_model=HealthReport)
def get_health() -> dict:
    return health_service.health()


@capabilities_router.get("", response_model=CapabilitiesReport)
def get_capabilities() -> dict:
    return health_service.capabilities()
