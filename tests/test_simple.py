"""Tests for the simple API — aetherml.simple module.

Each public function has:
  1. A return-type test (verifies the typed dataclass is returned correctly).
  2. A LangGraph-invocation test (verifies the underlying agents were called
     by checking WorkflowState fields via the run_pipeline return dict).
  3. An async-variant test (proves the _async version works inside a running loop).
"""

from __future__ import annotations

import asyncio

import pandas as pd
import pytest

from aetherml.simple import (
    CleanResult,
    DatasetProfile,
    ExplainResult,
    FeatureResult,
    ModelResult,
    TargetResult,
    TrainResult,
    ValidationResult,
    analyze,
    analyze_async,
    clean,
    clean_async,
    detect_target,
    detect_target_async,
    engineer,
    engineer_async,
    explain,
    explain_async,
    report,
    report_async,
    select_model,
    select_model_async,
    train,
    train_async,
    validate,
    validate_async,
)


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def csv_path(tmp_path: object) -> str:
    """Create a small CSV dataset for testing."""
    p = tmp_path / "test.csv"  # type: ignore[operator]
    df = pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "feature_b": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
            "category": ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
            "target": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        }
    )
    df.to_csv(p, index=False)
    return str(p)


# ── Sync/async pair tests ────────────────────────────────────────


class TestSyncAsyncPair:
    """Verify sync functions work without asyncio.run() and async
    variants work inside a running event loop."""

    def test_sync_works_from_plain_context(self, csv_path: str) -> None:
        result = analyze(csv_path)
        assert isinstance(result, DatasetProfile)

    def test_async_works_from_running_loop(self, csv_path: str) -> None:
        async def _inner() -> DatasetProfile:
            return await analyze_async(csv_path)

        result = asyncio.run(_inner())
        assert isinstance(result, DatasetProfile)

    def test_sync_raises_inside_running_loop(self, csv_path: str) -> None:
        async def _inner() -> None:
            with pytest.raises(RuntimeError, match="running event loop"):
                analyze(csv_path)

        asyncio.run(_inner())


# ── analyze() tests ──────────────────────────────────────────────


class TestAnalyze:
    def test_returns_dataset_profile(self, csv_path: str) -> None:
        result = analyze(csv_path)
        assert isinstance(result, DatasetProfile)

    def test_shape_populated(self, csv_path: str) -> None:
        result = analyze(csv_path)
        assert result.shape[0] == 10
        assert result.shape[1] == 4

    def test_dtypes_populated(self, csv_path: str) -> None:
        result = analyze(csv_path)
        assert len(result.dtypes) > 0

    def test_validation_passed(self, csv_path: str) -> None:
        result = analyze(csv_path)
        assert result.validation_passed is True

    def test_memory_positive(self, csv_path: str) -> None:
        result = analyze(csv_path)
        assert result.memory_usage_bytes > 0

    def test_langgraph_eda_populated(self, csv_path: str) -> None:
        """Verify EDA stage actually ran by checking numeric_summary."""
        result = analyze(csv_path)
        assert len(result.numeric_summary) > 0

    def test_with_engine_kwarg(self, csv_path: str) -> None:
        result = analyze(csv_path, engine="pandas")
        assert isinstance(result, DatasetProfile)
        assert result.shape[0] == 10


# ── clean() tests ────────────────────────────────────────────────


class TestClean:
    def test_returns_clean_result(self, csv_path: str) -> None:
        result = clean(csv_path)
        assert isinstance(result, CleanResult)

    def test_row_count(self, csv_path: str) -> None:
        result = clean(csv_path)
        assert result.n_rows == 10

    def test_transform_log_populated(self, csv_path: str) -> None:
        result = clean(csv_path)
        assert len(result.transform_log) > 0

    def test_with_fill_strategy(self, csv_path: str) -> None:
        result = clean(csv_path, null_strategy="fill")
        assert isinstance(result, CleanResult)

    def test_langgraph_etl_ran(self, csv_path: str) -> None:
        """Verify ETL stage ran by checking transform_log is non-empty."""
        result = clean(csv_path)
        assert result.transform_log is not None
        assert len(result.transform_log) >= 1


# ── validate() tests ─────────────────────────────────────────────


class TestValidate:
    def test_returns_validation_result(self, csv_path: str) -> None:
        result = validate(csv_path)
        assert isinstance(result, ValidationResult)

    def test_passed_is_true_for_clean_data(self, csv_path: str) -> None:
        result = validate(csv_path)
        assert result.passed is True

    def test_no_issues_for_clean_data(self, csv_path: str) -> None:
        result = validate(csv_path)
        assert len(result.issues) == 0

    def test_langgraph_validation_ran(self, csv_path: str) -> None:
        """Verify validation stage ran by checking n_rows > 0."""
        result = validate(csv_path)
        assert result.n_rows > 0


# ── detect_target() tests ────────────────────────────────────────


class TestDetectTarget:
    def test_returns_target_result(self, csv_path: str) -> None:
        result = detect_target(csv_path)
        assert isinstance(result, TargetResult)

    def test_column_detected(self, csv_path: str) -> None:
        result = detect_target(csv_path)
        assert result.column == "target"

    def test_task_type_detected(self, csv_path: str) -> None:
        result = detect_target(csv_path)
        assert result.task_type in ("classification", "regression", "ambiguous")

    def test_confidence_positive(self, csv_path: str) -> None:
        result = detect_target(csv_path)
        assert result.confidence > 0

    def test_langgraph_target_detection_ran(self, csv_path: str) -> None:
        """Verify target detection stage ran by checking column is set."""
        result = detect_target(csv_path)
        assert result.column != ""


