"""Tests for JSON + run-scoped report variants."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from phronesisml.ml.reports import build_json_report, build_run_report


@dataclass
class _StubState:
    run_id: str = "run-abc"
    status: str = "completed"
    timestamp: str = "2026-08-04T10:00:00Z"
    version: str = "0.2.2"
    data_path: str = "data.csv"
    n_rows: int = 500
    n_columns: int = 6
    feature_names: list = field(default_factory=lambda: ["a", "b", "c"])
    target_column: str = "y"
    task_type: str = "classification"
    target_detection_confidence: float = 0.9
    ambiguity_reason: None = None
    engine: str = "pandas"
    best_pipeline: dict = field(
        default_factory=lambda: {
            "model_type": "random_forest",
            "candidates_tried": ["logistic_regression", "random_forest"],
            "rejected_models": ["logistic_regression"],
            "rejection_reasons": "lower cv score",
            "rationale": "best cross-validated score",
            "best_params": {"n_estimators": 100},
        }
    )
    evaluation_report: dict = field(default_factory=lambda: {"f1_macro": 0.9})
    explanation_report: dict = field(
        default_factory=lambda: {
            "explainer": "tree",
            "feature_importance": {"a": 0.6, "b": 0.4},
        }
    )
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def test_build_json_report_is_jsonable() -> None:
    report = build_json_report(_StubState(), narrative="ok")
    text = json.dumps(report)  # must not raise
    assert "run-abc" in text
    assert report["target"]["task_type"] == "classification"
    assert report["model"]["model_type"] == "random_forest"
    assert report["explanation"]["explainer"] == "tree"


def test_build_json_report_dict_state() -> None:
    report = build_json_report(
        {"run_id": "r1", "target_column": "price", "task_type": "regression"}
    )
    assert report["run"]["run_id"] == "r1"
    assert report["target"]["target_column"] == "price"


def test_build_run_report_writes_file(tmp_path) -> None:
    info = build_run_report(
        _StubState(),
        tmp_path,
        runtime_seconds=12.34,
        artifacts=[str(tmp_path / "model.pkl")],
    )
    assert info["run_id"] == "run-abc"
    assert info["bytes"] > 0

    text = (tmp_path / "run-abc.md").read_text(encoding="utf-8")
    assert "# Run Report" in text
    assert "run-abc" in text
    assert "classification" in text
    assert "random_forest" in text
    assert "tree" in text
    assert "12.34" in text
    assert "model.pkl" in text


def test_build_run_report_default_run_id(tmp_path) -> None:
    info = build_run_report({}, tmp_path)
    assert info["run_id"] == "default_run"
    assert (tmp_path / "default_run.md").is_file()


def test_build_run_report_regression_recommendations(tmp_path) -> None:
    state = _StubState()
    state.task_type = "regression"
    state.best_pipeline = {"model_type": "linear_regression", "best_params": {}}
    build_run_report(state, tmp_path)
    text = (tmp_path / "run-abc.md").read_text(encoding="utf-8")
    assert "residual" in text
