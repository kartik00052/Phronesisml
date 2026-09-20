"""Explainability router (``/api/runs/{run_id}/explainability``)."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import not_found
from backend.app.schemas.explainability_schemas import ExplainabilityView
from backend.app.services import explainability_service

router = APIRouter()


@router.get("/{run_id}/explainability", response_model=ExplainabilityView)
def get_explainability(run_id: str) -> dict:
    result = explainability_service.get(run_id)
    if result is None:
        raise not_found("Explainability", run_id)
    return result
