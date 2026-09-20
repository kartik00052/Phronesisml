"""Models router (``/api/runs/{run_id}/models``)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.auth.deps import get_current_user, require_owned_run
from backend.app.auth.verifier import AuthUser
from backend.app.schemas.model_schemas import ModelDetail, ModelRankingRow
from backend.app.services import model_service

router = APIRouter()


@router.get("/{run_id}/models", response_model=list[ModelRankingRow])
def list_models(
    run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]
) -> list[dict]:
    require_owned_run(run_id, user.user_id)
    result = model_service.list_models(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="RunNotFound")
    return result


@router.get("/{run_id}/models/{model:path}", response_model=ModelDetail)
def get_model_detail(
    run_id: str, model: str, user: Annotated[AuthUser, Depends(get_current_user)]
) -> dict:
    require_owned_run(run_id, user.user_id)
    result = model_service.get_model_detail(run_id, model)
    if result is None:
        raise HTTPException(status_code=404, detail="ModelNotFound")
    return result
