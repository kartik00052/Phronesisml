"""Dataset endpoints — upload, list, get, preview, schema, eda, delete."""

from __future__ import annotations

from backend.app.config import ROOT_DIR


def test_upload_and_list(client):
    path = ROOT_DIR / "data" / "iris.csv"
    with path.open("rb") as fh:
        resp = client.post(
            "/api/v1/datasets",
            files={"file": ("iris.csv", fh, "text/csv")},
        )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert "dataset" in body
    ds = body["dataset"]
    assert ds["summary"]["name"] == "iris.csv"
    assert ds["summary"]["rows"] == 150
    assert ds["summary"]["columns"] == 6
    dsid = ds["summary"]["id"]

    listed = client.get("/api/v1/datasets")
    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()["items"]]
    assert dsid in ids

    return dsid


def test_get_preview_schema_eda(client, iris_dataset):
    dsid = iris_dataset["summary"]["id"]

    detail = client.get(f"/api/v1/datasets/{dsid}")
    assert detail.status_code == 200
    assert detail.json()["summary"]["id"] == dsid
    assert "profile" in detail.json()
    assert "columns" in detail.json()
    assert "validation" in detail.json()

    preview = client.get(f"/api/v1/datasets/{dsid}/preview?pageSize=5")
    assert preview.status_code == 200
    body = preview.json()
    assert "rows" in body and "columns" in body
    assert len(body["rows"]) == 5

    schema = client.get(f"/api/v1/datasets/{dsid}/schema")
    assert schema.status_code == 200
    columns = schema.json()["columns"]
    assert columns and columns[0]["name"] == "Id"
    assert {c["name"] for c in columns} >= {"SepalLengthCm", "class"}

    eda = client.get(f"/api/v1/datasets/{dsid}/eda")
    assert eda.status_code == 200
    assert "numeric_columns" in eda.json()


def test_delete_dataset(client, iris_dataset):
    dsid = iris_dataset["summary"]["id"]
    resp = client.delete(f"/api/v1/datasets/{dsid}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    gone = client.get(f"/api/v1/datasets/{dsid}")
    assert gone.status_code == 404
    assert gone.json()["error"]["code"] == "NotFound"


def test_upload_garbage_content_rejected(client):
    resp = client.post("/api/v1/datasets", files={"file": ("big.csv", b"x" * 100, "text/csv")})
    assert resp.status_code in (413, 415, 422), resp.text
    assert "error" in resp.json()
