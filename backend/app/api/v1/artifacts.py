"""Artifacts router (``/api/runs/{run_id}/artifacts``)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.api.deps import not_found
from backend.app.schemas.artifact_schemas import ArtifactContent, ArtifactManifest
from backend.app.services import artifact_service

router = APIRouter()


@router.get("/{run_id}/artifacts", response_model=ArtifactManifest)
def manifest(run_id: str) -> dict:
    return artifact_service.manifest(run_id)


@router.get("/{run_id}/artifacts/{name:path}/content", response_model=ArtifactContent)
def content(run_id: str, name: str, maxChars: int | None = Query(None, alias="maxChars")) -> dict:
    try:
        return artifact_service.content(run_id, name, maxChars)
    except FileNotFoundError as exc:
        raise not_found("Artifact", name) from exc
