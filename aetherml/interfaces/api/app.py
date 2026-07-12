"""FastAPI application for AetherML.

Creates the app, registers middleware and exception handlers, and
includes the API router.  No business logic lives here.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from aetherml import __version__
from aetherml.interfaces.api.models import APIResponse, ErrorDetail
from aetherml.interfaces.api.routes import router

logger = logging.getLogger(__name__)

DOCUMENTATION_BASE_URL = "https://docs.aetherml.ai/errors"

_OPENAPI_TAGS = [
    {"name": "system", "description": "Health, version, and capabilities."},
    {"name": "jobs", "description": "Asynchronous job management."},
    {
        "name": "pipeline",
        "description": "Run ML pipeline stages on uploaded datasets.",
    },
]

app = FastAPI(
    title="AetherML",
    description=(
        "Automated Machine Learning lifecycle SDK — REST API. "
        "Upload a dataset and get results. No ML expertise required."
    ),
    version=__version__,
    openapi_tags=_OPENAPI_TAGS,
    license_info={"name": "MIT"},
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware ────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


@app.middleware("http")
async def _request_timing_middleware(request: Request, call_next: Any) -> JSONResponse:
    """Attach X-Request-ID and X-Process-Time to every response."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    try:
        response: JSONResponse = await call_next(request)
    except Exception:
        logger.exception("Unhandled exception")
        body = APIResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
                details=None,
                documentation=f"{DOCUMENTATION_BASE_URL}/INTERNAL_ERROR",
            ),
        )
        response = JSONResponse(status_code=500, content=body.model_dump())
    elapsed = time.perf_counter() - start
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    return response


# ── Exception handlers ───────────────────────────────────────────


@app.exception_handler(RequestValidationError)
async def _validation_error_handler(
    _req: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert FastAPI validation errors to standard error envelope."""
    body = APIResponse(
        success=False,
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=exc.errors(),
            documentation=f"{DOCUMENTATION_BASE_URL}/VALIDATION_ERROR",
        ),
    )
    return JSONResponse(status_code=422, content=body.model_dump())


@app.exception_handler(HTTPException)
async def _http_exception_handler(
    _req: Request, exc: HTTPException
) -> JSONResponse:
    """Forward structured HTTPException detail to the response."""
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(Exception)
async def _unhandled_error_handler(_req: Request, exc: Exception) -> JSONResponse:
    """Catch-all: convert unhandled exceptions to standard error envelope."""
    logger.exception("Unhandled exception")
    body = APIResponse(
        success=False,
        error=ErrorDetail(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            details=None,
            documentation=f"{DOCUMENTATION_BASE_URL}/INTERNAL_ERROR",
        ),
    )
    return JSONResponse(status_code=500, content=body.model_dump())


# ── Router ───────────────────────────────────────────────────────

app.include_router(router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root redirect hint."""
    return {
        "message": "AetherML API is running.",
        "docs": "/docs",
        "health": "/health",
    }
