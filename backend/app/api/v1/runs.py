"""Runs router (``/api/v1/runs``): create, list, inspect, cancel, restore,
delete, logs, recent, dataset, and prediction.

Every endpoint is user-scoped. Runs/datasets you do not own are hidden
(404). The authenticated identity always comes from the verified token.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.deps import not_found
from backend.app.auth.deps import get_current_user, require_owned_dataset, require_owned_run
from backend.app.auth.verifier import AuthUser
from backend.app.schemas.common import PageResult
from backend.app.schemas.dataset import Dataset
from backend.app.schemas.prediction_schemas import PredictionRequest, PredictionResponse
from backend.app.schemas.run_schemas import RecentRunActivity, Run, RunRequest, RunSummary
from backend.app.services import prediction_service, run_service

router = APIRouter()


@router.post("", response_model=Run, status_code=201)
def create_run(
    payload: RunRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    if payload.datasetId:
        require_owned_dataset(payload.datasetId, user.user_id)
    try:
        return run_service.create_run(payload.model_dump(), user_id=user.user_id)
    except run_service.RunError as exc:
        raise HTTPException(status_code=422, detail=exc.code) from exc


@router.get("", response_model=PageResult[RunSummary])
def list_runs(
    user: Annotated[AuthUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    status: str | None = None,
    datasetId: str | None = None,
    search: str | None = None,
    taskType: str | None = None,
    sort: str | None = None,
    order: str | None = Query(None, pattern="^(asc|desc)$"),
) -> dict[str, Any]:
    return run_service.list_runs(
        page=page,
        page_size=pageSize,
        status=status,
        dataset_id=datasetId,
        search=search,
        task_type=taskType,
        sort=sort,
        order=order,
        user_id=user.user_id,
    )


@router.get("/recent", response_model=list[RecentRunActivity])
def recent_runs(user: Annotated[AuthUser, Depends(get_current_user)]) -> list[dict[str, Any]]:
    return run_service.recent_activity(limit=8, user_id=user.user_id)


@router.get("/{run_id}", response_model=Run)
def get_run(run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]) -> dict[str, Any]:
    require_owned_run(run_id, user.user_id)
    detail = run_service.get_run_detail(run_id)
    if detail is None:
        raise not_found("Run", run_id)
    return detail


@router.delete("/{run_id}", response_model=dict[str, Any])
def delete_run(run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]) -> dict[str, Any]:
    require_owned_run(run_id, user.user_id)
    try:
        return run_service.delete_run(run_id)
    except run_service.RunError as exc:
        raise not_found("Run", run_id) from exc


@router.post("/{run_id}/cancel", response_model=Run)
def cancel_run(run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]) -> dict[str, Any]:
    require_owned_run(run_id, user.user_id)
    try:
        return run_service.cancel_run(run_id)
    except run_service.RunError as exc:
        raise HTTPException(status_code=409, detail=exc.code) from exc


@router.post("/{run_id}/restore", response_model=Run)
def restore_run(
    run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]
) -> dict[str, Any]:
    require_owned_run(run_id, user.user_id)
    try:
        return run_service.restore_run(run_id)
    except run_service.RunError as exc:
        raise not_found("Run", run_id) from exc


@router.get("/{run_id}/logs", response_model=list[str])
def run_logs(run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]) -> list[str]:
    require_owned_run(run_id, user.user_id)
    try:
        return run_service.run_logs(run_id)
    except run_service.RunError as exc:
        raise not_found("Run", run_id) from exc


@router.get("/{run_id}/dataset", response_model=Dataset | None)
def run_dataset(
    run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]
) -> dict[str, Any] | None:
    require_owned_run(run_id, user.user_id)
    try:
        return run_service.run_dataset(run_id)
    except run_service.RunError:
        raise not_found("Run", run_id) from None


@router.post("/{run_id}/predict", response_model=PredictionResponse)
def predict(
    run_id: str,
    payload: PredictionRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    # A user can only predict with models fitted on their own runs; the
    # ownership check also prevents arbitrary run-artifact path access.
    require_owned_run(run_id, user.user_id)
    try:
        return prediction_service.predict(run_id, payload.samples)
    except prediction_service.PredictionError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc
