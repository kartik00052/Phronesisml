"""Tests for evaluation reporting helpers."""

from __future__ import annotations

from phronesisml.ml.evaluation import compare_models, metric_summary


def test_metric_summary_classification() -> None:
    metrics = {"accuracy": 0.9, "f1_weighted": 0.88, "precision": 0.85, "recall": 0.8}
    summary = metric_summary(metrics, task_type="classification")
    assert summary["primary_metric"] == "f1_weighted"
    assert summary["primary_value"] == 0.88
    assert summary["primary_higher_is_better"] is True
    assert len(summary["all_metrics"]) == 4


def test_metric_summary_regression() -> None:
    metrics = {"r2": 0.7, "rmse": 2.5, "mae": 1.2}
    summary = metric_summary(metrics, task_type="regression")
    assert summary["primary_metric"] == "r2"
    assert summary["primary_value"] == 0.7


def test_metric_summary_primary_not_present() -> None:
    metrics = {"recall": 0.5, "precision": 0.6}
    summary = metric_summary(metrics, task_type="classification")
    assert summary["primary_metric"] == "recall"
    assert summary["primary_value"] == 0.5


def test_metric_summary_empty() -> None:
    summary = metric_summary({}, task_type="classification")
    assert summary["primary_metric"] is None
    assert summary["all_metrics"] == []


def test_metric_summary_handles_none() -> None:
    metrics = {"accuracy": None, "f1_weighted": 0.5}
    summary = metric_summary(metrics, task_type="classification")
    assert summary["primary_metric"] == "f1_weighted"


def test_compare_models() -> None:
    evaluations = [
        {
            "model": "model_a",
            "model_info": {"name": "model_a"},
            "metrics": {"accuracy": 0.8, "f1_weighted": 0.75},
        },
        {
            "model": "model_b",
            "model_info": {"name": "model_b"},
            "metrics": {"accuracy": 0.9, "f1_weighted": 0.88},
        },
    ]
    report = compare_models(evaluations, task_type="classification")
    assert report["primary_metric"] == "f1_weighted"
    assert report["ranking"][0]["model"] == "model_b"
    assert report["ranking"][1]["model"] == "model_a"


def test_compare_models_handles_missing_metric() -> None:
    evaluations = [
        {"model_info": {"name": "a"}, "metrics": {"accuracy": 0.8}},
        {"model_info": {"name": "b"}, "metrics": {}},
    ]
    report = compare_models(evaluations, task_type="classification")
    assert report["ranking"][0]["model"] == "a"
    assert report["ranking"][1]["value"] is None


def test_compare_models_regression_lower_is_better() -> None:
    evaluations = [
        {"model_info": {"name": "a"}, "metrics": {"r2": 0.7, "rmse": 5.0}},
        {"model_info": {"name": "b"}, "metrics": {"r2": 0.7, "rmse": 1.0}},
    ]
    report = compare_models(evaluations, task_type="regression")
    assert report["primary_metric"] == "r2"
    assert report["higher_is_better"] is True
