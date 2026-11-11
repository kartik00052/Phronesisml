"""Health endpoint contract used by Render's deploy gate."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint_is_ready(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"]["reachable"] is True
    assert body["storage"]["writable"] is True
    assert body["missing_core"] == []
