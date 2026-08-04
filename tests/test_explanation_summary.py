"""Tests for explanation summarizers."""

from __future__ import annotations

from phronesisml.ml.explainability import (
    explanation_summary,
    validate_explanation,
)


def test_validate_explanation_ok_service_shape() -> None:
    explanation = {
        "feature_importance": {"a": 0.5, "b": 0.3},
        "explainer_type": "TreeExplainer",
        "sampled": False,
        "n_samples_used": 100,
        "n_features_used": 2,
        "max_samples": 100,
    }
    result = validate_explanation(explanation)
    assert result["valid"] is True
    assert result["issues"] == []


def test_validate_explanation_ok_legacy_shape() -> None:
    explanation = {
        "feature_importance": {"a": 0.5, "b": 0.3},
        "feature_names": ["a", "b"],
        "explainer": "tree",
        "status": "ok",
    }
    result = validate_explanation(explanation)
    assert result["valid"] is True
    assert result["issues"] == []


def test_validate_explanation_none() -> None:
    result = validate_explanation(None)
    assert result["valid"] is False
    assert any("None" in i for i in result["issues"])


def test_validate_explanation_missing_importance() -> None:
    result = validate_explanation({})
    assert result["valid"] is False
    assert any("feature_importance" in i for i in result["issues"])


def test_validate_explanation_bad_status() -> None:
    explanation = {
        "feature_importance": {"a": 1.0},
        "feature_names": ["a"],
        "explainer": "tree",
        "status": "error",
    }
    result = validate_explanation(explanation)
    assert result["valid"] is False
    assert any("status" in i for i in result["issues"])


def test_explanation_summary_top_features() -> None:
    explanation = {
        "feature_importance": {"c": 0.1, "a": 0.9, "b": 0.5},
        "explainer_type": "TreeExplainer",
    }
    summary = explanation_summary(explanation, top_n=2)
    assert summary["valid"] is True
    assert summary["n_features"] == 3
    assert [f["feature"] for f in summary["top_features"]] == ["a", "b"]
    assert summary["top_features"][0]["importance"] == 0.9
    assert summary["explainer"] == "TreeExplainer"


def test_explanation_summary_skips_non_numeric() -> None:
    explanation = {
        "feature_importance": {"a": "not-a-number", "b": 0.5},
        "feature_names": ["a", "b"],
        "explainer": "tree",
        "status": "ok",
    }
    summary = explanation_summary(explanation)
    assert summary["n_features_with_importance"] == 1
    assert [f["feature"] for f in summary["top_features"]] == ["b"]
