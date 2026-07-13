"""Comprehensive tests for the Phronesis Enterprise REST API."""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from phronesisml import __version__
from phronesisml.interfaces.api.app import app
from phronesisml.interfaces.api.jobs import job_store
from phronesisml.interfaces.api.models import (
    ALLOWED_EXTENSIONS,
    APIResponse,
    CapabilitiesData,
    ErrorDetail,
    HealthData,
    JobData,
    VersionData,
)


@pytest.fixture()
def client() -> Any:
    """Create a test client from the FastAPI app."""
    from starlette.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _reset_job_store() -> Any:
    """Reset the global job store before each test."""
    job_store._jobs.clear()
    yield
    job_store._jobs.clear()


def _csv_bytes(content: str = "a,b\n1,2\n3,4") -> bytes:
    return content.encode("utf-8")


def _make_file(
    name: str = "data.csv",
    content: bytes | None = None,
) -> dict[str, tuple[str, io.BytesIO, str]]:
    return {"file": (name, io.BytesIO(content or _csv_bytes()), "text/csv")}


# ── System endpoints ─────────────────────────────────────────────


class TestHealthEndpoint:
    """GET /health"""

    def test_returns_200(self, client: Any) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_success_true(self, client: Any) -> None:
        body = client.get("/health").json()
        assert body["success"] is True

    def test_version_matches_sdk(self, client: Any) -> None:
        data = client.get("/health").json()["data"]
        assert data["version"] == __version__

    def test_engines_listed(self, client: Any) -> None:
        data = client.get("/health").json()["data"]
        assert "pandas" in data["engines"]

    def test_platform_present(self, client: Any) -> None:
        data = client.get("/health").json()["data"]
        assert data["platform"] in ("windows", "linux", "darwin")


class TestVersionEndpoint:
    """GET /version"""

    def test_returns_200(self, client: Any) -> None:
        resp = client.get("/version")
        assert resp.status_code == 200

    def test_version_matches_sdk(self, client: Any) -> None:
        data = client.get("/version").json()["data"]
        assert data["version"] == __version__

    def test_sdk_field(self, client: Any) -> None:
        data = client.get("/version").json()["data"]
        assert data["sdk"] == "Phronesis"


class TestCapabilitiesEndpoint:
    """GET /capabilities"""

    def test_returns_200(self, client: Any) -> None:
        resp = client.get("/capabilities")
        assert resp.status_code == 200

    def test_file_formats(self, client: Any) -> None:
        data = client.get("/capabilities").json()["data"]
        assert "csv" in data["file_formats"]
        assert "xlsx" in data["file_formats"]

    def test_engines(self, client: Any) -> None:
        data = client.get("/capabilities").json()["data"]
        assert "pandas" in data["engines"]

    def test_pipeline_stages(self, client: Any) -> None:
        data = client.get("/capabilities").json()["data"]
        assert "upload" in data["pipeline_stages"]
        assert "storage" in data["pipeline_stages"]

    def test_limits(self, client: Any) -> None:
        data = client.get("/capabilities").json()["data"]
        assert "max_upload_size_mb" in data["limits"]

    def test_job_persistence_documented(self, client: Any) -> None:
        data = client.get("/capabilities").json()["data"]
        assert "job_persistence" in data
        assert data["job_persistence"] == "in-memory-single-process"


# ── Middleware ────────────────────────────────────────────────────


class TestMiddleware:
    """Request ID, timing, and CORS headers."""

    def test_request_id_header_present(self, client: Any) -> None:
        resp = client.get("/health")
        assert "X-Request-ID" in resp.headers

    def test_request_id_from_client_preserved(self, client: Any) -> None:
        resp = client.get("/health", headers={"X-Request-ID": "test-id-123"})
        assert resp.headers["X-Request-ID"] == "test-id-123"

    def test_timing_header_present(self, client: Any) -> None:
        resp = client.get("/health")
        assert "X-Process-Time" in resp.headers
        assert float(resp.headers["X-Process-Time"]) >= 0

    def test_cors_headers_present(self, client: Any) -> None:
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers


# ── Error response format ────────────────────────────────────────


class TestErrorResponseFormat:
    """All errors use the standard APIResponse + ErrorDetail envelope."""

    def test_error_has_success_false(self, client: Any) -> None:
        resp = client.post("/analyze", data={})
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False

    def test_error_has_error_detail(self, client: Any) -> None:
        resp = client.post("/analyze", data={})
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert "documentation" in body["error"]


# ── File upload validation ───────────────────────────────────────


