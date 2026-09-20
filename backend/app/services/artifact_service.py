"""Artifact service — manifest and content access for a run's saved artifacts.

Artifacts are written to ``settings.run_storage_dir/<run_id>`` by the run
worker; the manifest mirrors index rows and disk state.  DTO shapes follow
``frontend/src/types/artifact.ts``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.config import get_settings
from backend.app.db import repositories
from backend.app.workers.runner import _ARTIFACT_DESCRIPTIONS, _KIND_BY_EXT

_MAX_TEXT_CHARS = 250_000

_KIND_BY_NAME = {name: kind for name, (kind, _fmt) in _KIND_BY_EXT.items()}
_FORMAT_BY_NAME = {name: fmt for name, (_kind, fmt) in _KIND_BY_EXT.items()}


def artifact_dir(run_id: str) -> Path:
    # The run worker saves the artifact suite under run_storage_dir.
    return get_settings().run_storage_dir / run_id


def _safe_dir(run_id: str) -> Path | None:
    """Resolved run artifact directory, or ``None`` when run_id escapes storage."""
    storage_root = get_settings().run_storage_dir.resolve()
    resolved = (storage_root / run_id).resolve()
    if not resolved.is_relative_to(storage_root):
        return None
    return resolved


def artifact_path(run_id: str, name: str) -> Path | None:
    """Resolve an artifact path safely, or ``None`` when missing or unsafe.

    ``name`` and ``run_id`` are both treated as untrusted (they can reach
    this service via the ``{name:path}`` content route), so the resolved
    path must stay inside the run's own artifact directory — any parent
    traversal yields ``None`` instead of an out-of-bounds path.
    """
    path = _resolve_artifact(run_id, name)
    if path is not None and path.is_file():
        return path
    return None


def _resolve_artifact(run_id: str, name: str) -> Path | None:
    """Guard both run_id and name against path traversal outside storage."""
    storage_root = get_settings().run_storage_dir.resolve()
    base = (storage_root / run_id).resolve()
    if not base.is_relative_to(storage_root):
        return None
    candidate = (base / name).resolve()
    if not candidate.is_relative_to(base):
        return None
    return candidate


def artifact_exists(run_id: str, name: str) -> bool:
    return artifact_path(run_id, name) is not None


def read_artifact_text(run_id: str, name: str) -> dict[str, Any] | None:
    """Read a JSON artifact as a parsed dict (None when missing/not JSON)."""
    path = artifact_path(run_id, name)
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def manifest(run_id: str) -> dict[str, Any]:
    rows = repositories.list_artifacts(run_id)
    artifacts: list[dict[str, Any]] = []
    total_bytes = 0

    if rows:
        for row in rows:
            kind = row.kind or "pipeline"
            fmt = row.format
            size = row.size_bytes
            path = artifact_path(run_id, row.name)
            if path is not None:
                size = path.stat().st_size
            total_bytes += int(size or 0)
            artifacts.append(
                {
                    "name": row.name,
                    "kind": kind,
                    "format": fmt or _FORMAT_BY_NAME.get(row.name, "json"),
                    "sizeBytes": int(size or 0),
                    "status": row.status or "available",
                    "reason": row.reason,
                    "description": row.description or _ARTIFACT_DESCRIPTIONS.get(row.name, ""),
                    "url": f"/api/v1/runs/{run_id}/artifacts/{row.name}/content",
                }
            )
    else:
        run_dir = _safe_dir(run_id)
        for path in sorted(run_dir.iterdir()) if run_dir is not None and run_dir.is_dir() else []:
            if not path.is_file():
                continue
            name = path.name
            kind, fmt = _KIND_BY_EXT.get(name, ("pipeline", path.suffix.lstrip(".") or "json"))
            size = path.stat().st_size
            total_bytes += size
            artifacts.append(
                {
                    "name": name,
                    "kind": kind,
                    "format": fmt,
                    "sizeBytes": size,
                    "status": "available",
                    "reason": None,
                    "description": _ARTIFACT_DESCRIPTIONS.get(name, "Run artifact."),
                    "url": f"/api/v1/runs/{run_id}/artifacts/{name}/content",
                }
            )

    artifacts.sort(key=lambda item: item["name"])
    return {
        "runId": run_id,
        "artifactCount": len(artifacts),
        "totalBytes": total_bytes,
        "artifacts": artifacts,
    }


def content(run_id: str, name: str, max_chars: int | None = None) -> dict[str, Any]:
    path = _resolve_artifact(run_id, name)
    if path is None or not path.is_file():
        raise FileNotFoundError(f"artifact not found: {name}")
    limit = max_chars or _MAX_TEXT_CHARS
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise FileNotFoundError(str(exc)) from exc
    kind, fmt = _KIND_BY_EXT.get(name, ("pipeline", path.suffix.lstrip(".") or "json"))
    size = path.stat().st_size

    # Only the serialized model is binary: every other artifact in the suite
    # (json / txt / md / html) is textual and safe to preview inline.  The
    # former ``data.startswith(b"{")`` sniff misread every JSON file as binary
    # (its first bytes are '{' followed by a quote, never a bare '{').
    if fmt in {"joblib", "pkl"}:
        note = _binary_note(fmt)
        return {
            "name": name,
            "kind": kind,
            "format": fmt,
            "sizeBytes": size,
            "content": None,
            "note": note,
            "truncated": False,
        }

    text = _decode(data)
    truncated = len(text) > limit
    if truncated:
        text = text[:limit]
    return {
        "name": name,
        "kind": kind,
        "format": fmt,
        "sizeBytes": size,
        "content": text,
        "note": None,
        "truncated": truncated,
    }


def _binary_note(fmt: str) -> str:
    if fmt == "joblib":
        return "Serialized model binary (joblib). Download to reuse the fitted estimator."
    return f"Binary artifact ({fmt}). Not previewable inline — download to inspect."


def _decode(data: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return f"<binary artifact, {len(data)} bytes>"
