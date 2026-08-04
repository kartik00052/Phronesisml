"""Report I/O and extraction helpers.

Engine-light complements to :mod:`builder`.  These functions persist
generated reports, convert pipeline state into structured (JSON-able)
summaries, and render metrics dicts as Markdown tables.

Public API:
    - ``write_report``: persist a report to a Markdown/HTML/text file.
    - ``build_json_report``: JSON-serializable report from pipeline state.
    - ``build_run_report``: run-scoped dataset analysis report (Markdown).
    - ``report_to_dict``: structured summary of pipeline state.
    - ``render_metrics_table``: Markdown table from a metrics dict.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _state_get(state: Any, name: str) -> Any:
    """Safe attribute read that tolerates missing fields."""
    if isinstance(state, dict):
        return state.get(name)
    return getattr(state, name, None)


def _row_count(state: Any, profile: Any) -> Any:
    return (
        _state_get(state, "row_count")
        or _state_get(state, "n_rows")
        or _state_get(profile, "n_rows")
    )


def _column_count(state: Any, profile: Any) -> Any:
    columns = _state_get(state, "column_count") or _state_get(state, "n_columns")
    if columns is not None:
        return columns
    if isinstance(profile, dict):
        if profile.get("n_columns") is not None:
            return profile["n_columns"]
        numeric = profile.get("numeric_columns") or []
        categorical = profile.get("categorical_columns") or []
        return len(numeric) + len(categorical)
    feature_names = _state_get(state, "feature_names")
    return len(feature_names) if feature_names else None


def _warnings(state: Any) -> list[str]:
    return _state_get(state, "warnings") or _state_get(state, "preflight_warnings") or []


def _errors(state: Any) -> list[str]:
    return _state_get(state, "errors") or _state_get(state, "preflight_blockers") or []


def _jsonable(value: Any) -> Any:
    """Best-effort coercion of common non-JSON values."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return str(value)


