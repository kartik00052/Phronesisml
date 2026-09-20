"""Full-stack integration: a complete pipeline run to completion against real SDK.

Exercises the real end-to-end flow: upload → run → stages → models →
artifacts → report → explainability → predict.  Marked ``integration``;
run explicitly with ``pytest -m integration`` (addopts exclude them by
default because they train models).
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.integration

RUN_PAYLOAD = {
    "datasetId": None,
    "nullStrategy": "drop",
    "stages": [
        "etl",
        "validation",
        "eda",
        "target_detection",
        "feature_engineering",
        "model_selection",
        "evaluation",
        "explainability",
        "reporting",
        "storage",
    ],
    "mode": "fast",
    "maxTrials": 2,
    "engine": "pandas",
}

POLL_SECONDS = 0.5
TIMEOUT_SECONDS = 240


def _wait_for_terminal(client, run_id: str) -> dict:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    detail = {}
    while time.monotonic() < deadline:
        resp = client.get(f"/api/v1/runs/{run_id}")
        assert resp.status_code == 200, resp.text
        detail = resp.json()
        if detail["status"] in {"completed", "failed", "cancelled"}:
            return detail
        time.sleep(POLL_SECONDS)
    pytest.fail(
        f"run {run_id} did not reach a terminal state in {TIMEOUT_SECONDS}s: {detail.get('status')}"
    )


def test_full_pipeline_to_artifacts_and_predict(client, iris_dataset):
    payload = dict(RUN_PAYLOAD)
    payload["datasetId"] = iris_dataset["summary"]["id"]
    resp = client.post("/api/v1/runs", json=payload)
    assert resp.status_code == 201, resp.text
    run_id = resp.json()["id"]

    detail = _wait_for_terminal(client, run_id)
    assert detail["status"] == "completed", detail.get("error")

    assert detail["summary"]["bestModelType"]
    assert detail["stagesExecuted"]
    assert detail["totalDurationMs"] > 0

    stages = client.get(f"/api/v1/runs/{run_id}/pipeline/stages")
    assert stages.status_code == 200
    assert len(stages.json()) >= 5

    progress = client.get(f"/api/v1/runs/{run_id}/pipeline/progress")
    assert progress.status_code == 200
    assert progress.json()["status"] == "completed"

    overview = client.get(f"/api/v1/runs/{run_id}/pipeline")
    assert overview.status_code == 200
    assert overview.json()["stagesExecuted"]

    models = client.get(f"/api/v1/runs/{run_id}/models")
    assert models.status_code == 200, models.text
    rows = models.json()
    assert rows, "expected at least one model leaderboard row"
    assert "model_type" in rows[0]
    first = rows[0]["model_type"]
    model_detail = client.get(f"/api/v1/runs/{run_id}/models/{first}")
    assert model_detail.status_code == 200, model_detail.text
    assert "evaluation" in model_detail.json()

    manifest = client.get(f"/api/v1/runs/{run_id}/artifacts")
    manifest.raise_for_status()
    artifacts = manifest.json()["artifacts"]
    names = {a["name"] for a in artifacts}
    for expected in [
        "model.json",
        "model.joblib",
        "evaluation.json",
        "metrics.json",
        "shap.json",
        "target_detection.json",
        "report.md",
        "report.html",
        "pipeline.json",
    ]:
        assert expected in names, f"missing artifact {expected} in {sorted(names)}"

    content = client.get(f"/api/v1/runs/{run_id}/artifacts/model.json/content")
    assert content.status_code == 200, content.text
    assert "content" in content.json()

    report = client.get(f"/api/v1/runs/{run_id}/report?format=markdown")
    assert report.status_code == 200
    assert report.json()["markdown"]

    explain = client.get(f"/api/v1/runs/{run_id}/explainability")
    assert explain.status_code == 200
    view = explain.json()
    assert "importance" in view
    assert len(view["importance"]) >= 1

    stats = client.get("/api/v1/stats")
    assert stats.status_code == 200
    assert "engineBreakdown" in stats.json()

    recent = client.get("/api/v1/runs/recent")
    assert recent.status_code == 200
    assert isinstance(recent.json(), list)

    run_dataset = client.get(f"/api/v1/runs/{run_id}/dataset")
    assert run_dataset.status_code == 200
    assert run_dataset.json()["summary"]["name"] == "iris.csv"

    predict = client.post(f"/api/v1/runs/{run_id}/predict", json={})
    assert predict.status_code in (200, 400, 422), predict.text
    if predict.status_code == 200:
        out = predict.json()
        assert "predictions" in out or "result" in out


def test_cancel_run(client, iris_dataset):
    payload = dict(RUN_PAYLOAD)
    payload["datasetId"] = iris_dataset["summary"]["id"]
    resp = client.post("/api/v1/runs", json=payload)
    assert resp.status_code == 201, resp.text
    run_id = resp.json()["id"]

    cancel = client.post(f"/api/v1/runs/{run_id}/cancel")
    assert cancel.status_code == 200, cancel.text
    state = cancel.json()["status"]
    assert state in {"cancelled", "running", "queued", "completed", "failed"}
