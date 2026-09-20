"""Models router (``/api/runs/{run_id}/models``)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.schemas.model_schemas import ModelDetail, ModelRankingRow
from backend.app.services import model_service

router = APIRouter()


@router.get("/{run_id}/models", response_model=list[ModelRankingRow])
def list_models(run_id: str) -> list[dict]:
    result = model_service.list_models(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="RunNotFound")
    return result


@router.get("/{run_id}/models/{model:path}", response_model=ModelDetail)
def get_model_detail(run_id: str, model: str) -> dict:
    result = model_service.get_model_detail(run_id, model)
    if result is None:
        raise HTTPException(status_code=404, detail="ModelNotFound")
    return result
