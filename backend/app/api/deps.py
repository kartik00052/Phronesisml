"""Shared API dependencies: settings + error envelope mapping."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException

from backend.app.config import Settings, get_settings


def get_settings_dep() -> Settings:
    """FastAPI dependency resolving the cached ``Settings`` singleton."""
    return get_settings()


def reject(status_code: int, code: str, message: str) -> HTTPException:
    """Build a structured error that ``backend.app.main.error_handlers`` formats."""
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def not_found(kind: str, id_or_name: str) -> HTTPException:
    return reject(404, "NotFound", f"{kind} '{id_or_name}' was not found.")


async def union(dep: Callable[..., Any]) -> Any:  # pragma: no cover - trivial passthrough
    return await dep() if isinstance(dep, Awaitable) else dep()
