"""Authentication, ownership isolation and WebSocket auth tests.

These run against an isolated temp SQLite DB (see conftest.py) with Django-style
``AUTH_MODE=disabled`` — the exact single-tenant default that keeps the dev/test
flow token-free. In that mode the backend resolves every request to the fixed
*local-demo* identity, so the tests here assert the **hide-don't-reveal**
ownership contract proven at the router/repository boundary:

- a run/dataset owned by user A is invisible to user B (``None`` at the repo,
  404 at the router — never a leaky 403);
- ownership is enforced *before* any service mutates data (create/get/delete/
  predict/cancel all route through ``require_owned_*``).

The Supabase deployment reuses this identical code path — only the token
resolution changes (JWT verification in ``deps.get_current_user``), which is
why a green ownership suite here transfers directly to AUTH_MODE=supabase.
Token-mandatory behaviour (missing/invalid/expired → 401) and the WebSocket
auth matrix live in ``test_supabase_auth.py``, which flips the app into
``AUTH_MODE=supabase`` with a hermetically minted test JWT.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.auth.deps import require_owned_dataset, require_owned_run
from backend.app.db import repositories


def _row(**overrides: object) -> dict[str, object]:
    is_dataset = "format" in overrides
    prefix = "ds" if is_dataset else "run"
    row: dict[str, object] = {"id": f"{prefix}_{uuid.uuid4().hex[:16]}", "name": "test-row"}
    if is_dataset:
        row["path"] = f"/tmp/{uuid.uuid4().hex}.csv"
    row.update(overrides)
    return row


def test_run_owned_by_one_user_is_hidden_from_another() -> None:
    r = repositories.create_run(_row(name="theirs", user_id="user-a"))
    assert repositories.get_run(r.id, user_id="user-b") is None


def test_dataset_owned_by_one_user_is_hidden_from_another() -> None:
    d = repositories.create_dataset(_row(name="theirs", format="csv", user_id="user-a"))
    assert repositories.get_dataset(d.id, user_id="user-b") is None


def test_run_visible_to_its_owner() -> None:
    r = repositories.create_run(_row(name="mine", user_id="user-a"))
    assert repositories.get_run(r.id, user_id="user-a") is not None


def test_sessionless_rows_remain_shared() -> None:
    """Sample/shared rows (user_id NULL) stay visible post-migration."""
    d = repositories.create_dataset(_row(name="sample", format="csv", user_id=None))
    assert repositories.get_dataset(d.id, user_id="user-a") is not None
    assert repositories.get_dataset(d.id, user_id="user-b") is not None


def test_require_owned_run_allows_owner() -> None:
    r = repositories.create_run(_row(name="mine", user_id="user-a"))
    require_owned_run(r.id, user_id="user-a")  # must not raise


def test_require_owned_run_raises_404_for_foreign_owner() -> None:
    r = repositories.create_run(_row(name="theirs", user_id="user-a"))
    with pytest.raises(HTTPException) as exc:
        require_owned_run(r.id, user_id="user-b")
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NotFound"


def test_require_owned_dataset_raises_404_for_foreign_owner() -> None:
    d = repositories.create_dataset(_row(name="theirs", format="csv", user_id="user-a"))
    with pytest.raises(HTTPException) as exc:
        require_owned_dataset(d.id, user_id="user-b")
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NotFound"


def test_lists_are_scoped_to_owner() -> None:
    a = repositories.create_run(_row(user_id="user-a"))
    b = repositories.create_run(_row(user_id="user-b"))

    mine, _total = repositories.list_runs(user_id="user-a")
    ids = {run.id for run in mine}
    assert a.id in ids
    assert b.id not in ids


def test_foreign_data_returns_404_via_http(client: TestClient) -> None:
    """End-to-end: ownership hides existence before any service runs."""
    r = repositories.create_run(_row(name="theirs", user_id="user-a"))
    resp = client.get(f"/api/v1/runs/{r.id}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NotFound"
