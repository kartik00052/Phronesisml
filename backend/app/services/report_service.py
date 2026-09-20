"""Report service — run report composed from real run state + SDK artifacts.

DTO follows ``frontend/src/types/report.ts``.  Supported formats:
``markdown`` (report.md), ``html`` (report.html), ``json`` (pipeline.json).
"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.app.db import repositories
from backend.app.db.repositories import iso
from backend.app.services.artifact_service import artifact_path

_SECTION_RE = re.compile(r"^#{1,2}\s+(.+)$")


def _read_text(run_id: str, name: str) -> str | None:
    path = artifact_path(run_id, name)
    if path is None or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _read_json(run_id: str, name: str) -> dict[str, Any] | None:
    path = artifact_path(run_id, name)
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def get(run_id: str, report_format: str = "markdown") -> dict[str, Any] | None:
    run = repositories.get_run(run_id)
    if run is None:
        return None

    if report_format == "json":
        pipeline = _read_json(run_id, "pipeline.json")
        if pipeline is None:
            return None
        raw = json.dumps(pipeline, indent=2, default=str)
        return {
            "runId": run.id,
            "format": "json",
            "title": f"Pipeline report — {run.dataset_name or run.id}",
            "created": iso(run.completed_at or run.updated_at) or "",
            "reportLength": len(raw),
            "reportLines": raw.count("\n") + 1,
            "downloadUrl": f"/api/v1/runs/{run.id}/report?format=json",
            "json": raw,
            "sections": _sections(pipeline),
        }

    if report_format == "html":
        html = _read_text(run_id, "report.html")
        if html is None:
            return None
        return {
            "runId": run.id,
            "format": "html",
            "title": f"HTML report — {run.dataset_name or run.id}",
            "created": iso(run.completed_at or run.updated_at) or "",
            "reportLength": len(html),
            "reportLines": html.count("\n") + 1,
            "downloadUrl": f"/api/v1/runs/{run.id}/report?format=html",
            "html": html,
            "sections": [],
        }

    md = _read_text(run_id, "report.md")
    if md is None:
        return None
    return {
        "runId": run.id,
        "format": "markdown",
        "title": f"Analysis report — {run.dataset_name or run.id}",
        "created": iso(run.completed_at or run.updated_at) or "",
        "reportLength": len(md),
        "reportLines": md.count("\n") + 1,
        "downloadUrl": f"/api/v1/runs/{run.id}/report?format=markdown",
        "markdown": md,
        "sections": [match.group(1).strip() for match in _SECTION_RE.finditer(md)],
    }


def _sections(pipeline: dict[str, Any]) -> list[str]:
    sections: list[str] = []
    if pipeline.get("run") is not None:
        sections.append("Run")
    for key in ("dataset", "target", "model", "metrics", "explanation"):
        if pipeline.get(key) is not None:
            sections.append(key.title())
    if pipeline.get("narrative"):
        sections.append("Narrative")
    return sections
