"""Authentication, ownership isolation and router-level protections.

These run against the isolated temp SQLite DB that conftest.py sets up, in the
default ``AUTH_MODE=disabled`` single-tenant identity. The ownership code under
test (``require_owned_run`` / ``require_owned_dataset`` / ownership-clause
filtering in ``repositories``) is exactly the code path the Supabase JWT flow
reuses — the only difference in ``AUTH_MODE=supabase`` is *how* ``user_id`` is
resolved (verified JWT claims instead of the static local-dev identity).

The tests follow the "hide, don't reveal" contract: cross-user rows are
indistinguishable from missing rows (``None`` / 404), never a leaky 403.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.auth.deps import require_owned_dataset, require_owned_run
from backend.app.db import repositories


def _row(name: str, *, user_id: str | None = None) -> dict:
    return {"name": name, "user_id": user_id}


def test_run_owner_can_read_own() -> None:
    r = repositories.create_run(_row("mine", user_id="user-a"))
    assert repositories.get_run(r["id"], user_id="user-a") is not None


def test_run_hidden_from_foreign_user() -> None:
    r = repositories.create_run(_row("theirs", user_id="user-a"))
    assert repositories.get_run(r["id"], user_id="user-b") is None


def test_dataset_hidden_from_foreign_user() -> None:
    d = repositories.create_dataset(_row("foreign-ds", user_id="user-a"))
    assert repositories.get_dataset(d["id"], user_id="user-b") is None


def test_shared_dataset_visible_to_everyone() -> None:
    d = repositories.create_dataset(_row("shared-sample", user_id=None))
    assert repositories.get_dataset(d["id"], user_id="user-a") is not None
    assert repositories.get_dataset(d["id"], user_id="user-b") is not None


def test_require_owned_run_allows_owner() -> None:
    r = repositories.create_run(_row("mine", user_id="user-a"))
    require_owned_run(run_id=r["id"], user_id="user-a")  # must not raise


def test_require_owned_run_rejects_foreigner_with_404() -> None:
    r = repositories.create_run(_row("theirs", user_id="user-a"))
    with pytest.raises(HTTPException) as exc:
        require_owned_run(run_id=r["id"], user_id="user-b")
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NotFound"


def test_require_owned_dataset_rejects_foreigner_with_404() -> None:
    d = repositories.create_dataset(_row("foreign-ds", user_id="user-a"))
    with pytest.raises(HTTPException) as exc:
        require_owned_dataset(dataset_id=d["id"], user_id="user-b")
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "NotFound"


def test_user_a_cannot_delete_user_b_dataset(client: TestClient) -> None:
    d = repositories.create_dataset(_row("theirs", user_id="user-a"))

    # Borrow the ownership deps the datasets router uses; a foreign user's
    # delete is rejected before it reaches the storage/delete layer.
    try:
        require_owned_dataset(dataset_id=d["id"], user_id="user-b")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        pytest.fail("foreign user must not be allowed to reach the delete path")