def build_json_report(
    state: Any,
    narrative: str | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable report from pipeline state.

    Args:
        state: ``WorkflowState`` (or compatible dataclass / dict).
        narrative: Optional free-text narrative to attach.

    Returns:
        A dict with run metadata, dataset info, pipeline results
        (validation/eda/target/features/models/metrics/explanation),
        warnings, and narrative.
    """
    metrics = _state_get(state, "evaluation_report") or _state_get(state, "metrics")
    best_pipeline = _state_get(state, "best_pipeline")
    data_profile = _state_get(state, "data_profile")
    explanation = _state_get(state, "explanation_report")
    version: str | None = None
    try:
        from phronesisml import __version__ as _pkg_version

        version = _pkg_version
    except ImportError:  # pragma: no cover - defensive
        version = None

    return {
        "run": {
            "run_id": _state_get(state, "run_id"),
            "status": _state_get(state, "status"),
            "timestamp": _state_get(state, "timestamp"),
            "version": _state_get(state, "version") or version,
        },
        "dataset": {
            "path": _state_get(state, "data_path"),
            "rows": _row_count(state, data_profile),
            "columns": _column_count(state, data_profile),
            "feature_names": _state_get(state, "feature_names"),
            "data_profile": _jsonable(data_profile),
        },
        "target": {
            "target_column": _state_get(state, "target_column"),
            "task_type": _state_get(state, "task_type"),
            "target_confidence": _state_get(state, "target_detection_confidence"),
            "ambiguity_reason": _state_get(state, "ambiguity_reason"),
        },
        "model": _jsonable(best_pipeline),
        "metrics": _jsonable(metrics),
        "explanation": {
            "explainer": _jsonable(
                _state_get(explanation, "explainer") or _state_get(explanation, "explainer_type")
            )
            if explanation
            else None,
            "feature_importance": _jsonable(_state_get(explanation, "feature_importance"))
            if explanation
            else None,
        },
        "warnings": _warnings(state),
        "errors": _errors(state),
        "narrative": narrative,
    }


def build_run_report(
    state: Any,
    run_dir: str | Path,
    runtime_seconds: float | None = None,
    artifacts: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a run-scoped dataset analysis report at ``<run_dir>/<run_id>.md``.

    The report documents dataset information, target/task, engine, sampling,
    feature engineering transformations, candidate models, best model with
    hyperparameters, metrics, SHAP explainer + feature importance,
    warnings/errors, runtime, artifacts, and recommendations.

    Args:
        state: ``WorkflowState`` (or compatible dataclass / dict).
        run_dir: Directory to write the Markdown report into.
        runtime_seconds: Optional total runtime.
        artifacts: Optional list of artifact paths produced by the run.

    Returns:
        A dict with ``run_id``, ``path``, and ``bytes``.

    Raises:
        OSError: If disk write fails.
    """
    run_id = _state_get(state, "run_id") or "default_run"
    dest_dir = Path(run_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{run_id}.md"

    task_type = _state_get(state, "task_type") or "unknown"
    target = _state_get(state, "target_column") or "not detected"
    metrics = _state_get(state, "evaluation_report") or _state_get(state, "metrics") or {}
    best = _state_get(state, "best_pipeline") or {}
    data_profile = _state_get(state, "data_profile")
    explanation = _state_get(state, "explanation_report") or {}
    candidates = _state_get(state, "candidate_models") or []
    resource_report = _state_get(state, "resource_report")
    explainer = (
        _state_get(explanation, "explainer_type") or _state_get(explanation, "explainer") or "n/a"
    )

    nested_metrics = (
        metrics.get("metrics")
        if isinstance(metrics, dict) and isinstance(metrics.get("metrics"), dict)
        else None
    )
    metrics_table = render_metrics_table(nested_metrics) if nested_metrics else ""

    warnings = _warnings(state)
    errors = _errors(state)

    lines = [
        f"# Run Report — {run_id}",
        "",
        "## Dataset Information",
        f"- Rows: {_row_count(state, data_profile) or 'n/a'}",
        f"- Columns: {_column_count(state, data_profile) or 'n/a'}",
        f"- Feature columns: {_fmt_list(_state_get(state, 'feature_names'))}",
        f"- Data path: {_state_get(state, 'data_path') or 'n/a'}",
        "",
        "## Target & Task",
        f"- Target: `{target}`",
        f"- Task: `{task_type}`",
        f"- Confidence: {_state_get(state, 'target_detection_confidence') or 'n/a'}",
        f"- Ambiguity: {_state_get(state, 'ambiguity_reason') or 'none'}",
        "",
        "## Engine & Sampling",
        f"- Engine: "
        f"{_state_get(resource_report, 'engine') or _state_get(state, 'engine') or 'n/a'}",
        f"- Sampling: {_jsonable(_state_get(state, 'sampling_metadata')) or 'none'}",
        "",
        "## Feature Engineering",
        f"- Transformations: {_fmt_list(_state_get(state, 'transform_log'))}",
        "",
        "## Model Selection",
        f"- Candidates tried: "
        f"{_fmt_list([c.get('name') or c.get('model_type') for c in candidates])}",
        f"- Best model: `{best.get('model_type') or 'n/a'}`",
        f"- Best score: {best.get('score') or 'n/a'}",
        f"- Trials used: {best.get('trials_used') or 'n/a'}",
        f"- HPO truncated: {best.get('truncated') or False}",
        f"- Hyperparameters: {best.get('best_params') or best.get('params') or 'n/a'}",
        "",
        "## Evaluation Metrics",
        metrics_table,
        "",
        "## SHAP Explainability",
        f"- Explainer: {explainer or 'n/a'}",
        f"- Feature importance: "
        f"{_jsonable(_state_get(explanation, 'feature_importance')) or 'n/a'}",
        "",
        "## Warnings & Errors",
        f"- Warnings: {_fmt_list(warnings)}",
        f"- Errors: {_fmt_list(errors)}",
        "",
        "## Runtime & Artifacts",
        f"- Runtime (seconds): {_fmt_float(runtime_seconds)}",
        f"- Artifacts: {_fmt_list(artifacts)}",
        "",
        "## Recommendations",
        _render_recommendations(task_type, metrics),
    ]

    text = "\n".join(lines)
    path.write_text(text, encoding="utf-8")
    return {"run_id": run_id, "path": str(path), "bytes": path.stat().st_size}


def _fmt_list(value: Any) -> str:
    if not value:
        return "n/a"
    if isinstance(value, list | tuple):
        return ", ".join(str(v) for v in value)
    return str(value)


def _fmt_float(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"


def _render_recommendations(task_type: str, metrics: dict[str, Any]) -> str:
    recs: list[str] = []
    if task_type == "classification":
        recs.append(
            "Inspect the confusion matrix; tune the decision threshold via the "
            "precision-recall curve when class balance is skewed."
        )
    elif task_type == "regression":
        recs.append(
            "Inspect residual distribution; consider feature scaling and "
            "log-transforming skewed targets."
        )
    recs.append("Re-run with a fixed seed to confirm reproducibility.")
    return "\n".join(f"- {r}" for r in recs)


def write_report(
    report: str,
    path: str | Path,
    fmt: str | None = None,
) -> dict[str, Any]:
    """Persist a report string to disk.

    Args:
        report: Report text (e.g. from ``build_report``).
        path: Destination file path.  When *fmt* is ``"html"`` the
            report is wrapped in a minimal HTML document if it does not
            already look like HTML.
        fmt: Optional format hint: ``"md"``, ``"html"``, or ``"txt"``.
            When ``None``, inferred from *path* suffix.

    Returns:
        A dict with ``path``, ``fmt``, and ``bytes``.

    Raises:
        OSError: If disk write fails.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if fmt is None:
        fmt = {"md": "md", ".md": "md", ".markdown": "md", "html": "html", ".html": "html"}.get(
            p.suffix.lower(), "txt"
        )

    text = report
    if fmt == "html" and not text.lstrip().lower().startswith("<"):
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = (
            "<!DOCTYPE html>\n<html><head><meta charset='utf-8'>"
            "<title>PhronesisML Report</title></head>"
            f"<body><pre>{escaped}</pre></body></html>\n"
        )

    p.write_text(text, encoding="utf-8")
    return {"path": str(p), "fmt": fmt, "bytes": p.stat().st_size}


def report_to_dict(state: Any) -> dict[str, Any]:
    """Extract a JSON-serializable summary from pipeline state.

    Reads safe attributes (target, task type, best model, metrics, run
    metadata) and tolerates missing fields.

    Args:
        state: WorkflowState (or compatible dataclass / object).

    Returns:
        A dict with ``run_id``, ``target_column``, ``task_type``,
        ``model``, ``n_features``, ``metrics``, and ``timestamp`` fields
        when available.
    """
    metrics = getattr(state, "evaluation_report", None)
    if metrics is None:
        metrics = getattr(state, "metrics", None)

    feature_names = getattr(state, "feature_names", None)

    return {
        "run_id": getattr(state, "run_id", None),
        "timestamp": getattr(state, "timestamp", None),
        "target_column": getattr(state, "target_column", None),
        "task_type": getattr(state, "task_type", None),
        "model": getattr(state, "best_pipeline", None),
        "n_features": len(feature_names) if feature_names else None,
        "metrics": metrics,
    }


def render_metrics_table(
    metrics: dict[str, Any],
    include_keys: list[str] | None = None,
) -> str:
    """Render a metrics dict as a Markdown table.

    Args:
        metrics: Flat dict of ``metric -> value``.
        include_keys: Optional subset of keys to include.  When ``None``
            all scalar values are included.

    Returns:
        A Markdown table string (header row + one row per metric).
    """
    rows: list[tuple[str, str]] = []
    for key, value in metrics.items():
        if include_keys is not None and key not in include_keys:
            continue
        if isinstance(value, dict | list):
            continue
        rows.append((str(key), _format_value(value)))

    if not rows:
        return "| Metric | Value |\n| --- | --- |\n| _no data_ | _no data_ |\n"

    lines = ["| Metric | Value |", "| --- | --- |"]
    for key, value in rows:
        safe_key = key.replace("|", "\\|")
        safe_value = value.replace("|", "\\|")
        lines.append(f"| {safe_key} | {safe_value} |")
    return "\n".join(lines) + "\n"


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if value is None:
        return "_None_"
    return str(value)
