"""One-shot E2E integration check against the real backend + SDK pipeline."""

import json
import sys
import time

from fastapi.testclient import TestClient

import backend.app.main as m

P = "/api/v1"


def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), name, extra)
    return cond


ok = True

with TestClient(m.app) as client:
    # 1. health
    r = client.get(f"{P}/health")
    ok &= check(
        "health", r.status_code == 200 and "missing_core" in r.json() and "dependencies" in r.json()
    )

    # 2. capabilities
    r = client.get(f"{P}/capabilities")
    ok &= check(
        "capabilities",
        r.status_code == 200 and "task_types" in r.json() and "pipeline_stages" in r.json(),
    )

    # 3. engine recommend
    r = client.post(f"{P}/engine/recommend", json={"bytes": 5000, "rows": 100, "cols": 5})
    ok &= check(
        "engine/recommend",
        r.status_code == 200 and r.json().get("engine") == "pandas",
        str(r.json()),
    )

    # 4. upload
    with open("data/iris.csv", "rb") as fh:
        r = client.post(f"{P}/datasets", files={"file": ("iris.csv", fh, "text/csv")})
        print("upload resp", r.status_code, str(r.json())[:120])
        body = r.json()
        ok &= check(
            "upload",
            r.status_code in (200, 201)
            and "dataset" in body
            and body["dataset"]["summary"]["name"] == "iris.csv",
            list(body.keys()),
        )
    if not ok:
        sys.exit(1)
    dsid = body["dataset"]["summary"]["id"]

    # 5. list + get
    r = client.get(f"{P}/datasets")
    ok &= check("list datasets", r.status_code == 200 and len(r.json()["items"]) > 0)
    r = client.get(f"{P}/datasets/{dsid}")
    ok &= check(
        "get dataset",
        r.status_code == 200 and bool(r.json()["profile"].get("shape", {}).get("rows")),
    )

    # 6. preview / schema / eda
    r = client.get(f"{P}/datasets/{dsid}/preview")
    ok &= check("preview", r.status_code == 200 and "rows" in r.json())
    r = client.get(f"{P}/datasets/{dsid}/schema")
    ok &= check("schema", r.status_code == 200 and "columns" in r.json())
    r = client.get(f"{P}/datasets/{dsid}/eda")
    ok &= check("eda", r.status_code == 200 and "numeric_columns" in r.json())

    # 7. run
    r = client.post(
        f"{P}/runs",
        json={
            "datasetId": dsid,
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
            "maxTrials": 3,
            "maxTimeSeconds": 60,
        },
    )
    ok &= check("create run", r.status_code == 201, str(r.status_code))
    run = r.json()
    runid = run["id"]

    for _ in range(400):
        r = client.get(f"{P}/runs/{runid}")
        st = r.json()["status"]
        if st in ("completed", "failed"):
            break
        time.sleep(1)
    print("run final", st)
    if st != "completed":
        print(json.dumps(r.json(), indent=2)[:3000])
        sys.exit(1)
    ok &= check("run completed", st == "completed")

    # 8. run DTO shape
    run_dict = r.json()
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
        ok &= check(f"run.{key}", key in run_dict)

    # 9. pipeline
    r = client.get(f"{P}/runs/{runid}/pipeline")
    ok &= check(
        "pipeline overview",
        r.status_code == 200 and bool(r.json().get("stagesRequested")),
        r.json().get("mode", ""),
    )
    r = client.get(f"{P}/runs/{runid}/pipeline/stages")
    ok &= check(
        "pipeline stages",
        r.status_code == 200 and len(r.json()) >= 3 and "id" in r.json()[0],
        f"{len(r.json())} stages",
    )
    r = client.get(f"{P}/runs/{runid}/pipeline/progress")
    ok &= check("pipeline progress", r.status_code == 200 and "completedStages" in r.json())

    # 10. models
    r = client.get(f"{P}/runs/{runid}/models")
    ok &= check("models list", r.status_code == 200, str(r.json())[:200])
    if r.status_code == 200 and r.json():
        first = r.json()[0]
        ok &= check(
            "model row shape", "model_type" in first and "primary_score" in first, str(list(first))
        )
        r2 = client.get(f"{P}/runs/{runid}/models/{first['model_type']}")
        ok &= check(
            "model detail", r2.status_code == 200 and "evaluation" in r2.json(), str(r2.status_code)
        )

    # 11. artifacts
    r = client.get(f"{P}/runs/{runid}/artifacts")
    ok &= check(
        "artifacts manifest",
        r.status_code == 200 and "artifacts" in r.json(),
        f"{len(r.json().get('artifacts', []))} artifacts",
    )
    art = r.json().get("artifacts", [])
    if art:
        a = art[0]
        r2 = client.get(f"{P}/runs/{runid}/artifacts/{a['name']}/content")
        ok &= check(
            "artifact content",
            r2.status_code == 200 and "content" in r2.json(),
            str(r2.status_code),
        )

    # 12. report
    r = client.get(f"{P}/runs/{runid}/report?format=markdown")
    ok &= check(
        "report md", r.status_code == 200 and bool(r.json().get("markdown")), str(r.status_code)
    )
    r = client.get(f"{P}/runs/{runid}/report?format=html")
    ok &= check(
        "report html", r.status_code == 200 and bool(r.json().get("html")), str(r.status_code)
    )
    r = client.get(f"{P}/runs/{runid}/report?format=json")
    ok &= check(
        "report json", r.status_code == 200 and bool(r.json().get("json")), str(r.status_code)
    )

    # 13. explainability
    r = client.get(f"{P}/runs/{runid}/explainability")
    ok &= check("explainability", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        ok &= check("explain view", "report" in r.json() and "importance" in r.json())

    # 14. logs
    r = client.get(f"{P}/runs/{runid}/logs")
    ok &= check("logs string[]", r.status_code == 200 and isinstance(r.json(), list))

    # 15. stats + recent + run dataset
    r = client.get(f"{P}/stats")
    ok &= check(
        "stats",
        r.status_code == 200
        and "engineBreakdown" in r.json()
        and isinstance(r.json()["engineBreakdown"], dict),
    )
    r = client.get(f"{P}/runs/recent")
    ok &= check("recent", r.status_code == 200 and isinstance(r.json(), list))
    r = client.get(f"{P}/runs/{runid}/dataset")
    ok &= check("run dataset", r.status_code == 200 and "profile" in r.json(), str(r.status_code))

    # 16. deliverable artifacts (§44)
    required = [
        "model.json",
        "model.joblib",
        "evaluation.json",
        "metrics.json",
        "training.json",
        "shap.json",
        "feature_metadata.json",
        "target_detection.json",
        "eda.json",
        "validation.json",
        "resource_estimation.json",
        "engine_selection.json",
        "pipeline.json",
        "run_metadata.json",
        "report.md",
        "report.html",
        "config.json",
        "logs.txt",
    ]
    found = {
        a["name"] for a in client.get(f"{P}/runs/{runid}/artifacts").json().get("artifacts", [])
    }
    missing = [x for x in required if x not in found]
    ok &= check("written artifacts on disk", not missing, f"missing={missing}")

print("\n=== RESULT:", "ALL PASS" if ok else "SOME FAILURES", "===")
sys.exit(0 if ok else 1)
