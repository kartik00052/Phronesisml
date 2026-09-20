"""FastAPI application entrypoint. All routes are mounted under ``/api/v1``.

Startup runs the SQLite schema bootstrap (``init_db``) and attaches the
WebSocket hub to the app's event loop so worker threads can broadcast.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1 import api_router
from backend.app.config import get_settings
from backend.app.db.database import init_db
from backend.app.middleware import RequestContextMiddleware
from backend.app.ws.hub import HUB

settings = get_settings()


def _app_version() -> str:
    """Report the SDK's own version — never a hard-coded duplicate."""
    try:
        from phronesisml import __version__

        return str(__version__)
    except Exception:  # noqa: BLE001 - import must never break startup
        return "0.0.0+unknown"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    from backend.app.services.run_service import reconcile_interrupted_runs

    # No worker thread survives a process restart: mark any run left queued
    # or running as failed honestly instead of leaving it stuck forever.
    # Reconcile never auto-runs anything — recovery is always explicit.
    reconcile_interrupted_runs()
    if settings.seed_sample_datasets:
        from backend.app.services.dataset_service import seed_sample_datasets

        seed_sample_datasets(settings)
    import asyncio

    HUB.attach(asyncio.get_running_loop())
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=_app_version(),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(Exception, _internal_error_handler)
    app.add_exception_handler(HTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.include_router(api_router, prefix="/api/v1")

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        include_in_schema=False,
    )
    async def _unmatched_route(full_path: str) -> JSONResponse:
        """Starlette's router-level 404 bypasses exception handlers; surface
        it through the standard nested error envelope instead."""
        raise HTTPException(status_code=404, detail="Not Found")

    return app


async def _http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HttpError")
        message = str(detail.get("message") or detail.get("detail") or exc.detail)
        details = detail if detail.get("code") else None
    elif isinstance(detail, list):
        code = "ValidationError"
        message = "; ".join(str(item) for item in detail)
        details = None
    else:
        # Routers raise HTTPException(detail=<semantic code>) e.g. RunNotFound.
        # No whitespace ⇒ treat the string as the machine-readable code.
        if isinstance(detail, str) and detail and " " not in detail:
            code = detail
            message = detail
        else:
            code = "HttpError"
            message = str(detail)
        details = None
    return JSONResponse(status_code=exc.status_code, content=_error_payload(code, message, details))


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Wrap FastAPI's default 422 body in the shared nested error envelope."""
    problems = [
        {
            "location": ".".join(str(part) for part in err.get("loc", ())),
            "message": str(err.get("msg", "invalid value")),
            "type": str(err.get("type", "value_error")),
        }
        for err in exc.errors()
    ]
    message = (
        "; ".join(
            f"{p['location']}: {p['message']}" if p["location"] else p["message"] for p in problems
        )
        or "Request validation failed."
    )
    return JSONResponse(
        status_code=422,
        content=_error_payload("ValidationError", message, {"problems": problems}),
    )


async def _internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    import logging
    import traceback

    logging.getLogger(__name__).error("unhandled error on %s %s", request.method, request.url.path)
    logging.getLogger(__name__).error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=_error_payload("InternalError", "An unexpected server error occurred."),
    )


def _error_payload(
    code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload


app = create_app()


# Re-exported helpers used by routers/tests to build consistent error bodies.
def error_payload(code: str, message: str) -> dict[str, Any]:
    return _error_payload(code, message)
