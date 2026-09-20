"""Reports router (``/api/runs/{run_id}/report``)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.report_schemas import ReportInfo
from backend.app.services import report_service

router = APIRouter()


@router.get("/{run_id}/report", response_model=ReportInfo)
def get_report(run_id: str, format: str = Query("markdown")) -> dict:
    result = report_service.get(run_id, format)
    if result is None:
        raise HTTPException(status_code=404, detail="ReportNotFound")
    return result
