"""Tests for the AetherML REST API (FastAPI)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from aetherml import __version__
from aetherml.interfaces.api.app import app
from aetherml.interfaces.api.models import ErrorResponse, HealthResponse, PipelineRequest


@pytest.fixture()
def client() -> Any:
    """Create a test client from the FastAPI app."""
    from starlette.testclient import TestClient

    return TestClient(app)


class TestHealthEndpoint:
    """GET /health"""

    def test_returns_200(self, client: Any) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_version_matches_sdk(self, client: Any) -> None:
        body = client.get("/health").json()
        assert body["version"] == __version__
        assert body["status"] == "ok"

    def test_python_field_present(self, client: Any) -> None:
        body = client.get("/health").json()
        assert "python" in body
        assert isinstance(body["python"], str)


class TestPipelineEndpoint:
    """POST /pipeline"""

    def test_missing_data_path_returns_422(self, client: Any) -> None:
        resp = client.post("/pipeline", json={})
        assert resp.status_code == 422

    def test_empty_data_path_returns_422(self, client: Any) -> None:
        resp = client.post("/pipeline", json={"data_path": ""})
        assert resp.status_code == 422

    def test_rejects_extra_fields(self, client: Any) -> None:
        resp = client.post(
            "/pipeline",
            json={"data_path": "dummy.csv", "unknown_field": True},
        )
        assert resp.status_code == 422

    def test_validates_enum_null_strategy(self, client: Any) -> None:
        resp = client.post(
            "/pipeline",
            json={"data_path": "dummy.csv", "null_strategy": "bogus"},
        )
        assert resp.status_code == 422

    def test_success_returns_200(self, client: Any) -> None:
        mock_result = {"row_count": 100, "column_count": 5}
        with patch(
            "aetherml.interfaces.api.app.run_pipeline",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = client.post("/pipeline", json={"data_path": "dummy.csv"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"
            assert body["result"]["row_count"] == 100

    def test_workflow_error_returns_500(self, client: Any) -> None:
        from aetherml.exceptions import WorkflowError

        with patch(
            "aetherml.interfaces.api.app.run_pipeline",
            new_callable=AsyncMock,
            side_effect=WorkflowError("bad graph"),
        ):
            resp = client.post("/pipeline", json={"data_path": "dummy.csv"})
            assert resp.status_code == 500

    def test_config_error_returns_422(self, client: Any) -> None:
        from aetherml.exceptions import ConfigurationError

        with patch(
            "aetherml.interfaces.api.app.run_pipeline",
            new_callable=AsyncMock,
            side_effect=ConfigurationError("bad config"),
        ):
            resp = client.post("/pipeline", json={"data_path": "dummy.csv"})
            assert resp.status_code == 422


class TestModels:
    """Pydantic request/response models."""

    def test_pipeline_request_defaults(self) -> None:
        req = PipelineRequest(data_path="data.csv")
        assert req.engine is None
        assert req.null_strategy == "drop"
        assert req.stages is None

    def test_pipeline_request_rejects_empty_data_path(self) -> None:
        with pytest.raises(ValidationError):
            PipelineRequest(data_path="")

    def test_health_response_fields(self) -> None:
        resp = HealthResponse(status="ok", version="0.1.0", python="3.11.0")
        d = resp.model_dump()
        assert d["status"] == "ok"
        assert d["version"] == "0.1.0"

    def test_error_response_fields(self) -> None:
        resp = ErrorResponse(error_type="WorkflowError", message="failed")
        d = resp.model_dump()
        assert d["error_type"] == "WorkflowError"
        assert d["message"] == "failed"
