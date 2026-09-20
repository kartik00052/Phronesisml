"""AUTH_MODE=supabase behavior — hermetic, no real Supabase required.

These tests run the *same* FastAPI app as the disabled-mode suite but flip
the frozen Settings so ``auth_enabled`` is true, with a fixed local test
JWT secret (HS256). This exercises the exact production code path:

- every protected HTTP endpoint requires a valid ``Authorization: Bearer``;
- missing / invalid / expired tokens return 401 with the shared envelope;
- the identity comes exclusively from the token's ``sub`` claim — never from
  a client-supplied user id/email;
- ownership isolation returns 404 (hidden) for foreign datasets/runs,
  artifacts, reports and prediction, across direct access and id tampering;
- the WebSocket endpoint rejects unauthenticated/invalid connections with
  4401 before accept, accepts the owning user, and refuses non-owners on the
  same run with 4404.

Database remains SQLite (unit-test level); only authentication is switched.
The real Supabase project (live JWT + JWKS + Postgres) is verified separately
by the make/scripts live check — never by these unit tests.
"""

from __future__ import annotations

import dataclasses
import time
import uuid
from collections.abc import Iterator

import jwt
import pytest
from starlette.websockets import WebSocketDisconnect

from backend.app import config as config_module
from backend.app.config import get_settings

TEST_SECRET = "supabase-mode-test-secret-not-for-production"
TEST_ISSUER = "https://test.supabase.co/auth/v1"
TEST_AUDIENCE = "authenticated"

USER_A = "aaaaaaaa-0000-4000-8000-a0000000000a"
USER_B = "bbbbbbbb-0000-4000-8000-b0000000000b"


def _token(
    sub: str,
    *,
    secret: str = TEST_SECRET,
    audience: str = TEST_AUDIENCE,
    issuer: str = TEST_ISSUER,
    ttl_seconds: int = 3600,
    extra: dict[str, object] | None = None,
) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": sub,
        "aud": audience,
        "iss": issuer,
        "iat": now,
        "exp": now + ttl_seconds,
        "role": "authenticated",
        "email": f"{sub}@example.com",
    }
    if extra:
        claims.update(extra)
    return jwt.encode(claims, secret, algorithm="HS256")


def _auth(sub: str = USER_A) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(sub)}"}


@pytest.fixture()
def supabase_client() -> Iterator[object]:
    """FastAPI TestClient running with AUTH_MODE=supabase (hermetic setup)."""
    from fastapi.testclient import TestClient

    from backend.app.main import app

    base = get_settings()
    if base.auth_enabled:
        pytest.fail("Test environment must start with AUTH_MODE=disabled.")
    mode = dataclasses.replace(
        base,
        auth_mode="supabase",
        supabase_jwt_secret=TEST_SECRET,
        supabase_jwt_issuer=TEST_ISSUER,
        supabase_jwt_audience=TEST_AUDIENCE,
    )
    config_module._settings = mode
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        config_module._settings = base


def _create_run_row() -> object:
    from backend.app.db import repositories

    return repositories.create_run(
        {
            "id": f"run_{uuid.uuid4().hex[:16]}",
            "name": "theirs",
            "dataset_name": "iris.csv",
            "user_id": USER_A,
        }
    )


# ─────────────────────────── Token rejection ───────────────────────────


def test_missing_token_returns_401(supabase_client) -> None:
    resp = supabase_client.get("/api/v1/runs")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "Unauthenticated"


