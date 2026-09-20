"""Datasets router (``/api/v1/datasets``).

Uploads are streamed to disk (never buffered fully in memory), then
inspected with the real SDK loaders/profiler/validators.

Every endpoint is user-scoped: rows are always filtered by the authenticated
Supabase user, and accessing a dataset you do not own returns 404 (hidden).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from backend.app.api.deps import not_found
from backend.app.auth.deps import get_current_user, require_owned_dataset
from backend.app.auth.verifier import AuthUser
from backend.app.config import get_settings
from backend.app.db import repositories
from backend.app.schemas.common import PageResult
from backend.app.schemas.dataset import (
    Dataset,
    DatasetDeleteResult,
    DatasetPreviewPage,
    DatasetSchemaView,
    DatasetSummary,
    DatasetUploadResult,
)
from backend.app.services import dataset_service
from backend.app.services.dataset_service import UploadRejectedError

router = APIRouter()


@router.get("", response_model=PageResult[DatasetSummary])
def list_datasets(
    user: Annotated[AuthUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    format: str | None = Query(None),
) -> dict[str, Any]:
    items, total = repositories.list_datasets(
        page=page, page_size=pageSize, search=search, format=format, user_id=user.user_id
    )
    return {
        "items": [dataset_service.dataset_summary(ds) for ds in items],
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "hasMore": page * pageSize < total,
    }


@router.get("/{dataset_id}", response_model=Dataset)
def get_dataset(
    dataset_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    require_owned_dataset(dataset_id, user.user_id)
    dataset = repositories.get_dataset(dataset_id, user_id=user.user_id)
    if dataset is None:
        raise not_found("Dataset", dataset_id)
    return dataset_service.dataset_to_dict(dataset)


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewPage)
def dataset_preview(
    dataset_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    require_owned_dataset(dataset_id, user.user_id)
    preview = dataset_service.dataset_preview(dataset_id, page=page, page_size=pageSize)
    if preview is None:
        raise not_found("Dataset", dataset_id)
    return preview


@router.get("/{dataset_id}/schema", response_model=DatasetSchemaView)
def dataset_schema(
    dataset_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    require_owned_dataset(dataset_id, user.user_id)
    schema = dataset_service.dataset_schema(dataset_id)
    if schema is None:
        raise not_found("Dataset", dataset_id)
    return schema


@router.get("/{dataset_id}/eda")
def dataset_eda(
    dataset_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    require_owned_dataset(dataset_id, user.user_id)
    profile = dataset_service.dataset_eda(dataset_id)
    if profile is None:
        raise not_found("Dataset", dataset_id)
    return profile


@router.post("", response_model=DatasetUploadResult, status_code=201)
async def upload_dataset(
    user: Annotated[AuthUser, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> dict[str, Any]:
    settings = get_settings()
    try:
        size = _stream_upload_size(file, settings.max_upload_bytes)
    except dataset_service.UploadRejectedError as exc:
        raise HTTPException(status_code=413, detail=exc.code) from exc
    file.file.seek(0)
    try:
        dataset = dataset_service.upload_dataset(
            dataset_id=None,
            filename=file.filename or "upload.bin",
            size_bytes=size,
            content=file.file,
            settings=settings,
            user_id=user.user_id,
        )
    except UploadRejectedError as exc:
        code = getattr(exc, "code", "UploadRejectedError")
        status = 415 if code in {"UnsupportedFormat", "UnsupportedColumnType"} else 422
        raise HTTPException(status_code=status, detail=code) from exc
    return {"dataset": dataset}


@router.post(
    "/upload", response_model=DatasetUploadResult, status_code=201, include_in_schema=False
)
async def upload_dataset_alias(
    user: Annotated[AuthUser, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> dict[str, Any]:
    return await upload_dataset(user, file)


@router.delete("/{dataset_id}", response_model=DatasetDeleteResult)
def delete_dataset(
    dataset_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return dataset_service.delete_dataset(dataset_id, user_id=user.user_id)


def _stream_upload_size(file: UploadFile, max_bytes: int) -> int:
    """Count bytes while streaming read + verify the size limit (no full buffering)."""
    size = 0
    while chunk := file.file.read(1024 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise UploadRejectedError("FileTooLarge", "Upload exceeds the configured size limit.")
    return size
