"""Route handlers for the Phronesis REST API.

Every handler is a thin adapter: validate input → call SDK → wrap
result.  No business logic, no preprocessing, no ML logic.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Coroutine
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from phronesisml import __version__
from phronesisml.interfaces.api.jobs import job_store
from phronesisml.interfaces.api.models import (
    ALLOWED_EXTENSIONS,
    DOCUMENTATION_BASE_URL,
    MAX_UPLOAD_SIZE_MB,
    APIResponse,
    CapabilitiesData,
    ErrorDetail,
    HealthData,
    JobData,
    VersionData,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────


def _ok(data: Any) -> APIResponse:
    """Wrap successful data in the standard envelope."""
    return APIResponse(success=True, data=data)


def _err(code: str, message: str, status: int, details: Any = None) -> HTTPException:
    """Build an HTTPException with a structured ErrorDetail body."""
    body = APIResponse(
        success=False,
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
            documentation=f"{DOCUMENTATION_BASE_URL}/{code}",
        ),
    )
    return HTTPException(status_code=status, detail=body.model_dump())


def _validate_file(file: UploadFile) -> None:
    """Validate uploaded file type.  Raises HTTPException on failure."""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise _err(
            "UNSUPPORTED_FORMAT",
            f"File format '{ext}' is not supported. "
            f"Allowed: {sorted(e.lstrip('.') for e in ALLOWED_EXTENSIONS)}",
            status=415,
        )


async def _save_upload(file: UploadFile) -> str:
    """Read, validate size, and save upload to a temp directory.

    Returns the path to the saved file.  The caller is responsible
    for cleanup.
    """
    _validate_file(file)

    content = await file.read()
    if len(content) == 0:
        raise _err("EMPTY_FILE", "Uploaded file is empty.", status=422)

    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise _err(
            "FILE_TOO_LARGE",
            f"File exceeds maximum size of {MAX_UPLOAD_SIZE_MB} MB.",
            status=413,
        )

    tmp_dir = tempfile.mkdtemp(prefix="phronesisml_")
    safe_name = os.path.basename(file.filename or "data")
    tmp_path = os.path.join(tmp_dir, safe_name)
    with open(tmp_path, "wb") as fh:
        fh.write(content)

    return tmp_path


def _cleanup_path(path: str) -> None:
    """Best-effort removal of a temp file and its parent directory."""
    try:
        parent = os.path.dirname(path)
        if os.path.exists(path):
            os.remove(path)
        if os.path.isdir(parent):
            shutil.rmtree(parent, ignore_errors=True)
    except OSError:
        logger.warning("Failed to clean up temp path: %s", path)


def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass instance to a plain dict."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return {"value": obj}


async def _submit_job(coro: Coroutine[Any, Any, Any]) -> APIResponse:
    """Create a job, schedule *coro* as a background task, return job info."""
    job = await job_store.create()
    await job_store.start_job(job.id, coro)
    return _ok(JobData(**job.to_dict()))


# ── System endpoints ─────────────────────────────────────────────


@router.get("/health", response_model=None, tags=["system"])
async def health() -> APIResponse:
    """Liveness and readiness check."""
    engines: list[str] = ["pandas"]
    try:
        import polars  # noqa: F401

        engines.append("polars")
    except ImportError:
        pass
    try:
        import pyspark  # noqa: F401

        engines.append("spark")
    except ImportError:
        pass

    return _ok(
        HealthData(
            status="ok",
            version=__version__,
            python=sys.version,
            platform=platform.system().lower(),
            engines=engines,
        ).model_dump(),
    )


@router.get("/version", response_model=None, tags=["system"])
async def version() -> APIResponse:
    """Return SDK version information."""
    return _ok(
        VersionData(
            version=__version__,
            python=sys.version,
        ).model_dump(),
    )


@router.get("/capabilities", response_model=None, tags=["system"])
async def capabilities() -> APIResponse:
    """Return supported formats, engines, stages, and limits."""
    from phronesisml.workflow.graph import PIPELINE_ORDER

    return _ok(
        CapabilitiesData(
            file_formats=[e.lstrip(".") for e in sorted(ALLOWED_EXTENSIONS)],
            engines=["pandas", "polars", "spark"],
            pipeline_stages=list(PIPELINE_ORDER),
            limits={
                "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
            },
        ).model_dump(),
    )


# ── Job management ───────────────────────────────────────────────


@router.get("/jobs/{job_id}", response_model=None, tags=["jobs"])
async def get_job(job_id: str) -> APIResponse:
    """Return the status and result of a job."""
    job = await job_store.get(job_id)
    if job is None:
        raise _err("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status=404)
    return _ok(JobData(**job.to_dict()))


@router.get("/jobs", response_model=None, tags=["jobs"])
async def list_jobs() -> APIResponse:
    """Return all jobs (newest first)."""
    jobs = await job_store.list_jobs()
    return _ok([JobData(**j.to_dict()).model_dump() for j in jobs])


# ── Pipeline endpoints ───────────────────────────────────────────


@router.post("/analyze", response_model=None, tags=["pipeline"])
async def analyze(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
) -> APIResponse:
    """Run the complete ML pipeline on a dataset.

    Uploads the file, runs all stages (upload → … → storage), and
    returns the full result asynchronously.
    """
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import analyze_async

        return await _submit_job(_run_and_cleanup(analyze_async, tmp_path, engine, null_strategy))
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/clean", response_model=None, tags=["pipeline"])
async def clean(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
) -> APIResponse:
    """Run ETL (upload + clean) on a dataset."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import clean_async

        return await _submit_job(_run_and_cleanup(clean_async, tmp_path, engine, null_strategy))
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/validate", response_model=None, tags=["pipeline"])
async def validate(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
) -> APIResponse:
    """Run upload + ETL + validation on a dataset."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import validate_async

        return await _submit_job(_run_and_cleanup(validate_async, tmp_path, engine, null_strategy))
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/detect-target", response_model=None, tags=["pipeline"])
async def detect_target(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
) -> APIResponse:
    """Detect the target column and task type."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import detect_target_async

        return await _submit_job(
            _run_and_cleanup(detect_target_async, tmp_path, engine, null_strategy)
        )
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/engineer", response_model=None, tags=["pipeline"])
async def engineer(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
    variance_threshold: float = Form(0.01),  # noqa: B008
    correlation_threshold: float = Form(0.05),  # noqa: B008
    min_features: int = Form(1),  # noqa: B008
) -> APIResponse:
    """Run feature engineering on a dataset."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import engineer_async

        return await _submit_job(
            _run_and_cleanup(
                engineer_async,
                tmp_path,
                engine,
                null_strategy,
                variance_threshold=variance_threshold,
                correlation_threshold=correlation_threshold,
                min_features=min_features,
            )
        )
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/recommend-model", response_model=None, tags=["pipeline"])
async def recommend_model(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
    variance_threshold: float = Form(0.01),  # noqa: B008
    correlation_threshold: float = Form(0.05),  # noqa: B008
    min_features: int = Form(1),  # noqa: B008
    cv: int | None = Form(None, description="Cross-validation folds (None=default split)."),  # noqa: B008
) -> APIResponse:
    """Recommend the best ML algorithm without training."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import select_model_async

        return await _submit_job(
            _run_and_cleanup(
                select_model_async,
                tmp_path,
                engine,
                null_strategy,
                variance_threshold=variance_threshold,
                correlation_threshold=correlation_threshold,
                min_features=min_features,
                cv=cv,
            )
        )
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/train", response_model=None, tags=["pipeline"])
async def train(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
    variance_threshold: float = Form(0.01),  # noqa: B008
    correlation_threshold: float = Form(0.05),  # noqa: B008
    min_features: int = Form(1),  # noqa: B008
    cv: int | None = Form(None, description="Cross-validation folds (None=default split)."),  # noqa: B008
) -> APIResponse:
    """Train the recommended model on a dataset (full pipeline)."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import train_async

        return await _submit_job(
            _run_and_cleanup(
                train_async,
                tmp_path,
                engine,
                null_strategy,
                variance_threshold=variance_threshold,
                correlation_threshold=correlation_threshold,
                min_features=min_features,
                cv=cv,
            )
        )
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/evaluate", response_model=None, tags=["pipeline"])
async def evaluate(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
    variance_threshold: float = Form(0.01),  # noqa: B008
    correlation_threshold: float = Form(0.05),  # noqa: B008
    min_features: int = Form(1),  # noqa: B008
    cv: int | None = Form(None, description="Cross-validation folds (None=default split)."),  # noqa: B008
) -> APIResponse:
    """Evaluate models on a dataset (includes model selection + evaluation)."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import select_model_async

        return await _submit_job(
            _run_and_cleanup(
                select_model_async,
                tmp_path,
                engine,
                null_strategy,
                variance_threshold=variance_threshold,
                correlation_threshold=correlation_threshold,
                min_features=min_features,
                cv=cv,
            )
        )
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/explain", response_model=None, tags=["pipeline"])
async def explain(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
    variance_threshold: float = Form(0.01),  # noqa: B008
    correlation_threshold: float = Form(0.05),  # noqa: B008
    min_features: int = Form(1),  # noqa: B008
) -> APIResponse:
    """Run SHAP-based model explainability."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import explain_async

        return await _submit_job(
            _run_and_cleanup(
                explain_async,
                tmp_path,
                engine,
                null_strategy,
                variance_threshold=variance_threshold,
                correlation_threshold=correlation_threshold,
                min_features=min_features,
            )
        )
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


@router.post("/report", response_model=None, tags=["pipeline"])
async def report(
    file: UploadFile = File(..., description="Dataset file."),  # noqa: B008
    engine: str | None = Form(None),  # noqa: B008
    null_strategy: str = Form("drop"),  # noqa: B008
    variance_threshold: float = Form(0.01),  # noqa: B008
    correlation_threshold: float = Form(0.05),  # noqa: B008
    min_features: int = Form(1),  # noqa: B008
) -> APIResponse:
    """Generate a full report for a dataset."""
    tmp_path = await _save_upload(file)
    try:
        from phronesisml.simple import report_async

        return await _submit_job(
            _run_and_cleanup(
                report_async,
                tmp_path,
                engine,
                null_strategy,
                variance_threshold=variance_threshold,
                correlation_threshold=correlation_threshold,
                min_features=min_features,
            )
        )
    except HTTPException:
        _cleanup_path(tmp_path)
        raise


# ── Internal helpers ─────────────────────────────────────────────


async def _run_and_cleanup(
    func: Any,
    path: str,
    engine: str | None,
    null_strategy: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run a simple-API async function and clean up the temp file."""
    try:
        result = await func(path, engine=engine, null_strategy=null_strategy, **kwargs)
        return _dataclass_to_dict(result)
    finally:
        _cleanup_path(path)