def test_invalid_token_returns_401(supabase_client) -> None:
    resp = supabase_client.get("/api/v1/runs", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "Unauthenticated"


def test_expired_token_returns_401(supabase_client) -> None:
    expired = _token(USER_A, ttl_seconds=-3600)
    resp = supabase_client.get("/api/v1/runs", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "Unauthenticated"


def test_tampered_issuer_rejected(supabase_client) -> None:
    forged = _token(USER_A, issuer="https://evil.example/auth/v1")
    resp = supabase_client.get("/api/v1/runs", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


def test_valid_token_allows_request(supabase_client) -> None:
    resp = supabase_client.get("/api/v1/runs", headers=_auth())
    assert resp.status_code == 200
    assert "items" in resp.json()


# ─────────────────────── Identity comes from the JWT ─────────────────────


def test_identity_comes_from_sub_not_client_claims() -> None:
    """Token claims that lie about identity must not override the ``sub`` subject."""
    from backend.app.auth.verifier import verify_token

    token = _token(
        USER_A,
        extra={"user_id": "evil-injected-id", "email": "someone-elses@example.com"},
    )
    settings = dataclasses.replace(
        get_settings(),
        auth_mode="supabase",
        supabase_jwt_secret=TEST_SECRET,
        supabase_jwt_issuer=TEST_ISSUER,
    )
    resolved = verify_token(token, settings)
    assert resolved.user_id == USER_A
    assert resolved.email == "someone-elses@example.com"  # informational field only


def test_substitution_cannot_cross_users(supabase_client) -> None:
    """User A referencing User B's dataset id is treated as not-found (hidden)."""
    from backend.app.db import repositories

    ds = repositories.create_dataset(
        {
            "id": f"ds_{uuid.uuid4().hex[:16]}",
            "name": "b-data.csv",
            "path": f"/tmp/{uuid.uuid4().hex}.csv",
            "format": "csv",
            "user_id": USER_B,
        }
    )
    resp = supabase_client.post(
        "/api/v1/runs",
        json={"datasetId": ds.id, "nullStrategy": "drop", "mode": "fast", "stages": ["etl"]},
        headers=_auth(USER_A),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NotFound"


# ────────────────────────── Ownership isolation ──────────────────────────


def test_dataset_isolation_upload_and_read(supabase_client) -> None:
    from backend.app.config import ROOT_DIR

    iris = ROOT_DIR / "data" / "iris.csv"
    with iris.open("rb") as fh:
        upload = supabase_client.post(
            "/api/v1/datasets",
            files={"file": ("iris.csv", fh, "text/csv")},
            headers=_auth(USER_A),
        )
    assert upload.status_code == 201, upload.text
    ds_id = upload.json()["dataset"]["summary"]["id"]

    owned = supabase_client.get(f"/api/v1/datasets/{ds_id}", headers=_auth(USER_A))
    assert owned.status_code == 200, owned.text

    foreign = supabase_client.get(f"/api/v1/datasets/{ds_id}", headers=_auth(USER_B))
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "NotFound"


def test_run_and_descendants_hidden_from_foreign_user(supabase_client) -> None:
    run = _create_run_row()

    for owner, expect in ((USER_A, 200), (USER_B, 404)):
        resp = supabase_client.get(f"/api/v1/runs/{run.id}", headers=_auth(owner))
        assert resp.status_code == expect

    for path in (
        f"/api/v1/runs/{run.id}/artifacts",
        f"/api/v1/runs/{run.id}/report",
    ):
        foreign = supabase_client.get(path, headers=_auth(USER_B))
        assert foreign.status_code == 404, path

    predict = supabase_client.post(
        f"/api/v1/runs/{run.id}/predict",
        json={
            "samples": [
                {"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}
            ]
        },
        headers=_auth(USER_B),
    )
    assert predict.status_code == 404


def test_lists_are_scoped_in_supabase_mode(supabase_client) -> None:
    from backend.app.db import repositories

    a = repositories.create_run(
        {"id": f"run_{uuid.uuid4().hex[:16]}", "dataset_name": "iris.csv", "user_id": USER_A}
    )
    b = repositories.create_run(
        {"id": f"run_{uuid.uuid4().hex[:16]}", "dataset_name": "iris.csv", "user_id": USER_B}
    )

    mine = supabase_client.get("/api/v1/runs", headers=_auth(USER_A))
    assert mine.status_code == 200
    ids = [r["id"] for r in mine.json()["items"]]
    assert a.id in ids
    assert b.id not in ids


# ───────────────────────── WebSocket authentication ──────────────────────


def test_websocket_unauthenticated_rejected(supabase_client) -> None:
    run = _create_run_row()
    url = f"/api/v1/ws/runs/{run.id}?last_seq=0"
    with pytest.raises(WebSocketDisconnect) as exc, supabase_client.websocket_connect(url):
        pass
    assert exc.value.code == 4401


def test_websocket_invalid_token_rejected(supabase_client) -> None:
    run = _create_run_row()
    url = f"/api/v1/ws/runs/{run.id}?last_seq=0&access_token=not-a-jwt"
    with pytest.raises(WebSocketDisconnect) as exc, supabase_client.websocket_connect(url):
        pass
    assert exc.value.code == 4401


def test_websocket_owner_accepted(supabase_client) -> None:
    import json

    run = _create_run_row()
    token = _token(USER_A)
    url = f"/api/v1/ws/runs/{run.id}?last_seq=0&access_token={token}"
    with supabase_client.websocket_connect(url) as ws:
        assert "type" in json.loads(ws.receive_text())


def test_websocket_non_owner_rejected(supabase_client) -> None:
    run = _create_run_row()
    token = _token(USER_B)
    url = f"/api/v1/ws/runs/{run.id}?last_seq=0&access_token={token}"
    with pytest.raises(WebSocketDisconnect) as exc, supabase_client.websocket_connect(url):
        pass
    assert exc.value.code == 4404
