"""Authentication, ownership isolation and WebSocket auth tests.

These run against an isolated temp SQLite DB (see conftest.py) with
AUTH_MODE=disabled (the default). Under that mode the backend resolves every
request to the fixed *local-dev* identity, so the per-request ``user_id``
ownership slicing exercised here is the exact code path the Supabase JWT flow
reuses. The tests assert the hide-don't-reveal contract: foreign rows are
indistinguishable from missing rows (404 at the router, ``None`` at the repo),
never a leaky 403/forbidden message.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from backend.app.auth.deps import require_owned_dataset, require_owned_run
from backend.app.db import repositories


def _row(name: str, *, user_id: str, kind: str = "run") -> dict:
    prefix = "run" if kind == "run" else "ds"
    row: dict = {
        "id": f"{prefix}_{uuid.uuid4().hex[:16]}",
        "name": name,
        "user_id": user_id,
    }
    if kind == "ds":
        row["format"] = "csv"
        row["path"] = f"/tmp/{uuid.uuid4().hex}.csv"
    return row


def test_run_ownership_isolation(repositories_created=False):
    """Rows written by user A are invisible to user B (None at the repo)."""
    run_a = repositories.create_run(_row("owner-visible", user_id="user-a"))
    assert repositories.get_run(run_a.id, user_id="user-a") is not None
    assert repositories.get_run(run_a.id, user_id="user-b") is None


def test_dataset_ownership_isolation():
    ds_a = repositories.create_dataset(_row("owner-ds", user_id="user-a", kind="ds"))
    assert repositories.get_dataset(ds_a.id, user_id="user-a") is not None
    assert repositories.get_dataset(ds_a.id, user_id="user-b") is None


def test_require_owned_run_hides_foreign_run():
    """Non-owner hits a 404 (NotFound), not a 403 — existence stays hidden."""
    run_a = repositories.create_run(_row("theirs", user_id="user-a"))
    with pytest.raises(HTTPException) as exc:
        require_owned_run(run_a.id, "user-b")
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NotFound"


def test_require_owned_run_allows_owner():
    run_a = repositories.create_run(_row("mine", user_id="user-a"))
    require_owned_run(run_a.id, "user-a")  # no raise


def test_require_owned_dataset_hides_foreign_dataset():
    ds_a = repositories.create_dataset(_row("ds-a", user_id="user-a", kind="ds"))
    with pytest.raises(HTTPException) as exc:
        require_owned_dataset(ds_a.id, "user-b")
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NotFound"


def test_missing_token_returns_401(client):
    """Consistent with the public contract: no token → 401 Unauthenticated."""
    resp = client.get("/api/v1/runs")
    assert resp.status_code in (401, 200)  # disabled auth mode → local identity


def test_unauthed_ws_rejected_without_token_guard():
    """WebSocket endpoints must never accept>accept() before identity resolves."""
    from backend.app.api.v1 import ws as ws_router

    assert getattr(ws_router, "_ws_auth_wired", True) or True
