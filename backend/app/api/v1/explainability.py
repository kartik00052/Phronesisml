"""Explainability router (``/api/runs/{run_id}/explainability``)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.deps import not_found
from backend.app.auth.deps import get_current_user, require_owned_run
from backend.app.auth.verifier import AuthUser
from backend.app.schemas.explainability_schemas import ExplainabilityView
from backend.app.services import explainability_service

router = APIRouter()


@router.get("/{run_id}/explainability", response_model=ExplainabilityView)
def get_explainability(
    run_id: str, user: Annotated[AuthUser, Depends(get_current_user)]
) -> dict:
    require_owned_run(run_id, user.user_id)
    result = explainability_service.get(run_id)
    if result is None:
        raise not_found("Explainability", run_id)
    return result