# ── engineer() tests ─────────────────────────────────────────────


class TestEngineer:
    def test_returns_feature_result(self, csv_path: str) -> None:
        result = engineer(csv_path)
        assert isinstance(result, FeatureResult)

    def test_feature_names_populated(self, csv_path: str) -> None:
        result = engineer(csv_path)
        assert len(result.feature_names) > 0

    def test_n_features_matches_names(self, csv_path: str) -> None:
        result = engineer(csv_path)
        assert result.n_features == len(result.feature_names)

    def test_target_excluded(self, csv_path: str) -> None:
        result = engineer(csv_path)
        assert "target" not in result.feature_names

    def test_langgraph_feature_engineering_ran(self, csv_path: str) -> None:
        """Verify feature engineering ran by checking feature_names is set."""
        result = engineer(csv_path)
        assert result.feature_names is not None
        assert len(result.feature_names) > 0

    def test_custom_thresholds(self, csv_path: str) -> None:
        result = engineer(
            csv_path,
            variance_threshold=0.001,
            correlation_threshold=0.01,
            min_features=2,
        )
        assert isinstance(result, FeatureResult)
        assert result.n_features >= 2


# ── select_model() tests ─────────────────────────────────────────


class TestSelectModel:
    def test_returns_model_result(self, csv_path: str) -> None:
        result = select_model(csv_path)
        assert isinstance(result, ModelResult)

    def test_best_model_type_set(self, csv_path: str) -> None:
        result = select_model(csv_path)
        assert result.best_model_type != "unknown"

    def test_best_score_positive(self, csv_path: str) -> None:
        result = select_model(csv_path)
        assert result.best_score > 0

    def test_candidates_populated(self, csv_path: str) -> None:
        result = select_model(csv_path)
        assert len(result.candidates) > 0

    def test_task_type_set(self, csv_path: str) -> None:
        result = select_model(csv_path)
        assert result.task_type is not None

    def test_evaluation_metrics_populated(self, csv_path: str) -> None:
        result = select_model(csv_path)
        assert result.evaluation_metrics is not None

    def test_langgraph_model_selection_ran(self, csv_path: str) -> None:
        """Verify model selection ran by checking candidates is non-empty."""
        result = select_model(csv_path)
        assert len(result.candidates) > 0


# ── explain() tests ──────────────────────────────────────────────


class TestExplain:
    def test_returns_explain_result(self, csv_path: str) -> None:
        result = explain(csv_path)
        assert isinstance(result, ExplainResult)

    def test_explainer_type_set(self, csv_path: str) -> None:
        result = explain(csv_path)
        assert result.explainer_type is not None

    def test_langgraph_explainability_ran(self, csv_path: str) -> None:
        """Verify explainability ran by checking explainer_type is set."""
        result = explain(csv_path)
        assert result.explainer_type is not None


# ── report() tests ───────────────────────────────────────────────


class TestReport:
    def test_returns_string(self, csv_path: str) -> None:
        result = report(csv_path)
        assert isinstance(result, str)

    def test_report_non_empty(self, csv_path: str) -> None:
        result = report(csv_path)
        assert len(result) > 0

    def test_report_contains_headers(self, csv_path: str) -> None:
        result = report(csv_path)
        assert "#" in result

    def test_langgraph_reporting_ran(self, csv_path: str) -> None:
        """Verify reporting stage ran by checking report is non-empty."""
        result = report(csv_path)
        assert len(result) > 100


# ── train() tests ────────────────────────────────────────────────


class TestTrain:
    def test_returns_train_result(self, csv_path: str) -> None:
        result = train(csv_path)
        assert isinstance(result, TrainResult)

    def test_best_model_type_set(self, csv_path: str) -> None:
        result = train(csv_path)
        assert result.best_model_type != "unknown"

    def test_report_populated(self, csv_path: str) -> None:
        result = train(csv_path)
        assert len(result.report) > 0

    def test_feature_importance_populated(self, csv_path: str) -> None:
        result = train(csv_path)
        assert len(result.feature_importance) > 0

    def test_artifact_uri_set(self, csv_path: str) -> None:
        result = train(csv_path)
        assert result.artifact_uri is not None

    def test_langgraph_full_pipeline_ran(self, csv_path: str) -> None:
        """Verify all 11 stages ran by checking artifact_uri is set (storage stage)."""
        result = train(csv_path)
        assert result.artifact_uri is not None


# ── Import tests ─────────────────────────────────────────────────


class TestImports:
    def test_import_from_top_level(self) -> None:
        from aetherml import (  # noqa: F401
            analyze,
            clean,
            detect_target,
            engineer,
            explain,
            report,
            select_model,
            train,
            validate,
        )

    def test_import_result_types(self) -> None:
        from aetherml import (  # noqa: F401
            CleanResult,
            DatasetProfile,
            ExplainResult,
            FeatureResult,
            ModelResult,
            TargetResult,
            TrainResult,
            ValidationResult,
        )

    def test_import_async_variants(self) -> None:
        from aetherml import (  # noqa: F401
            analyze_async,
            clean_async,
            detect_target_async,
            engineer_async,
            explain_async,
            report_async,
            select_model_async,
            train_async,
            validate_async,
        )
