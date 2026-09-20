"""Contract tests — /api/v1 health, capabilities, engine, error envelope."""

from __future__ import annotations


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "missing_core" in body
    assert "dependencies" in body
    assert "database" in body and body["database"]["reachable"] is True
    assert "storage" in body and body["storage"]["writable"] is True


def test_capabilities(client):
    resp = client.get("/api/v1/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert "name" in body
    assert "version" in body
    assert "task_types" in body and body["task_types"]
    assert "engines" in body and "pandas" in body["engines"]
    assert "explainers" in body
    assert "pipeline_stages" in body and "model_selection" in body["pipeline_stages"]
    assert "sdk_methods" in body
    assert "cli_commands" in body


def test_engine_recommend(client):
    resp = client.post("/api/v1/engine/recommend", json={"bytes": 2048, "rows": 150, "cols": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["engine"] == "pandas"
    assert "reason" in body


def test_error_envelope_is_nested(client):
    resp = client.get("/api/v1/datasets/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]


def test_404_unknown_route(client):
    resp = client.get("/api/v1/nope/not/a/thing")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body and "message" in body["error"]


def test_predict_requires_run(client):
    resp = client.post("/api/v1/runs/missing-run/predict", json={"samples": [{}]})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RunNotFound"
