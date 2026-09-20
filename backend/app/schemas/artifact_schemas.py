"""Artifact schemas — 1:1 with ``frontend/src/types/artifact.ts``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Artifact(BaseModel):
    name: str
    kind: str
    format: str
    sizeBytes: int = Field(default=0, alias="sizeBytes")
    status: str = "available"
    reason: str | None = None
    description: str = ""
    url: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ArtifactManifest(BaseModel):
    runId: str = Field(alias="runId")
    artifactCount: int = Field(default=0, alias="artifactCount")
    totalBytes: int = Field(default=0, alias="totalBytes")
    artifacts: list[Artifact] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ArtifactContent(BaseModel):
    name: str
    kind: str
    format: str
    sizeBytes: int = Field(default=0, alias="sizeBytes")
    content: str | None = None
    note: str | None = None
    truncated: bool | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")
