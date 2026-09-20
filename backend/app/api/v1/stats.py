"""Stats router (``/api/stats``)."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.stats_schemas import DashboardStats
from backend.app.services import stats_service

router = APIRouter()


@router.get("", response_model=DashboardStats)
def dashboard() -> dict:
    return stats_service.dashboard()
