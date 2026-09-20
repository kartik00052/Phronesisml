"""Stats router (``/api/stats``)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.auth.deps import get_current_user
from backend.app.auth.verifier import AuthUser
from backend.app.schemas.stats_schemas import DashboardStats
from backend.app.services import stats_service

router = APIRouter()


@router.get("", response_model=DashboardStats)
def dashboard(user: Annotated[AuthUser, Depends(get_current_user)]) -> dict:
    return stats_service.dashboard(user_id=user.user_id)
