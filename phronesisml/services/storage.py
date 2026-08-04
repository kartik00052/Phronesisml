"""Storage service — persist pipeline artifacts to disk.

Extracted from ``StorageAgent`` to separate file I/O logic from
agent orchestration.  All functions are pure (no agent dependency)
and can be called directly or through the agent.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def save_artifact(
    data: Any,
    name: str,
    base_dir: str | Path,
    fmt: str = "json",
) -> dict[str, Any]:
    """Save a single artifact to disk.

    Args:
        data: Serializable payload.  ``fmt="csv"`` accepts a pandas
            DataFrame; ``fmt="txt"`` accepts a str; otherwise the payload
            is JSON-serialized (``default=str``).
        name: Artifact filename (extension added from *fmt*).
        base_dir: Directory to write into (created if missing).
        fmt: ``"json"``, ``"csv"``, ``"txt"``, or ``"md"``.

    Returns:
        A dict with ``path``, ``name``, ``fmt``, and ``bytes``.

    Raises:
        ValueError: If *fmt* is unknown.
        OSError: If disk write fails.
    """
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)

    extension = {"json": ".json", "csv": ".csv", "txt": ".txt", "md": ".md"}.get(fmt)
    if extension is None:
        msg = f"Unknown artifact format: {fmt!r}. Use json/csv/txt/md."
        raise ValueError(msg)

    path = base / f"{name}{extension}"
    if fmt == "csv":
        if not hasattr(data, "to_csv"):
            msg = "fmt='csv' requires a pandas DataFrame."
            raise TypeError(msg)
        data.to_csv(path, index=False)
        payload_bytes = path.stat().st_size
    else:
        text = data if isinstance(data, str) else json.dumps(data, indent=2, default=str)
        path.write_text(text, encoding="utf-8")
        payload_bytes = path.stat().st_size

    logger.info("Storage service: saved artifact %s (%d bytes).", path, payload_bytes)
    return {"path": str(path), "name": name, "fmt": fmt, "bytes": payload_bytes}


def load_artifact(path: str | Path) -> Any:
    """Load a saved artifact back into memory.

    ``.json`` files are parsed to Python objects; ``.csv`` files are
    read as pandas DataFrames; ``.txt`` / ``.md`` files are read as str.

    Args:
        path: Path to the artifact file.

    Returns:
        The deserialized payload.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    p = Path(path)
    if not p.is_file():
        msg = f"Artifact does not exist: {p}"
        raise FileNotFoundError(msg)

    suffix = p.suffix.lower()
    if suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    if suffix == ".csv":
        import pandas as pd

        return pd.read_csv(p)
    return p.read_text(encoding="utf-8")


def list_artifacts(base_dir: str | Path) -> dict[str, Any]:
    """List artifacts saved under a run directory.

    Args:
        base_dir: Run directory to scan (recursively).

    Returns:
        A dict with ``count`` and ``artifacts`` (list of dicts with
        ``path``, ``name``, ``extension``, ``bytes``).
    """
    base = Path(base_dir)
    if not base.is_dir():
        return {"count": 0, "artifacts": []}

    artifacts = []
    for p in sorted(base.rglob("*")):
        if p.is_file():
            artifacts.append(
                {
                    "path": str(p),
                    "name": p.name,
                    "extension": p.suffix,
                    "bytes": p.stat().st_size,
                }
            )
    return {"count": len(artifacts), "artifacts": artifacts}


def build_artifact_manifest(
    artifacts: list[str] | dict[str, Any],
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a manifest describing saved artifacts.

    Args:
        artifacts: List of file paths, or the dict returned by
            ``list_artifacts``.
        run_id: Optional run identifier for the manifest header.

    Returns:
        A JSON-serializable dict with ``run_id``, ``artifact_count``,
        ``files`` (list of path + bytes), and ``total_bytes``.
    """
    files: list[dict[str, Any]] = []
    if isinstance(artifacts, dict):
        paths = [a["path"] for a in artifacts.get("artifacts", [])]
    else:
        paths = list(artifacts)

    for path in paths:
        p = Path(path)
        files.append(
            {
                "path": str(p),
                "name": p.name,
                "bytes": p.stat().st_size if p.is_file() else 0,
            }
        )

    return {
        "run_id": run_id,
        "artifact_count": len(files),
        "files": files,
        "total_bytes": int(sum(f["bytes"] for f in files)),
    }


def save_artifacts(
    state: Any,
    base_dir: str | Path = "./Phronesis_artifacts",
) -> dict[str, Any]:
    """Persist pipeline artifacts to disk.

    Reads from: ``state.run_id``, ``state.trained_model``,
    ``state.final_report``, ``state.processed_data``,
    ``state.evaluation_report``.

    Args:
        state: The current ``WorkflowState``.
        base_dir: Base directory for artifact storage.

    Returns:
        A dict with ``artifact_uri`` and ``saved_files``.

    Raises:
        OSError: If disk write fails.
    """
    run_id = getattr(state, "run_id", None) or "default_run"
    artifact_dir = Path(base_dir) / run_id

    logger.info("Storage service: persisting artifacts to %s.", artifact_dir)

    artifact_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []

    # Save evaluation report as JSON
    eval_report = getattr(state, "evaluation_report", None)
    if eval_report is not None:
        eval_path = artifact_dir / "evaluation_report.json"
        eval_path.write_text(
            json.dumps(eval_report, indent=2, default=str),
            encoding="utf-8",
        )
        saved_files.append(str(eval_path))

    # Save final report if present
    final_report = getattr(state, "final_report", None)
    if final_report is not None:
        report_path = artifact_dir / "final_report.md"
        report_path.write_text(str(final_report), encoding="utf-8")
        saved_files.append(str(report_path))

    # Save metadata summary
    metadata = {
        "run_id": run_id,
        "target_column": getattr(state, "target_column", None),
        "task_type": getattr(state, "task_type", None),
        "best_pipeline": getattr(state, "best_pipeline", None),
        "saved_files": saved_files,
    }
    meta_path = artifact_dir / "run_metadata.json"
    meta_path.write_text(
        json.dumps(metadata, indent=2, default=str),
        encoding="utf-8",
    )
    saved_files.append(str(meta_path))

    artifact_uri = str(artifact_dir)
    logger.info(
        "Storage service: saved %d artifacts to %s.",
        len(saved_files),
        artifact_uri,
    )

    return {"artifact_uri": artifact_uri, "saved_files": saved_files}
