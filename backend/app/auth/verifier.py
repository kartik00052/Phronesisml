"""Supabase access-token verification.

Supports the two signing models Supabase exposes:

- **HS256** with the project JWT secret (``SUPABASE_JWT_SECRET``) — used by
  most projects. This placeholder value is server-only: it is configured via
  environment and never shipped to the browser.
- **RS256/EdDSA** via the project's JWKS endpoint (``SUPABASE_URL`` or an
  explicit ``SUPABASE_JWKS_URL``) — newer RSA-key projects. Keys are fetched
  once and cached with a short TTL.

At least one server-side secret/endpoint must be configured before
``AUTH_MODE=supabase`` is enabled. Every valid token is checked for its
signature, ``exp``, ``aud`` (default ``authenticated``) and, when configured,
``iss``. The caller gets the identity from the verified claims — nothing from
the client is trusted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import jwt

from backend.app.config import Settings, get_settings

# Fixed identity used when AUTH_MODE=disabled (single-tenant dev/test).
# Distinct from any real Supabase UUID so ownership rules behave predictably.
DEV_USER_ID = "local-dev"

_JWKS_TTL_SECONDS = 900
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass(frozen=True)
class AuthUser:
    """Authenticated request context derived from a verified Supabase token."""

    user_id: str
    email: str | None = None
    role: str | None = None
    authenticated: bool = True
    raw_claims: dict[str, Any] = field(default_factory=dict)


class AuthError(Exception):
    """Raised when a token cannot be verified (missing, expired, or invalid)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def verify_token(token: str, settings: Settings | None = None) -> AuthUser:
    """Verify a Supabase access token and return the authenticated user.

    Raises :class:`AuthError` for every failure mode. Callers map that to a
    401 response — they never fabricate an identity themselves.
    """
    settings = settings or get_settings()
    audiences = [settings.supabase_jwt_audience] if settings.supabase_jwt_audience else None
    issuer = settings.resolved_supabase_jwt_issuer
    token = token.strip()
    if not token:
        raise AuthError("Unauthenticated", "Missing access token.")

    strategies: list[tuple[str, Any]] = []
    if settings.supabase_jwt_secret:
        strategies.append(("HS256", settings.supabase_jwt_secret))
    jwks_url = settings.resolved_supabase_jwks_url
    if jwks_url:
        strategies.append(("JWKS", jwks_url))

    if not strategies:
        raise AuthError(
            "Misconfigured",
            "Authentication is enabled but no JWT secret or JWKS endpoint is configured.",
        )

    last_error: Exception = AuthError("Unauthenticated", "Invalid access token.")
    for kind, material in strategies:
        try:
            if kind == "HS256":
                claims = jwt.decode(
                    token,
                    material,
                    algorithms=["HS256"],
                    audience=audiences,
                    issuer=issuer,
                    leeway=30,
                )
            else:
                claims = _decode_with_jwks(token, str(material), audiences, issuer)
            return _from_claims(claims)
        except AuthError:
            raise
        except Exception as exc:  # noqa: BLE001 - collate and keep trying
            last_error = exc
    raise AuthError("Unauthenticated", _describe_failure(str(last_error)))


def _decode_with_jwks(
    token: str,
    url: str,
    audiences: list[str] | None,
    issuer: str | None,
) -> dict[str, Any]:
    signing_key = _jwks_signing_key(url, token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[signing_key.algorithm_name],
        audience=audiences,
        issuer=issuer,
        leeway=30,
    )


def _jwks_signing_key(url: str, token: str) -> Any:
    jwks = _fetch_jwks(url)
    key_set = jwt.PyJWKSet.from_dict(jwks)
    return key_set.get_signing_key_from_jwt(token)


def _fetch_jwks(url: str) -> dict[str, Any]:
    now = time.monotonic()
    cached = _jwks_cache.get(url)
    if cached and now - cached[0] < _JWKS_TTL_SECONDS:
        return cached[1]
    import httpx

    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        raise AuthError("JwksUnreachable", "Supabase JWKS endpoint could not be reached.") from exc
    payload = response.json()
    if not isinstance(payload, dict) or "keys" not in payload:
        raise AuthError("JwksInvalid", "Supabase JWKS endpoint returned an unexpected payload.")
    _jwks_cache[url] = (time.monotonic(), payload)
    return payload


def _from_claims(claims: dict[str, Any]) -> AuthUser:
    sub = claims.get("sub") or claims.get("user_id")
    if not sub:
        raise AuthError("Unauthenticated", "Token is missing the subject claim.")
    email = claims.get("email")
    return AuthUser(
        user_id=str(sub),
        email=str(email) if email else None,
        role=str(claims["role"]) if claims.get("role") else None,
        authenticated=True,
        raw_claims=claims,
    )


def _describe_failure(message: str) -> str:
    if "expired" in message.lower() or "signature has expired" in message.lower():
        return "The access token has expired."
    return "Invalid access token."