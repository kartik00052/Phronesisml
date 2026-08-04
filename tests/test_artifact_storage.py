"""Tests for the artifact storage helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from phronesisml.services.storage import (
    build_artifact_manifest,
    list_artifacts,
    load_artifact,
    save_artifact,
)


def test_save_artifact_json_roundtrip(tmp_path) -> None:
    info = save_artifact({"a": 1, "b": [2, 3]}, "metrics", tmp_path, fmt="json")
    assert info["name"] == "metrics"
    assert info["fmt"] == "json"
    assert info["bytes"] > 0
    assert load_artifact(info["path"]) == {"a": 1, "b": [2, 3]}


def test_save_artifact_csv(tmp_path) -> None:
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    info = save_artifact(df, "data", tmp_path, fmt="csv")
    loaded = load_artifact(info["path"])
    assert list(loaded.columns) == ["x", "y"]
    assert loaded["x"].tolist() == [1, 2]


def test_save_artifact_text(tmp_path) -> None:
    info = save_artifact("# title", "report", tmp_path, fmt="md")
    assert load_artifact(info["path"]) == "# title"


def test_save_artifact_unknown_format(tmp_path) -> None:
    with pytest.raises(ValueError, match="Unknown artifact format"):
        save_artifact({}, "x", tmp_path, fmt="yaml")


def test_save_artifact_csv_requires_dataframe(tmp_path) -> None:
    with pytest.raises(TypeError, match="DataFrame"):
        save_artifact({"a": 1}, "x", tmp_path, fmt="csv")


def test_load_artifact_missing_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_artifact(tmp_path / "nope.json")


def test_list_artifacts(tmp_path) -> None:
    save_artifact({"a": 1}, "one", tmp_path, fmt="json")
    save_artifact("hi", "two", tmp_path, fmt="txt")
    result = list_artifacts(tmp_path)
    assert result["count"] == 2
    names = {a["name"] for a in result["artifacts"]}
    assert names == {"one.json", "two.txt"}


def test_list_artifacts_missing_dir(tmp_path) -> None:
    result = list_artifacts(tmp_path / "missing")
    assert result["count"] == 0


def test_build_artifact_manifest(tmp_path) -> None:
    save_artifact({"a": 1}, "one", tmp_path, fmt="json")
    listing = list_artifacts(tmp_path)
    manifest = build_artifact_manifest(listing, run_id="run-1")
    assert manifest["run_id"] == "run-1"
    assert manifest["artifact_count"] == 1
    assert manifest["total_bytes"] > 0
    assert manifest["files"][0]["name"] == "one.json"


def test_build_artifact_manifest_from_paths(tmp_path) -> None:
    p = tmp_path / "plain.txt"
    p.write_text("x", encoding="utf-8")
    manifest = build_artifact_manifest([str(p)])
    assert manifest["artifact_count"] == 1
    assert manifest["total_bytes"] == 1
