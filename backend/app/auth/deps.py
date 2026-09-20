"""Shared authentication/authorization FastAPI dependencies.

Protected endpoints add ``user: AuthUser = Depends(get_current_user)`` and
then use ``require_owned_run`` / ``require_owned_dataset`` to enforce server-
side ownership. The identity always comes from ``verifier.verify_token`` —
never from a client-supplied user id.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, WebSocket

from backend.app.api.deps import not_found
from backend.app.auth.verifier import (
    DEV_USER_ID,
    AuthError,
    AuthUser,
    verify_token,
)
from backend.app.config import get_settings
from backend.app.db import repositories

WWW_AUTHENTICATE = "Bearer"


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthUser:
    """Resolve the authenticated user for a protected HTTP endpoint.

    With ``AUTH_MODE=disabled`` returns the fixed local-dev identity so the
    single-tenant dev/test flow needs no token. With ``AUTH_MODE=supabase`` a
    valid ``Authorization: Bearer <token>`` header is required.
    """
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthUser(user_id=DEV_USER_ID, role="local", authenticated=False)
    token = _extract_bearer(authorization)
    if not token:
        raise _unauthorized("Missing access token.")
    try:
        return verify_token(token, settings)
    except AuthError as exc:
        raise _unauthorized(str(exc), exc) from exc


def get_websocket_user(websocket: WebSocket) -> AuthUser:
    """Resolve the authenticated user for a WebSocket connection.

    Accepted token sources (checked in order): ``access_token``/``token``
    query parameters, then ``Authorization: Bearer``. Returning the local-dev
    identity when auth is disabled keeps the dev flow token-free.
    """
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthUser(user_id=DEV_USER_ID, role="local", authenticated=False)
    token = websocket.query_params.get("access_token") or websocket.query_params.get("token")
    if not token:
        token = _extract_bearer(websocket.headers.get("authorization"))
    if not token:
        raise AuthError("Unauthenticated", "Missing access token.")
    return verify_token(token, settings)


def require_owned_dataset(dataset_id: str, user_id: str) -> None:
    """404 (hidden) unless the dataset exists and belongs to *user_id*."""
    if repositories.get_dataset(dataset_id, user_id=user_id) is None:
        raise not_found("Dataset", dataset_id)


def require_owned_run(run_id: str, user_id: str) -> None:
    """404 (hidden) unless the run exists and belongs to *user_id*."""
    if repositories.get_run(run_id, user_id=user_id) is None:
        raise not_found("Run", run_id)


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def _unauthorized(message: str, exc: AuthError | None = None) -> HTTPException:
    detail = {"code": "Unauthenticated", "message": message}
    if exc is not None and exc.code == "Misconfigured":
        detail = {"code": "Misconfigured", "message": message}
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": WWW_AUTHENTICATE},
    )