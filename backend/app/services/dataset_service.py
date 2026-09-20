"""Dataset service — upload, inspect, and DTO assembly for datasets.

Inspection reuses the SDK's real loaders, profiler, and validators so
the browse/upload UI shows authentic values for every field.
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from pathlib import Path
from typing import Any

from backend.app.config import Settings, get_settings
from backend.app.db import repositories
from backend.app.db.models import Dataset
from backend.app.db.repositories import iso
from phronesisml.configs.settings import PANDAS_MAX_BYTES

ALLOWED_EXTENSIONS = frozenset({".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl"})

_PREVIEW_ROWS = 10
_MAX_PREVIEW_CELLS = 500

# Bundled sample datasets shipped in the repository. They are registered as
# real (sample-flagged) datasets so Iris & friends are browsable/inspectable,
# but never auto-selected and never auto-run.
BUNDLED_SAMPLES: tuple[tuple[str, str], ...] = (
    ("iris.csv", "data/iris.csv"),
    ("credit_card_clients.csv", "data/credit_card_clients.csv"),
)


class UploadRejectedError(Exception):
    """Raised when an upload is rejected before storing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def upload_dataset(
    *,
    dataset_id: str | None,
    filename: str,
    size_bytes: int,
    content: Any,
    settings: Settings | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Persist and inspect an uploaded dataset, returning the full DTO."""
    settings = settings or get_settings()
    if size_bytes > settings.max_upload_bytes:
        limit_mb = settings.max_upload_size_mb
        raise UploadRejectedError(
            "FileTooLarge",
            f"File is {size_bytes / 1024 / 1024:.1f} MB; limit is {limit_mb} MB.",
        )

    name, ext = _safe_name(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadRejectedError(
            "UnsupportedFormat",
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )

    dataset_id = dataset_id or f"ds_{uuid.uuid4().hex[:16]}"
    dataset_dir = settings.data_storage_dir / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    dest = dataset_dir / f"{name}{ext}"
    _write_content(dest, content)

    try:
        profile, validation, preview, sheets = _inspect(dest, settings)
    except Exception as exc:  # noqa: BLE001
        _cleanup_upload(dataset_id, dataset_dir)
        raise UploadRejectedError("InspectionFailed", f"Could not inspect dataset: {exc}") from exc

    missing_cells = int(sum((validation.get("null_counts") or {}).values()))
    duplicate_rows = int(validation.get("duplicate_rows") or 0)

    try:
        repositories.create_dataset(
            {
                "id": dataset_id,
                "user_id": user_id,
                "name": f"{name}{ext}",
                "path": str(dest),
                "format": ext.lstrip("."),
                "size_bytes": size_bytes,
                "rows": profile.get("shape", {}).get("rows"),
                "columns": profile.get("shape", {}).get("columns"),
                "engine": _inspect_engine_name(dest),
                "engine_reason": _inspect_engine_reason(dest),
                "validation_passed": bool(validation.get("passed")),
                "missing_cells": missing_cells,
                "duplicate_rows": duplicate_rows,
                "profile_path": str(dataset_dir / "profile.json"),
                "validation_path": str(dataset_dir / "validation.json"),
                "preview_path": str(dataset_dir / "preview.json"),
                "sheets": sheets,
                "sample": False,
            }
        )
        (dataset_dir / "profile.json").write_text(json.dumps(profile, default=_json_default))
        (dataset_dir / "validation.json").write_text(json.dumps(validation, default=_json_default))
        (dataset_dir / "preview.json").write_text(json.dumps(preview, default=_json_default))

        dataset = repositories.get_dataset(dataset_id)
    except Exception as exc:  # noqa: BLE001 - any post-write failure must not leave orphans
        _cleanup_upload(dataset_id, dataset_dir)
        raise UploadRejectedError(
            "UploadFailed", f"Could not finalize dataset upload: {exc}"
        ) from exc
    if dataset is None:  # pragma: no cover - race guard
        _cleanup_upload(dataset_id, dataset_dir)
        raise UploadRejectedError("UpsertFailed", "Dataset row could not be created.")
    return dataset_to_dict(dataset)


def seed_sample_datasets(settings: Settings | None = None) -> list[dict[str, Any]]:
    """Register the bundled sample datasets as sample-flagged rows.

    Idempotent: a sample is copied from the repository ``data/`` directory
    into storage (run-scoped, user-deletable) and registered only if its
    deterministic id is not already present. Samples are never auto-selected
    and never trigger a run — they exist purely so the UI can offer
    ``Sample datasets`` for inspection and explicit run creation.
    """
    settings = settings or get_settings()
    # In multitenant (supabase) mode bundled samples are shared system rows
    # (user_id NULL, visible to every authenticated user). In dev mode they
    # belong to this environment's local-dev identity.
    sample_user: str | None = None if settings.auth_enabled else "local-dev"
    registered: list[dict[str, Any]] = []
    for file_name, rel in BUNDLED_SAMPLES:
        source = settings.root_dir / rel
        if not source.is_file():
            continue
        dataset_id = f"ds_sample_{hashlib.sha1(file_name.encode()).hexdigest()[:16]}"
        if repositories.get_dataset(dataset_id) is not None:
            continue
        dataset_dir = settings.data_storage_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        dest = dataset_dir / file_name
        with source.open("rb") as src, dest.open("wb") as out:
            while chunk := src.read(1024 * 1024):
                out.write(chunk)
        try:
            profile, validation, preview, sheets = _inspect(dest, settings)
        except Exception:  # noqa: BLE001 - a broken fixture must not block startup
            if dataset_dir.is_dir():
                import shutil

                shutil.rmtree(dataset_dir, ignore_errors=True)
            continue
        missing_cells = int(sum((validation.get("null_counts") or {}).values()))
        duplicate_rows = int(validation.get("duplicate_rows") or 0)
        repositories.create_dataset(
            {
                "id": dataset_id,
                "user_id": sample_user,
                "name": file_name,
                "path": str(dest),
                "format": file_name.rsplit(".", 1)[-1].lower(),
                "size_bytes": dest.stat().st_size,
                "rows": profile.get("shape", {}).get("rows"),
                "columns": profile.get("shape", {}).get("columns"),
                "engine": _inspect_engine_name(dest),
                "engine_reason": "Bundled sample dataset — inspect, then start a run explicitly.",
                "validation_passed": bool(validation.get("passed")),
                "missing_cells": missing_cells,
                "duplicate_rows": duplicate_rows,
                "profile_path": str(dataset_dir / "profile.json"),
                "validation_path": str(dataset_dir / "validation.json"),
                "preview_path": str(dataset_dir / "preview.json"),
                "sheets": sheets,
                "sample": True,
            }
        )
        (dataset_dir / "profile.json").write_text(json.dumps(profile, default=_json_default))
        (dataset_dir / "validation.json").write_text(json.dumps(validation, default=_json_default))
        (dataset_dir / "preview.json").write_text(json.dumps(preview, default=_json_default))
        row = repositories.get_dataset(dataset_id)
        if row is not None:
            registered.append(dataset_to_dict(row))
    return registered


def dataset_to_dict(dataset: Dataset, run_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assemble the full ``Dataset`` DTO (frontend contract) for a dataset row."""
    profile = _read_json(dataset.profile_path) or {}
    validation = _read_json(dataset.validation_path) or {}
    preview = _read_json(dataset.preview_path) or {"columns": [], "rows": [], "maxRows": 0}
    sheets = dataset.sheets or []

    columns = _columns_from_profile(profile)
    summary = {
        "id": dataset.id,
        "name": dataset.name,
        "path": dataset.path,
        "format": dataset.format,
        "sizeBytes": dataset.size_bytes,
        "rows": dataset.rows,
        "columns": dataset.columns,
        "engine": dataset.engine,
        "engineReason": dataset.engine_reason,
        "validationPassed": dataset.validation_passed,
        "missingCells": dataset.missing_cells,
        "duplicateRows": dataset.duplicate_rows,
        "targetColumn": dataset.target_column,
        "taskType": dataset.task_type,
        "registeredAt": iso(dataset.registered_at),
        "lastUsedRunId": dataset.last_used_run_id,
        "sample": bool(dataset.sample),
    }
    if run_context:
        summary = {**summary, **run_context["summary_overrides"]}
    return {
        "summary": summary,
        "profile": profile,
        "columns": columns,
        "validation": validation,
        "transformLog": [],
        "preview": preview,
        "sheets": sheets,
    }


def dataset_summary(dataset: Dataset) -> dict[str, Any]:
    return dataset_to_dict(dataset)["summary"]


def for_run(run: Any) -> dict[str, Any]:
    """Build the run-linked dataset DTO from run artifacts plus upload metadata.

    The profile/validation/preview come from the run's own artifacts when
    present (the run may have re-validated the file), otherwise from the
    original upload inspection. ``transform_log`` comes from the run row.
    """
    profile: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    preview: dict[str, Any] = {"columns": [], "rows": [], "maxRows": 0}
    inferred_target = None
    inferred_task = None

    for name in ("eda.json", "pre_validation.json"):
        raw = _run_artifact_json(run.id, name)
        if raw:
            profile = raw
            break

    for name in ("validation.json", "pre_validation.json"):
        raw = _run_artifact_json(run.id, name)
        if not raw:
            continue
        if name == "validation.json" or raw.get("passed") is not None:
            validation = raw
            break

    source = None
    if run.dataset_id:
        source = repositories.get_dataset(run.dataset_id)
    if source:
        preview = _read_json(source.preview_path) or preview
        if not profile:
            profile = _read_json(source.profile_path) or {}
        if not validation:
            validation = _read_json(source.validation_path) or {}

    for name in ("target_detection.json", "feature_metadata.json"):
        raw = _run_artifact_json(run.id, name) or {}
        inferred_target = raw.get("target_column") or inferred_target
        inferred_task = raw.get("task_type") or raw.get("model_type") or inferred_task

    summary = {
        "id": run.dataset_id or run.id,
        "name": run.dataset_name or "run dataset",
        "path": run.dataset_path or "",
        "format": (run.dataset_path or "").rsplit(".", 1)[-1] if run.dataset_path else "",
        "sizeBytes": run.file_size_bytes or 0,
        "rows": run.rows,
        "columns": run.columns,
        "engine": run.engine,
        "engineReason": run.engine or "selected at run time",
        "validationPassed": (
            validation.get("passed") if validation.get("passed") is not None else None
        ),
        "missingCells": (
            int(sum((validation.get("null_counts") or {}).values()))
            if validation.get("null_counts")
            else 0
        ),
        "duplicateRows": int(validation.get("duplicate_rows") or 0),
        "targetColumn": inferred_target or run.target_column,
        "taskType": inferred_task or run.task_type,
        "registeredAt": iso(source.registered_at) if source else iso(run.created_at),
        "lastUsedRunId": run.id,
        "sample": bool(getattr(source, "sample", False)) if source else False,
    }
    return {
        "summary": summary,
        "profile": profile,
        "columns": _columns_from_profile(profile),
        "validation": validation,
        "transformLog": list(run.transform_log or []),
        "preview": preview,
        "sheets": (source.sheets if source else []) or [],
    }


def _run_artifact_json(run_id: str, name: str) -> dict[str, Any] | None:
    from backend.app.services.artifact_service import artifact_path

    path = artifact_path(run_id, name)
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


# ─────────────────── overview + derived views ─────────────────


def dataset_preview(dataset_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any] | None:
    """Paginated row preview from the stored CSV/sheet file."""
    dataset = repositories.get_dataset(dataset_id)
    if dataset is None:
        return None
    path = Path(dataset.path)
    if not path.is_file():
        return None
    pandas = _is_pandas_engine(path)
    engine = _build_engine(path, pandas)
    try:
        from phronesisml.data.loaders.file_loader import load_file

        df = engine.collect(load_file(str(path), engine))
        rows_total = int(df.shape[0])
        start = (page - 1) * page_size
        window = df.head(start + page_size).tail(page_size)
        columns = [str(c) for c in window.columns]
        rows = [_jsonable_row(row) for row in window.itertuples(index=False, name=None)]
        return {
            "columns": columns,
            "rows": rows,
            "page": page,
            "pageSize": page_size,
            "totalRows": rows_total,
            "hasMore": start + page_size < rows_total,
        }
    except Exception as exc:  # noqa: BLE001
        raise UploadRejectedError("PreviewFailed", f"Could not build preview: {exc}") from exc


def dataset_schema(dataset_id: str) -> dict[str, Any] | None:
    dataset = repositories.get_dataset(dataset_id)
    if dataset is None:
        return None
    profile = _read_json(dataset.profile_path) or {}
    return {
        "name": dataset.name,
        "columns": _columns_from_profile(profile),
        "shape": profile.get("shape")
        or {
            "rows": dataset.rows or 0,
            "columns": dataset.columns or 0,
        },
    }


def dataset_eda(dataset_id: str) -> dict[str, Any] | None:
    dataset = repositories.get_dataset(dataset_id)
    if dataset is None:
        return None
    profile = _read_json(dataset.profile_path) or {}
    if not profile:
        return None
    return dataset_to_dict(dataset)["profile"]


def delete_dataset(dataset_id: str, user_id: str | None = None) -> dict[str, Any]:
    from sqlalchemy import select

    from backend.app.db.models import Dataset as _Dataset
    from backend.app.db.repositories import _ownership_clause, session_scope

    with session_scope() as session:
        stmt = select(_Dataset).where(_Dataset.id == dataset_id)
        owner = _ownership_clause(_Dataset.user_id, user_id)
        if owner is not None:
            stmt = stmt.where(owner)
        dataset = session.scalar(stmt)
    if dataset is None:
        # Missing, or not owned by the caller → intentionally hidden.
        return {"deleted": False, "id": None}
    import shutil

    storage_root = get_settings().data_storage_dir.resolve()
    dataset_dir = (
        Path(dataset.path).parent if dataset.path else get_settings().data_storage_dir / dataset_id
    )
    resolved = dataset_dir.resolve()
    if not resolved.is_relative_to(storage_root):
        # Safety: refuse to remove anything outside the configured storage root.
        return {"deleted": False, "id": dataset_id}
    with session_scope() as session:
        session.query(_Dataset).filter(_Dataset.id == dataset_id).delete()  # type: ignore[attr-defined]
        session.commit()
    if dataset_dir.is_dir():
        shutil.rmtree(dataset_dir, ignore_errors=True)
    return {"deleted": True, "id": dataset_id}


# ─────────────────── helpers ───────────────────────────────────


def _inspect(
    path: Path, settings: Settings
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    pandas = _is_pandas_engine(path)
    engine = _build_engine(path, pandas)

    from phronesisml.data.loaders.file_loader import _EXCEL_EXTENSIONS, load_file
    from phronesisml.data.profilers.stats import profile_dataset
    from phronesisml.data.validators.checks import validate_dataframe

    df = load_file(str(path), engine)
    profile = profile_dataset(df, engine)
    _, validation = validate_dataframe(df, engine)
    preview = _build_preview(df, engine)
    sheets: list[dict[str, Any]] = []
    if path.suffix.lower() in _EXCEL_EXTENSIONS:
        try:
            from phronesisml.data.loaders.file_loader import list_excel_sheets

            sheets = [
                {
                    "name": s["name"],
                    "index": i,
                    "rows": s.get("rows") or 0,
                    "cols": s.get("columns") or 0,
                }
                for i, s in enumerate(list_excel_sheets(path))
            ]
        except Exception:  # noqa: BLE001
            sheets = []
    return profile, validation, preview, sheets


def _build_engine(path: Path, pandas: bool) -> Any:
    if pandas:
        from phronesisml.engines.pandas_engine import PandasEngine

        return PandasEngine()
    from phronesisml.engines.polars_engine import PolarsEngine

    return PolarsEngine()


def _is_pandas_engine(path: Path) -> bool:
    if path.suffix.lower() in {".xlsx", ".xls", ".json", ".jsonl"}:
        return True
    return path.stat().st_size < PANDAS_MAX_BYTES


def _inspect_engine_name(path: Path) -> str:
    return "pandas" if _is_pandas_engine(path) else "polars"


def _inspect_engine_reason(path: Path) -> str:
    if _is_pandas_engine(path):
        return "inspection engine: pandas (small file or Excel/JSON)"
    return "inspection engine: polars (larger tabular file)"


def _build_preview(df: Any, engine: Any) -> dict[str, Any]:
    collected = engine.collect(df)
    head = collected.head(_PREVIEW_ROWS)
    columns = [str(c) for c in head.columns]
    rows = [_jsonable_row(row) for row in head.itertuples(index=False, name=None)]
    return {"columns": columns, "rows": rows, "maxRows": _PREVIEW_ROWS}


def _jsonable_row(row: tuple[Any, ...]) -> list[Any]:
    out: list[Any] = []
    for value in row:
        if value is None or isinstance(value, (str, int, float, bool)):
            if isinstance(value, float) and math.isnan(value):
                out.append(None)
            else:
                out.append(value)
        else:
            rendered = _json_default(value)
            out.append(
                rendered
                if isinstance(rendered, (str, int, float, bool)) or rendered is None
                else str(rendered)
            )
    return out


def _columns_from_profile(profile: dict[str, Any]) -> list[dict[str, Any]]:
    numeric = set(profile.get("numeric_columns") or [])
    categorical = set(profile.get("categorical_columns") or [])
    numeric_summary = profile.get("numeric_summary") or {}
    categorical_summary = profile.get("categorical_summary") or {}
    columns: list[dict[str, Any]] = []
    for name in profile.get("column_names") or []:
        is_num = name in numeric
        is_cat = name in categorical
        null_count = 0
        if is_num:
            null_count = int(numeric_summary.get(name, {}).get("null_count") or 0)
        elif is_cat:
            null_count = int(categorical_summary.get(name, {}).get("null_count") or 0)
        rows = profile.get("shape", {}).get("rows") or 0
        columns.append(
            {
                "name": name,
                "dtype": (profile.get("dtypes") or {}).get(name, "unknown"),
                "numeric": is_num,
                "categorical": is_cat,
                "nullCount": null_count,
                "nullPercent": round(null_count / rows, 4) if rows else 0,
                "cardinality": categorical_summary.get(name, {}).get("cardinality"),
                "stats": numeric_summary.get(name),
                "topValues": categorical_summary.get(name, {}).get("top_values"),
            }
        )
    return columns


def _safe_name(filename: str) -> tuple[str, str]:
    stem = Path(filename).stem or "dataset"
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem).strip()
    safe = safe[:80] or "dataset"
    ext = Path(filename).suffix.lower()
    return safe, ext


def _write_content(dest: Path, content: Any) -> None:
    if hasattr(content, "read"):
        with dest.open("wb") as handle:
            while chunk := content.read(1024 * 1024):
                handle.write(chunk)
    else:
        dest.write_bytes(_as_bytes(content))


def _as_bytes(content: Any) -> bytes:
    if isinstance(content, bytes):
        return content
    return bytes(content)


def _cleanup_upload(dataset_id: str, dataset_dir: Path) -> None:
    """Best-effort removal of a partial upload (dir + any registered row).

    Runs on every failure path after the file hits disk so a rejected upload
    can never leave an orphan directory or a half-indexed dataset row.
    """
    try:
        from backend.app.db.models import Dataset as DatasetModel
        from backend.app.db.repositories import session_scope

        with session_scope() as session:
            session.query(DatasetModel).filter(DatasetModel.id == dataset_id).delete()
            session.commit()
    except Exception:  # noqa: BLE001 - cleanup is best-effort
        pass
    if dataset_dir.is_dir():
        import shutil

        shutil.rmtree(dataset_dir, ignore_errors=True)


def _read_json(path_s: str | None) -> dict[str, Any] | None:
    if not path_s:
        return None
    path = Path(path_s)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _json_default(value: Any) -> Any:
    import datetime

    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return value
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    try:
        return str(value)
    except Exception:  # noqa: BLE001
        return repr(value)


def engine_recommend(inputs: dict[str, Any]) -> dict[str, Any]:
    """Advisory engine recommendation delegated to the SDK's selector.

    The backend never re-implements engine heuristics; it forwards the
    dataset characteristics to ``phronesisml.engines.recommend.recommend_engine``
    (single source of truth shared with the run worker).
    """
    from phronesisml.engines.recommend import recommend_engine

    return recommend_engine(
        n_rows=int(inputs.get("rows") or 0),
        n_cols=int(inputs.get("cols") or 0),
        memory_bytes=int(inputs.get("bytes") or 0),
    )