class TestFileUploadValidation:
    """File type, size, and content validation."""

    def test_missing_file_returns_422(self, client: Any) -> None:
        resp = client.post("/analyze", data={})
        assert resp.status_code == 422

    def test_unsupported_format_returns_415(self, client: Any) -> None:
        resp = client.post(
            "/analyze",
            files={"file": ("data.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        assert resp.status_code == 415
        body = resp.json()
        assert body["error"]["code"] == "UNSUPPORTED_FORMAT"

    def test_empty_file_returns_422(self, client: Any) -> None:
        resp = client.post(
            "/analyze",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "EMPTY_FILE"

    def test_csv_accepted(self, client: Any) -> None:
        with patch(
            "phronesisml.interfaces.api.routes._run_and_cleanup",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ):
            resp = client.post(
                "/analyze",
                files=_make_file("data.csv"),
            )
            assert resp.status_code == 200

    def test_xlsx_accepted(self, client: Any) -> None:
        with patch(
            "phronesisml.interfaces.api.routes._run_and_cleanup",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ):
            resp = client.post(
                "/analyze",
                files=_make_file("data.xlsx"),
            )
            assert resp.status_code == 200

    def test_json_accepted(self, client: Any) -> None:
        with patch(
            "phronesisml.interfaces.api.routes._run_and_cleanup",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ):
            resp = client.post(
                "/analyze",
                files=_make_file("data.json"),
            )
            assert resp.status_code == 200


# ── Pipeline endpoints (happy path) ──────────────────────────────


class TestPipelineEndpoints:
    """POST /analyze, /clean, /validate, etc."""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/analyze",
            "/clean",
            "/validate",
            "/detect-target",
            "/engineer",
            "/recommend-model",
            "/train",
            "/evaluate",
            "/explain",
            "/report",
        ],
    )
    def test_all_endpoints_return_200_with_valid_file(self, client: Any, endpoint: str) -> None:
        with patch(
            "phronesisml.interfaces.api.routes._run_and_cleanup",
            new_callable=AsyncMock,
            return_value={"result": "ok"},
        ):
            resp = client.post(endpoint, files=_make_file())
            assert resp.status_code == 200, f"{endpoint} returned {resp.status_code}"

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/analyze",
            "/clean",
            "/validate",
            "/detect-target",
            "/engineer",
            "/recommend-model",
            "/train",
            "/evaluate",
            "/explain",
            "/report",
        ],
    )
    def test_all_endpoints_return_job_id(self, client: Any, endpoint: str) -> None:
        with patch(
            "phronesisml.interfaces.api.routes._run_and_cleanup",
            new_callable=AsyncMock,
            return_value={"result": "ok"},
        ):
            resp = client.post(endpoint, files=_make_file())
            body = resp.json()
            assert body["success"] is True
            assert "job_id" in body["data"]
            assert body["data"]["status"] in ("queued", "running", "completed")


# ── Job system ───────────────────────────────────────────────────


class TestJobSystem:
    """GET /jobs and GET /jobs/{job_id}"""

    def test_get_nonexistent_job_returns_404(self, client: Any) -> None:
        resp = client.get("/jobs/nonexistent-id")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "JOB_NOT_FOUND"

    def test_list_jobs_returns_empty(self, client: Any) -> None:
        resp = client.get("/jobs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []

    def test_list_jobs_returns_created_job(self, client: Any) -> None:
        with patch(
            "phronesisml.interfaces.api.routes._run_and_cleanup",
            new_callable=AsyncMock,
            return_value={"result": "ok"},
        ):
            client.post("/analyze", files=_make_file())
        resp = client.get("/jobs")
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["status"] in ("queued", "running", "completed")


# ── Pydantic models ─────────────────────────────────────────────


class TestModels:
    """Pydantic model validation."""

    def test_api_response_success(self) -> None:
        resp = APIResponse(success=True, data={"key": "value"})
        d = resp.model_dump()
        assert d["success"] is True
        assert d["data"]["key"] == "value"

    def test_api_response_error(self) -> None:
        resp = APIResponse(
            success=False,
            error=ErrorDetail(code="TEST", message="test error"),
        )
        d = resp.model_dump()
        assert d["success"] is False
        assert d["error"]["code"] == "TEST"

    def test_health_data_fields(self) -> None:
        data = HealthData(
            status="ok",
            version="0.1.0",
            python="3.11.0",
            platform="linux",
            engines=["pandas"],
        )
        d = data.model_dump()
        assert d["version"] == "0.1.0"
        assert d["engines"] == ["pandas"]

    def test_version_data_fields(self) -> None:
        data = VersionData(version="0.1.0", python="3.11.0")
        d = data.model_dump()
        assert d["version"] == "0.1.0"
        assert d["sdk"] == "Phronesis"

    def test_capabilities_data_fields(self) -> None:
        data = CapabilitiesData(
            file_formats=["csv", "xlsx"],
            engines=["pandas"],
            pipeline_stages=["upload", "etl"],
            limits={"max_upload_size_mb": 100},
        )
        d = data.model_dump()
        assert "csv" in d["file_formats"]
        assert d["limits"]["max_upload_size_mb"] == 100

    def test_job_data_fields(self) -> None:
        data = JobData(
            job_id="test-id",
            status="completed",
            created_at="2024-01-01T00:00:00",
        )
        d = data.model_dump()
        assert d["job_id"] == "test-id"
        assert d["status"] == "completed"

    def test_error_detail_fields(self) -> None:
        detail = ErrorDetail(
            code="TEST_ERROR",
            message="Something went wrong",
            details={"field": "name"},
            documentation="https://docs.Phronesis.ai/errors/TEST_ERROR",
        )
        d = detail.model_dump()
        assert d["code"] == "TEST_ERROR"
        assert d["details"]["field"] == "name"

    def test_allowed_extensions_defined(self) -> None:
        assert ".csv" in ALLOWED_EXTENSIONS
        assert ".xlsx" in ALLOWED_EXTENSIONS
        assert ".json" in ALLOWED_EXTENSIONS
        assert ".parquet" in ALLOWED_EXTENSIONS
