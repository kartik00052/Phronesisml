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


def _unavailable(name: str, reason: str) -> dict[str, Any]:
    """Build a documented placeholder artifact for an intentionally missing output.

    Args:
        name: Logical artifact name (e.g. ``"shap"``).
        reason: Why the artifact is unavailable for this run.

    Returns:
        A JSON-serializable dict with ``status`` and ``reason``.
    """
    return {"artifact": name, "status": "unavailable", "reason": reason}


def save_artifacts(
    state: Any,
    base_dir: str | Path = "./Phronesis_artifacts",
) -> dict[str, Any]:
    """Persist the full pipeline artifact suite to disk.

    Writes the standard 17-file artifact set (``evaluation.json``,
    ``metrics.json``, ``training.json``, ``model.json``,
    ``feature_metadata.json``, ``target_detection.json``,
    ``resource_estimation.json``, ``engine_selection.json``, ``eda.json``,
    ``validation.json``, ``shap.json``, ``pipeline.json``,
    ``run_metadata.json``, ``report.md``, ``report.html``, ``config.json``,
    ``logs.txt``) plus the binary ``model.joblib`` when a trained model
    exists.  Artifacts that are intentionally unavailable for a run
    (e.g. no SHAP output for unsupervised tasks) are written as documented
    placeholders rather than silently omitted.

    Args:
        state: The current ``WorkflowState``.
        base_dir: Base directory for artifact storage.

    Returns:
        A dict with ``artifact_uri``, ``saved_files``, and ``warnings``.

    Raises:
        OSError: If disk write fails.
    """
    run_id = getattr(state, "run_id", None) or "default_run"
    artifact_dir = Path(base_dir) / run_id

    logger.info("Storage service: persisting artifacts to %s.", artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    warnings: list[str] = []

    def _write(name: str, payload: Any, fmt: str = "json") -> None:
        ext = {"json": ".json", "txt": ".txt", "md": ".md", "html": ".html"}.get(fmt, ".json")
        path = artifact_dir / name if name.endswith(ext) else artifact_dir / f"{name}{ext}"
        if fmt in ("txt", "md", "html"):
            path.write_text(str(payload), encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        saved_files.append(str(path))

    # ── Structured per-capability artifacts ──────────────────────────
    evaluation_report = getattr(state, "evaluation_report", None)
    if evaluation_report is not None:
        _write("evaluation.json", evaluation_report)
        metrics = evaluation_report.get("metrics", {})
        if metrics:
            _write("metrics.json", metrics)
        else:
            _write("metrics.json", _unavailable("metrics", "no metrics computed"))
    else:
        _write("evaluation.json", _unavailable("evaluation", "no evaluation stage output"))

    best_pipeline = getattr(state, "best_pipeline", None) or {}
    trained_model = getattr(state, "trained_model", None)
    model_info = {
        "model_type": best_pipeline.get("model_type"),
        "model_class": type(trained_model).__name__ if trained_model is not None else None,
        "best_params": best_pipeline.get("best_params") or best_pipeline.get("params", {}),
        "score": best_pipeline.get("score"),
        "trials_used": best_pipeline.get("trials_used"),
        "time_elapsed": best_pipeline.get("time_elapsed"),
        "truncated": best_pipeline.get("truncated"),
        "estimated_training_cost": best_pipeline.get("estimated_training_cost"),
    }
    if best_pipeline:
        _write("model.json", model_info)
        _write("training.json", best_pipeline)
    else:
        _write("model.json", _unavailable("model", "no trained model"))
        _write("training.json", _unavailable("training", "no training stage output"))

    feature_names = getattr(state, "feature_names", None)
    feature_transform = getattr(state, "feature_transform", None)
    if feature_names is not None:
        _write(
            "feature_metadata.json",
            {
                "feature_names": feature_names,
                "n_features": len(feature_names),
                "feature_transform": feature_transform,
            },
        )
    else:
        _write(
            "feature_metadata.json",
            _unavailable("feature_metadata", "no feature engineering output"),
        )

    target_column = getattr(state, "target_column", None)
    task_type = getattr(state, "task_type", None)
    if target_column is not None or task_type is not None:
        _write(
            "target_detection.json",
            {
                "target_column": target_column,
                "task_type": task_type,
                "confidence": getattr(state, "target_detection_confidence", None),
                "ambiguity_reason": getattr(state, "ambiguity_reason", None),
            },
        )
    else:
        _write(
            "target_detection.json",
            _unavailable("target_detection", "no target detection output"),
        )

    resource_report = getattr(state, "resource_report", None)
    if resource_report is not None:
        _write("resource_estimation.json", resource_report)
    else:
        _write(
            "resource_estimation.json",
            _unavailable("resource_estimation", "pre-flight resource estimation did not run"),
        )

    engine_name = getattr(state, "engine_name", None)
    if engine_name is not None:
        _write(
            "engine_selection.json",
            {
                "engine": engine_name,
                "recommendation": {"engine": engine_name},
                "routing": {
                    "row_count": getattr(state, "row_count", None),
                    "engine_selected": engine_name,
                },
            },
        )
    else:
        _write(
            "engine_selection.json",
            _unavailable("engine_selection", "no engine selected (empty/partial state)"),
        )

    data_profile = getattr(state, "data_profile", None)
    if data_profile is not None:
        _write("eda.json", data_profile)
    else:
        _write("eda.json", _unavailable("eda", "no EDA stage output"))

    validation_report = getattr(state, "validation_report", None)
    if validation_report is not None:
        _write("validation.json", validation_report)
    else:
        _write("validation.json", _unavailable("validation", "no validation stage output"))

    explanation_report = getattr(state, "explanation_report", None)
    if explanation_report is not None:
        _write("shap.json", explanation_report)
    else:
        _write(
            "shap.json",
            _unavailable("shap", "no SHAP explanation produced for this task/model"),
        )

    config_snapshot = getattr(state, "config_snapshot", None)
    if config_snapshot is not None:
        _write("config.json", config_snapshot)
    else:
        _write("config.json", _unavailable("config", "no configuration snapshot recorded"))

    final_report = getattr(state, "final_report", None)
    if final_report is not None:
        _write("report.md", final_report, fmt="md")
        try:
            from phronesisml.ml.reports.builder import build_html_report

            _write("report.html", build_html_report(state), fmt="html")
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"report.html not written: {exc}")
    else:
        _write("report.md", _unavailable("report", "no reporting stage output"), fmt="txt")
        _write("report.html", _unavailable("report.html", "no reporting stage output"), fmt="txt")

    # ── Pipeline report (reuses the canonical JSON report builder) ───
    try:
        from phronesisml.ml.reports.io import build_json_report

        _write("pipeline.json", build_json_report(state))
    except Exception as exc:  # pragma: no cover - defensive
        warnings.append(f"pipeline.json not written: {exc}")

    # ── Binary model artifact ────────────────────────────────────────
    if trained_model is not None:
        try:
            import joblib

            model_path = artifact_dir / "model.joblib"
            joblib.dump(trained_model, model_path)
            saved_files.append(str(model_path))
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"model.joblib not written: {exc}")

    # ── Deterministic text log ───────────────────────────────────────
    transform_log = getattr(state, "transform_log", None) or []
    log_lines = [
        f"PhronesisML run log — run_id={run_id}",
        f"version={_package_version()} status={getattr(state, 'status', None)}",
        f"data_path={getattr(state, 'data_path', None)}",
        f"target_column={target_column} task_type={task_type}",
        f"engine={engine_name}",
        f"rows={getattr(state, 'row_count', None)}",
        f"feature_names={feature_names}",
        f"transformations={len(transform_log)}",
        *[f"[transform] {json.dumps(t, default=str)}" for t in transform_log or []],
        *[f"[warning] {w}" for w in warnings],
    ]
    _write("logs.txt", "\n".join(log_lines) + "\n", fmt="txt")

    # ── Run metadata (canonical index) ───────────────────────────────
    metadata = {
        "run_id": run_id,
        "status": getattr(state, "status", None),
        "version": _package_version(),
        "data_path": getattr(state, "data_path", None),
        "target_column": target_column,
        "task_type": task_type,
        "engine": engine_name,
        "best_pipeline": best_pipeline,
        "artifact_count": len(saved_files),
        "saved_files": saved_files,
    }
    _write("run_metadata.json", metadata)

    artifact_uri = str(artifact_dir)
    logger.info(
        "Storage service: saved %d artifacts to %s.",
        len(saved_files),
        artifact_uri,
    )

    return {"artifact_uri": artifact_uri, "saved_files": saved_files, "warnings": warnings}


def _package_version() -> str:
    """Return the installed ``phronesisml`` version (best-effort)."""
    try:
        from phronesisml import __version__ as _version

        return _version
    except ImportError:  # pragma: no cover - defensive
        return "unknown"
