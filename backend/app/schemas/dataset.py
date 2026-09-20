"""Dataset schemas — 1:1 with ``frontend/src/types/dataset.ts``.

The top-level ``Dataset`` is the nested shape the UI consumes:
``{summary, profile, columns, validation, transformLog, preview, sheets}``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnInfo(BaseModel):
    name: str
    dtype: str | None = None
    numeric: bool = False
    categorical: bool = False
    nullCount: int = 0
    nullPercent: float = 0.0
    cardinality: int | None = None
    stats: dict[str, Any] | None = None
    topValues: dict[str, int] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Shape(BaseModel):
    rows: int
    columns: int

    model_config = ConfigDict(extra="allow")


class NumericColumnSummary(BaseModel):
    count: int
    mean: float
    std: float
    min: float
    q25: float = Field(alias="25%")
    q50: float = Field(alias="50%")
    q75: float = Field(alias="75%")
    max: float
    null_count: int

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class CategoricalColumnSummary(BaseModel):
    cardinality: int
    null_count: int
    top_values: dict[str, int]

    model_config = ConfigDict(extra="allow")


class DataProfile(BaseModel):
    shape: Shape
    column_names: list[str]
    dtypes: dict[str, str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    numeric_summary: dict[str, NumericColumnSummary]
    categorical_summary: dict[str, CategoricalColumnSummary]
    memory_bytes: int = 0

    model_config = ConfigDict(extra="allow")


class ValidationReport(BaseModel):
    shape: Shape
    dtypes: dict[str, str]
    column_names: list[str]
    null_counts: dict[str, int]
    null_columns: list[str]
    empty_columns: list[str]
    duplicate_rows: int = 0
    passed: bool

    model_config = ConfigDict(extra="allow")


class TransformEntry(BaseModel):
    action: str
    model_config = ConfigDict(extra="allow")


class DatasetPreview(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    maxRows: int = 100

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class SheetInfo(BaseModel):
    name: str
    index: int
    rows: int
    cols: int

    model_config = ConfigDict(extra="allow")


class DatasetSummary(BaseModel):
    id: str
    name: str
    path: str
    format: str
    sizeBytes: int = 0
    rows: int | None = None
    columns: int | None = None
    engine: str | None = None
    engineReason: str | None = None
    validationPassed: bool | None = None
    missingCells: int | None = None
    duplicateRows: int | None = None
    targetColumn: str | None = None
    taskType: str | None = None
    registeredAt: str | None = None
    lastUsedRunId: str | None = None
    sample: bool = False

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Dataset(BaseModel):
    summary: DatasetSummary
    profile: DataProfile
    columns: list[ColumnInfo]
    validation: ValidationReport
    transformLog: list[TransformEntry]
    preview: DatasetPreview
    sheets: list[SheetInfo]

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class DatasetUploadResult(BaseModel):
    dataset: Dataset

    model_config = ConfigDict(extra="allow")


class DatasetDeleteResult(BaseModel):
    deleted: bool
    id: str | None = None

    model_config = ConfigDict(extra="allow")


class DatasetPreviewPage(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    page: int
    pageSize: int = Field(alias="pageSize")
    totalRows: int = Field(default=0, alias="totalRows")
    hasMore: bool = Field(default=False, alias="hasMore")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class DatasetSchemaView(BaseModel):
    name: str
    columns: list[ColumnInfo]
    shape: Shape

    model_config = ConfigDict(extra="allow")


class EngineRecommendation(BaseModel):
    """Compatibility alias kept in sync with ``engine_schemas.EngineRecommendation``."""

    engine: str
    reason: str
    routing: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")
