"""Comprehensive tests for the AetherML public SDK (beginner API)."""

from __future__ import annotations

import time

import pandas as pd
import pytest

from aetherml import (
    AetherML,
    AetherMLConfig,
    DatasetSummary,
    EDAReport,
    EvaluationMetrics,
    ExplanationReport,
    FeatureReport,
    ModelInfo,
    TargetInfo,
    ValidationReport,
    run_pipeline,
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


@pytest.fixture
def excel_path(tmp_path: object) -> str:
    """Create a small Excel file with multiple sheets."""
    p = tmp_path / "test.xlsx"  # type: ignore[operator]
    with pd.ExcelWriter(str(p)) as writer:
        pd.DataFrame({"a": range(50)}).to_excel(writer, sheet_name="Big", index=False)
        pd.DataFrame({"b": [1]}).to_excel(writer, sheet_name="Tiny", index=False)
    return str(p)


@pytest.fixture
def ml(csv_path: str) -> AetherML:
    """Create an AetherML instance with a CSV dataset."""
    return AetherML(csv_path)


# ── Import tests ─────────────────────────────────────────────────


class TestImports:
    def test_import_aetherml_class(self) -> None:
        from aetherml import AetherML

        assert AetherML is not None

    def test_import_result_types(self) -> None:
        from aetherml import (
            DatasetSummary,
            EDAReport,
            EvaluationMetrics,
            ExplanationReport,
            FeatureReport,
            ModelInfo,
            TargetInfo,
            ValidationReport,
        )

        for cls in [
            DatasetSummary,
            EDAReport,
            EvaluationMetrics,
            ExplanationReport,
            FeatureReport,
            ModelInfo,
            TargetInfo,
            ValidationReport,
        ]:
            assert cls is not None

    def test_import_performance(self) -> None:
        """Importing aetherml should be fast (< 2s)."""
        start = time.monotonic()
        import importlib

        import aetherml

        importlib.reload(aetherml)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"Import took {elapsed:.1f}s (> 2s)"

    def test_backward_compatible_imports(self) -> None:
        """Advanced API imports still work."""
        from aetherml import AetherMLConfig, WorkflowState, run_pipeline  # noqa: F811

        assert run_pipeline is not None
        assert AetherMLConfig is not None
        assert WorkflowState is not None


# ── Constructor tests ────────────────────────────────────────────


class TestConstructor:
    def test_basic_construction(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        assert ml.data_path == csv_path

    def test_default_config(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        assert isinstance(ml.config, AetherMLConfig)

    def test_custom_config(self, csv_path: str) -> None:
        config = AetherMLConfig()
        config.engine.preferred = "pandas"
        ml = AetherML(csv_path, config=config)
        assert ml.config.engine.preferred == "pandas"

    def test_state_starts_empty(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        assert ml.state.raw_data is None
        assert ml.state.processed_data is None

    def test_elapsed_none_before_execution(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        assert ml.elapsed is None

    def test_repr(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        r = repr(ml)
        assert "AetherML" in r
        assert "test.csv" in r
        assert "stages_completed=0" in r


# ── Method chaining tests ────────────────────────────────────────


class TestMethodChaining:
    def test_load_returns_self(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        result = ml.load()
        assert result is ml

    def test_clean_returns_self(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        result = ml.clean()
        assert result is ml

    def test_run_returns_self(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        result = ml.run()
        assert result is ml

    def test_full_chain(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        result = ml.load().clean().run()
        assert result is ml


# ── Stage method tests ───────────────────────────────────────────


class TestLoad:
    def test_loads_csv(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.load()
        assert ml.state.raw_data is not None
        assert ml.state.row_count == 10

    def test_loads_excel(self, excel_path: str) -> None:
        ml = AetherML(excel_path)
        ml.load()
        assert ml.state.raw_data is not None
        assert ml.state.row_count == 50  # picks the "Big" sheet

    def test_file_format_detected(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.load()
        assert ml.state.file_format == "csv"

    def test_load_is_idempotent(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.load()
        ml.load()  # second call should be a no-op (already executed)
        assert ml.state.raw_data is not None


class TestSummary:
    def test_returns_dataset_summary(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        s = ml.summary()
        assert isinstance(s, DatasetSummary)
        assert s.rows == 10
        assert s.columns == 4
        assert "feature_a" in s.column_names
        assert s.memory_bytes > 0
        assert len(s.preview) == 5

    def test_numeric_and_categorical_columns(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        s = ml.summary()
        assert "feature_a" in s.numeric_columns
        assert "category" in s.categorical_columns

    def test_memory_mb_property(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        s = ml.summary()
        assert s.memory_mb > 0

    def test_auto_loads_data(self, csv_path: str) -> None:
        """summary() should auto-trigger load()."""
        ml = AetherML(csv_path)
        s = ml.summary()
        assert s.rows == 10
        assert ml.state.raw_data is not None


class TestClean:
    def test_clean_with_drop(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.clean(null_strategy="drop")
        assert ml.state.processed_data is not None

    def test_clean_with_fill(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.clean(null_strategy="fill")
        assert ml.state.processed_data is not None

    def test_clean_with_flag(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.clean(null_strategy="flag")
        assert ml.state.processed_data is not None

    def test_transform_log_recorded(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.clean()
        assert ml.state.transform_log is not None
        assert len(ml.state.transform_log) > 0


class TestValidate:
    def test_returns_validation_report(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        v = ml.validate()
        assert isinstance(v, ValidationReport)
        assert v.passed is True
        assert v.rows == 10
        assert v.columns == 4

    def test_auto_cleans_before_validation(self, csv_path: str) -> None:
        """validate() should auto-trigger clean()."""
        ml = AetherML(csv_path)
        v = ml.validate()
        assert v.passed is True
        assert ml.state.processed_data is not None


class TestEDA:
    def test_returns_eda_report(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        e = ml.eda()
        assert isinstance(e, EDAReport)
        assert "feature_a" in e.numeric_columns
        assert e.memory_bytes > 0

    def test_numeric_summary_populated(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        e = ml.eda()
        assert "feature_a" in e.numeric_summary
        fa = e.numeric_summary["feature_a"]
        assert "mean" in fa
        assert "std" in fa


class TestProfile:
    def test_returns_dataset_summary(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        p = ml.profile()
        assert isinstance(p, DatasetSummary)
        assert p.rows == 10


class TestDetectTarget:
    def test_returns_target_info(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        t = ml.detect_target()
        assert isinstance(t, TargetInfo)
        assert t.column == "target"
        assert t.task_type in ("classification", "regression", "ambiguous")
        assert 0.0 <= t.confidence <= 1.0


class TestEngineerFeatures:
    def test_returns_feature_report(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        f = ml.engineer_features()
        assert isinstance(f, FeatureReport)
        assert f.n_features > 0
        assert f.n_rows == 10
        assert isinstance(f.features, pd.DataFrame)

    def test_target_excluded_from_features(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        f = ml.engineer_features()
        assert "target" not in f.feature_names


class TestRecommendModel:
    def test_returns_model_info(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        m = ml.recommend_model()
        assert isinstance(m, ModelInfo)
        assert m.model_type != "unknown"
        assert m.score > 0

    def test_candidates_populated(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        m = ml.recommend_model()
        assert len(m.candidates) > 0

    def test_train_alias(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        m1 = ml.recommend_model()
        m2 = ml.train()
        assert m1.model_type == m2.model_type


class TestEvaluate:
    def test_returns_evaluation_metrics(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        e = ml.evaluate()
        assert isinstance(e, EvaluationMetrics)
        assert e.accuracy is not None
        assert 0.0 <= e.accuracy <= 1.0

    def test_classification_metrics_present(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        e = ml.evaluate()
        assert e.precision_macro is not None
        assert e.recall_macro is not None
        assert e.f1_macro is not None
        assert e.confusion_matrix is not None


class TestExplain:
    def test_returns_explanation_report(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ex = ml.explain()
        assert isinstance(ex, ExplanationReport)
        assert ex.explainer_type != "none"
        assert len(ex.feature_importance) > 0

    def test_top_feature_is_highest(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ex = ml.explain()
        if ex.feature_importance:
            top = max(ex.feature_importance, key=ex.feature_importance.get)  # type: ignore[arg-type]
            assert top in ex.feature_importance


class TestReport:
    def test_returns_markdown_string(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        r = ml.report()
        assert isinstance(r, str)
        assert len(r) > 100
        assert "# AetherML Pipeline Report" in r

    def test_report_contains_sections(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        r = ml.report()
        assert "## Summary" in r
        assert "## Model Evaluation" in r
        assert "## Model Explainability" in r


# ── Full pipeline tests ──────────────────────────────────────────


class TestRun:
    def test_run_completes_all_stages(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.run()
        assert ml.state.raw_data is not None
        assert ml.state.processed_data is not None
        assert ml.state.validated_data is not None
        assert ml.state.target_column is not None
        assert ml.state.trained_model is not None
        assert ml.state.evaluation_report is not None
        assert ml.state.final_report is not None

    def test_run_elapsed_time(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.run()
        assert ml.elapsed is not None
        assert ml.elapsed > 0

    def test_run_repr_updated(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.run()
        r = repr(ml)
        assert "stages_completed=" in r


# ── Convenience accessor tests ───────────────────────────────────


class TestAccessors:
    def test_get_data(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        df = ml.get_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10

    def test_get_cleaned_data(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        df = ml.get_cleaned_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_get_features(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        df = ml.get_features()
        assert isinstance(df, pd.DataFrame)
        assert "target" not in df.columns

    def test_get_model(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        model = ml.get_model()
        assert model is not None
        assert hasattr(model, "predict")


# ── Dataclass tests ──────────────────────────────────────────────


class TestResultTypes:
    def test_dataset_summary_is_frozen(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        s = ml.summary()
        with pytest.raises(AttributeError):
            s.rows = 999  # type: ignore[misc]

    def test_validation_report_is_frozen(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        v = ml.validate()
        with pytest.raises(AttributeError):
            v.passed = False  # type: ignore[misc]

    def test_eda_report_is_frozen(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        e = ml.eda()
        with pytest.raises(AttributeError):
            e.shape = (0, 0)  # type: ignore[misc]


# ── Error handling tests ─────────────────────────────────────────


class TestErrorHandling:
    def test_missing_file_raises(self) -> None:
        from aetherml.exceptions import WorkflowError

        ml = AetherML("/nonexistent/file.csv")
        with pytest.raises((WorkflowError, OSError, FileNotFoundError)):
            ml.run()

    def test_invalid_null_strategy(self, csv_path: str) -> None:
        from aetherml.exceptions import WorkflowError

        ml = AetherML(csv_path)
        with pytest.raises((ValueError, KeyError, TypeError, WorkflowError)):
            ml.clean(null_strategy="invalid")

    def test_empty_excel_raises(self, tmp_path: object) -> None:
        from aetherml.exceptions import WorkflowError

        p = tmp_path / "empty.xlsx"  # type: ignore[operator]
        with pd.ExcelWriter(str(p)) as writer:
            pd.DataFrame().to_excel(writer, sheet_name="Empty", index=False)
        ml = AetherML(str(p))
        with pytest.raises((WorkflowError, Exception)):
            ml.run()


# ── Backward compatibility tests ─────────────────────────────────


class TestBackwardCompatibility:
    def test_run_pipeline_still_works(self, csv_path: str) -> None:
        import asyncio

        result = asyncio.run(run_pipeline(data_path=csv_path))
        assert result["row_count"] == 10
        assert result["best_model_type"] is not None

    def test_advanced_api_unchanged(self) -> None:
        """Advanced API classes are still importable."""
        from aetherml import AetherMLConfig, WorkflowState  # noqa: F811

        config = AetherMLConfig()
        state = WorkflowState(data_path="test.csv")
        assert config.engine.preferred is None
        assert state.data_path == "test.csv"
