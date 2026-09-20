"""Engine recommendation + capabilities router (``/api/engine``)."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.engine_schemas import (
    EngineRecommendation,
    EngineRecommendRequest,
    EngineReport,
)
from backend.app.services import health_service

router = APIRouter()


@router.post("/recommend", response_model=EngineRecommendation)
def recommend_engine(payload: EngineRecommendRequest) -> dict:
    return health_service.engine_recommend(payload.model_dump())


@router.get("/capabilities", response_model=EngineReport)
def engine_capabilities() -> dict:
    return health_service.engine_capabilities()
