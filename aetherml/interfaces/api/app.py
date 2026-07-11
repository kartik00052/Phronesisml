"""FastAPI application for AetherML.

Endpoints:
    POST /pipeline  — run the full ML pipeline on a dataset
    GET  /health    — liveness / version check
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from aetherml import __version__, run_pipeline
from aetherml.exceptions import AetherMLError, ConfigurationError, WorkflowError
from aetherml.interfaces.api.models import (
    ErrorResponse,
    HealthResponse,
    PipelineRequest,
    PipelineResponse,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AetherML",
    description="Automated Machine Learning lifecycle SDK — REST API.",
    version=__version__,
)


@app.exception_handler(AetherMLError)
async def _aetherml_error_handler(_req: Any, exc: AetherMLError) -> JSONResponse:
    body = ErrorResponse(
        error_type=type(exc).__name__,
        message=str(exc),
    )
    return JSONResponse(status_code=422, content=body.model_dump())


@app.exception_handler(WorkflowError)
async def _workflow_error_handler(_req: Any, exc: WorkflowError) -> JSONResponse:
    body = ErrorResponse(
        error_type="WorkflowError",
        message=str(exc),
    )
    return JSONResponse(status_code=500, content=body.model_dump())


@app.exception_handler(ConfigurationError)
async def _config_error_handler(_req: Any, exc: ConfigurationError) -> JSONResponse:
    body = ErrorResponse(
        error_type="ConfigurationError",
        message=str(exc),
    )
    return JSONResponse(status_code=422, content=body.model_dump())


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Liveness and version check."""
    return HealthResponse(
        status="ok",
        version=__version__,
        python=sys.version,
    )


@app.post(
    "/pipeline",
    response_model=PipelineResponse,
    responses={
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["pipeline"],
)
async def run_pipeline_endpoint(body: PipelineRequest) -> PipelineResponse:
    """Run the AetherML pipeline on a dataset."""
    try:
        result = await run_pipeline(
            data_path=body.data_path,
            engine_preference=body.engine,
            null_strategy=body.null_strategy,
            stages=body.stages,
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AetherMLError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PipelineResponse(status="ok", result=result)
