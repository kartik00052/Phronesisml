"""Pipeline router (``/api/runs/{run_id}/pipeline``)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.schemas.pipeline_schemas import (
    PipelineOverview,
    PipelineProgress,
    StageDetail,
)
from backend.app.services import pipeline_service

router = APIRouter()


@router.get("/{run_id}/pipeline", response_model=PipelineOverview)
def overview(run_id: str) -> dict:
    result = pipeline_service.overview(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="RunNotFound")
    return result


@router.get("/{run_id}/pipeline/stages", response_model=list[StageDetail])
def list_stages(run_id: str) -> list[dict]:
    result = pipeline_service.list_stages(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="RunNotFound")
    return result


@router.get("/{run_id}/pipeline/progress", response_model=PipelineProgress)
def progress(run_id: str) -> dict:
    result = pipeline_service.progress(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="RunNotFound")
    return result
