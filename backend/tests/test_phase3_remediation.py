"""Phase-3 remediation backend tests.

Covers the integration points that were previously gaps:

* sample dataset seeding (idempotent, sample-flagged, never auto-runs)
* delete safety (refuse paths outside the storage root)
* capabilities `optional_models` (real importlib probing, no hard-coding)
* engine capabilities reflecting the *installed* backends
* engine recommendation delegating to the SDK's single source of truth
"""

from __future__ import annotations

import importlib
import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient


def _probe(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:  # noqa: BLE001
        return False


# ─────────────────── sample dataset seeding ───────────────────────


def test_sample_datasets_seed_idempotent_and_never_auto_run(client: TestClient):
    from backend.app.db import repositories
    from backend.app.services import dataset_service

    runs_before = len(repositories.list_runs())

    first = dataset_service.seed_sample_datasets()
    assert len(first) >= 1, "iris/credit-card sample datasets should register"
    assert all(row["summary"]["sample"] is True for row in first)
    names = {row["summary"]["name"] for row in first}
    assert {"iris.csv", "credit_card_clients.csv"}.issubset(names)

    second = dataset_service.seed_sample_datasets()
    assert second == [], "seeding must be idempotent (no duplicate rows)"

    # Seeding must never create runs or change run state.
    assert len(repositories.list_runs()) == runs_before

    # The seeded rows are visible through the API, flagged as samples,
    # browsable, and stored inside the (temp) storage root so deletes are safe.
    listed = client.get("/api/v1/datasets").json()["items"]
    samples = [d for d in listed if d.get("sample")]
    sample_names = {d["name"] for d in samples}
    assert {"iris.csv", "credit_card_clients.csv"}.issubset(sample_names)

    iris_id = next(d["id"] for d in samples if d["name"] == "iris.csv")
    detail = client.get(f"/api/v1/datasets/{iris_id}")
    assert detail.status_code == 200
    assert detail.json()["summary"]["rows"] == 150


def test_seeded_sample_rows_are_deletable(client: TestClient):
    from backend.app.db import repositories
    from backend.app.services import dataset_service

    # Reuse an already-seeded sample row when present (tests share a session DB).
    rows, _total = repositories.list_datasets()
    existing = [r for r in rows if r.sample]
    if existing:
        ds_id = existing[0].id
    else:
        first = dataset_service.seed_sample_datasets()
        assert first, "expected samples to seed"
        ds_id = first[0]["summary"]["id"]

    deleted = client.delete(f"/api/v1/datasets/{ds_id}")
    assert deleted.status_code == 200
    body = deleted.json()
    assert body["deleted"] is True or body["id"] == ds_id


# ─────────────────── delete path safety ───────────────────────────


def test_delete_refuses_path_outside_storage_root():
    from backend.app.db import repositories
    from backend.app.services import dataset_service

    evil = Path("/tmp") / f"phronesisml-outside-{uuid.uuid4().hex[:8]}"
    evil.mkdir(parents=True, exist_ok=True)
    target = evil / "do-not-delete.txt"
    target.write_text("keep me")
    try:
        repositories.create_dataset(
            {
                "id": "ds_outside_root",
                "name": "evil.csv",
                "path": str(target),
                "format": "csv",
                "size_bytes": 7,
                "rows": 1,
                "columns": 1,
                "sample": False,
            }
        )
        result = dataset_service.delete_dataset("ds_outside_root")
        assert result == {"deleted": False, "id": "ds_outside_root"}
        assert target.exists(), "file outside storage root must not be removed"
        # The flagged row is still registered.
        assert repositories.get_dataset("ds_outside_root") is not None
    finally:
        shutil.rmtree(evil, ignore_errors=True)


# ─────────────────── capabilities: optional models ────────────────


def test_capabilities_reports_real_optional_models(client: TestClient):
    resp = client.get("/api/v1/capabilities")
    assert resp.status_code == 200
    body = resp.json()

    models = body.get("optional_models")
    assert models is not None, "capabilities must advertise optional_models"
    assert [m["name"] for m in models] == ["xgboost", "lightgbm", "catboost"]
    for m in models:
        assert m["optional"] is True
        assert m["installed"] == _probe(m["name"])
        if m["installed"]:
            assert m.get("version")
        else:
            assert m.get("reason")


def test_engine_capabilities_reflect_installed_backends(client: TestClient):
    resp = client.get("/api/v1/engine/capabilities")
    assert resp.status_code == 200
    body = resp.json()

    assert body["engines"] == ["pandas", "polars", "spark"]
    assert "pandas" in body["enginesAvailable"]
    assert "pandas" not in body["enginesMissing"]
    if _probe("polars"):
        assert "polars" in body["enginesAvailable"]
    else:
        assert "polars" in body["enginesMissing"]
    if _probe("pyspark"):
        assert "spark" in body["enginesAvailable"]
    else:
        assert "spark" in body["enginesMissing"]


# ─────────────────── engine recommend (SDK delegation) ────────────


def test_engine_recommend_uses_sdk_decide(client: TestClient):
    from phronesisml.engines.recommend import recommend_engine

    payload = {"bytes": 1_000, "rows": 10, "cols": 3}
    resp = client.post("/api/v1/engine/recommend", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    expected = recommend_engine(n_rows=10, n_cols=3, memory_bytes=1_000)
    assert body["engine"] == expected["engine"]
    assert body["reason"] == expected["reason"]
    assert body["routing"]["n_rows"] == expected["routing"]["n_rows"]
    assert body["routing"]["n_cols"] == expected["routing"]["n_cols"]

    # A tiny file must route to pandas (single source of truth).
    assert body["engine"] == "pandas"
