"""Run CRUD + websocket event stream over the real app."""

from __future__ import annotations

import json
import time

import pytest

RUN_PAYLOAD = {
    "datasetId": None,
    "nullStrategy": "drop",
    "stages": ["etl", "validation", "eda", "target_detection"],
    "mode": "fast",
    "maxTrials": 1,
    "engine": "pandas",
}


def _short_request(dataset_id: str) -> dict:
    payload = dict(RUN_PAYLOAD)
    payload["datasetId"] = dataset_id
    return payload


def test_create_and_list_runs(client, iris_dataset):
    resp = client.post("/api/v1/runs", json=_short_request(iris_dataset["summary"]["id"]))
    assert resp.status_code == 201, resp.text
    run = resp.json()
    assert "id" in run
    assert run["status"] in {"queued", "running", "completed"}
    runid = run["id"]

    listed = client.get("/api/v1/runs")
    assert listed.status_code == 200
    ids = [r["id"] for r in listed.json()["items"]]
    assert runid in ids

    detail = client.get(f"/api/v1/runs/{runid}")
    assert detail.status_code == 200
    for key in [
        "id",
        "status",
        "request",
        "summary",
        "sampling",
        "resourceReport",
        "warnings",
        "error",
        "logs",
        "stagesRequested",
        "stagesExecuted",
        "totalDurationMs",
        "createdAt",
        "updatedAt",
    ]:
        assert key in detail.json()

    logs = client.get(f"/api/v1/runs/{runid}/logs")
    assert logs.status_code == 200
    assert isinstance(logs.json(), list)

    run_dataset = client.get(f"/api/v1/runs/{runid}/dataset")
    assert run_dataset.status_code == 200
    assert run_dataset.json()["summary"]["name"] == "iris.csv"


def test_run_logs_falls_back_to_logs_txt(client, iris_dataset):
    from backend.app.config import get_settings

    resp = client.post("/api/v1/runs", json=_short_request(iris_dataset["summary"]["id"]))
    assert resp.status_code == 201, resp.text
    runid = resp.json()["id"]

    logs_txt = get_settings().run_storage_dir / runid / "logs.txt"
    logs_txt.parent.mkdir(parents=True, exist_ok=True)
    logs_txt.write_text("line one\n\nline two\n", encoding="utf-8")

    r = client.get(f"/api/v1/runs/{runid}/logs")
    assert r.status_code == 200, r.text
    assert r.json() == ["line one", "line two"], "blank lines must be stripped"


@pytest.mark.integration
def test_websocket_streams_replay(client, iris_dataset):
    resp = client.post("/api/v1/runs", json=_short_request(iris_dataset["summary"]["id"]))
    assert resp.status_code == 201, resp.text
    runid = resp.json()["id"]

    with client.websocket_connect(f"/api/v1/ws/runs/{runid}?last_seq=0") as ws:
        msg = json.loads(ws.receive_text())
        assert "type" in msg or "run_id" in msg or "event_type" in msg
        assert (
            msg.get("type") in {"replay.done", "run.started", "pipeline.stage", "ping"}
            or "type" in msg
        )


def test_cancel_restore_delete(client, iris_dataset):
    resp = client.post("/api/v1/runs", json=_short_request(iris_dataset["summary"]["id"]))
    assert resp.status_code == 201, resp.text
    runid = resp.json()["id"]

    cancel = client.post(f"/api/v1/runs/{runid}/cancel")
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] in {"cancelled", "running", "queued", "completed"}

    restore = client.post(f"/api/v1/runs/{runid}/restore")
    assert restore.status_code == 200, restore.text
    assert "id" in restore.json()

    for _ in range(1200):
        state = client.get(f"/api/v1/runs/{runid}").json()["status"]
        if state in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.05)
    assert state in {"completed", "failed"}, (
        "restored run must actually execute — a stale cancel flag leaves it cancelled"
    )

    delete = client.delete(f"/api/v1/runs/{runid}")
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True

    gone = client.get(f"/api/v1/runs/{runid}")
    assert gone.status_code == 404


def test_list_runs_filters_and_sorts(client, iris_dataset):
    first = client.post("/api/v1/runs", json=_short_request(iris_dataset["summary"]["id"]))
    second = client.post("/api/v1/runs", json=_short_request(iris_dataset["summary"]["id"]))
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    asc = client.get("/api/v1/runs", params={"sort": "createdAt", "order": "asc", "pageSize": 200})
    assert asc.status_code == 200, asc.text
    created = [r["createdAt"] for r in asc.json()["items"]]
    assert created == sorted(created), "asc must order by createdAt ascending"

    desc = client.get(
        "/api/v1/runs", params={"sort": "createdAt", "order": "desc", "pageSize": 200}
    )
    assert desc.status_code == 200, desc.text
    assert desc.json()["items"][0]["id"] in {first.json()["id"], second.json()["id"]}

    by_status = client.get("/api/v1/runs", params={"status": "queued"})
    assert by_status.status_code == 200, by_status.text
    assert all(r["status"] == "queued" for r in by_status.json()["items"])

    by_task = client.get("/api/v1/runs", params={"taskType": "unknown"})
    assert by_task.status_code == 200, by_task.text
    assert isinstance(by_task.json()["items"], list)
