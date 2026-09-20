"""Shared HTTP schemas — envelopes, pagination, list-query DTO, and general purpose helpers."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    """Paged collection envelope — camelCase to match the frontend ``Page<T>``."""

    items: list[T]
    total: int
    page: int
    pageSize: int = Field(alias="pageSize")
    hasMore: bool = Field(alias="hasMore")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ListQuery(BaseModel):
    """Shared pagination / filter query object."""

    page: int = 1
    pageSize: int = Field(default=50, alias="pageSize")
    sort: str | None = None
    order: str | None = None
    status: str | None = None
    taskType: str | None = Field(default=None, alias="taskType")
    datasetId: str | None = Field(default=None, alias="datasetId")
    search: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ErrorDetail(BaseModel):
    """Structured error payload — ``{"error": {code, message, details}}`` envelope."""

    code: str
    message: str
    details: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class ErrorEnvelope(BaseModel):
    """Top-level error envelope mirrored by the frontend ``ApiErrorPayload``."""

    error: ErrorDetail

    model_config = ConfigDict(extra="allow")


class OkResponse(BaseModel):
    ok: bool = True

    model_config = ConfigDict(extra="allow")
