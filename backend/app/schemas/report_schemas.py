"""Report schemas — 1:1 with ``frontend/src/types/report.ts``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReportFormat = Literal["markdown", "html", "json", "pdf"]


class ReportInfo(BaseModel):
    runId: str = Field(alias="runId")
    format: str
    title: str = ""
    created: str = ""
    reportLength: int = Field(default=0, alias="reportLength")
    reportLines: int = Field(default=0, alias="reportLines")
    downloadUrl: str | None = Field(default=None, alias="downloadUrl")
    markdown: str | None = None
    html: str | None = None
    json: str | None = None
    sections: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="allow")
