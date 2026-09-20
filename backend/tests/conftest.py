"""Pytest fixtures — isolated temp DB + storage for every test session.

Environment must be configured *before* any backend import so the frozen
Settings cache picks up the temp locations.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="phronesisml-test-"))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_ROOT / 'test.db'}")
os.environ.setdefault("DATA_STORAGE_DIR", str(TEST_ROOT / "datasets"))
os.environ.setdefault("RUN_STORAGE_DIR", str(TEST_ROOT / "runs"))
os.environ.setdefault("ARTIFACT_STORAGE_DIR", str(TEST_ROOT / "artifacts"))
os.environ.setdefault("REPORT_STORAGE_DIR", str(TEST_ROOT / "reports"))
os.environ.setdefault("REQUEST_LOG", "0")
os.environ.setdefault("SEED_SAMPLE_DATASETS", "0")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    """TestClient with the app lifespan (init_db + event hub) running."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def iris_csv() -> str:
    """Absolute path to the bundled IRIS fixture dataset."""
    from backend.app.config import ROOT_DIR

    return str(ROOT_DIR / "data" / "iris.csv")


@pytest.fixture(scope="function")
def iris_dataset(client: TestClient) -> dict:
    """Fresh uploaded IRIS dataset response for each test (isolated deletes)."""
    from backend.app.config import ROOT_DIR

    path = ROOT_DIR / "data" / "iris.csv"
    with path.open("rb") as fh:
        resp = client.post(
            "/api/v1/datasets",
            files={"file": ("iris.csv", fh, "text/csv")},
        )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["dataset"]
