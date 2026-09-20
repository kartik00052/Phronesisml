"""Reports router (``/api/runs/{run_id}/report``)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.auth.deps import get_current_user, require_owned_run
from backend.app.auth.verifier import AuthUser
from backend.app.schemas.report_schemas import ReportInfo
from backend.app.services import report_service

router = APIRouter()


@router.get("/{run_id}/report", response_model=ReportInfo)
def get_report(
    run_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    format: str = Query("markdown"),
) -> dict:
    require_owned_run(run_id, user.user_id)
    result = report_service.get(run_id, format)
    if result is None:
        raise HTTPException(status_code=404, detail="ReportNotFound")
    return result
