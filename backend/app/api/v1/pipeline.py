"""Pipeline router (``/api/runs/{run_id}/pipeline``)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.auth.deps import get_current_user, require_owned_run
from backend.app.auth.verifier import AuthUser
from backend.app.schemas.pipeline_schemas import (
    PipelineOverview,
    PipelineProgress,
    StageDetail,
)
from backend.app.services import pipeline_service

router = APIRouter()


@router.get("/{run_id}/pipeline", response_model=PipelineOverview)
def overview(
    run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]
) -> dict:
    require_owned_run(run_id, user.user_id)
    result = pipeline_service.overview(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="RunNotFound")
    return result


@router.get("/{run_id}/pipeline/stages", response_model=list[StageDetail])
def list_stages(
    run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]
) -> list[dict]:
    require_owned_run(run_id, user.user_id)
    result = pipeline_service.list_stages(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="RunNotFound")
    return result


@router.get("/{run_id}/pipeline/progress", response_model=PipelineProgress)
def progress(
    run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]
) -> dict:
    require_owned_run(run_id, user.user_id)
    result = pipeline_service.progress(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="RunNotFound")
    return result
