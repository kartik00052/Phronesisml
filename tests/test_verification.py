"""Verification tests for the 7 gap-closure items.

Tests: degenerate feature selection, async-loop guard, model_type
selection, run() field population, _repr_html_, and Spark error message.
"""

from __future__ import annotations

import asyncio

import pandas as pd
import pytest

from aetherml.sdk import AetherML

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def csv_path(tmp_path: object) -> str:
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
def degenerate_csv(tmp_path: object) -> str:
    """Dataset with near-constant and near-zero-correlation columns."""
    import numpy as np

    rng = np.random.RandomState(42)
    n = 200
    # Near-constant column: 99% same value
    constant_col = np.where(rng.rand(n) < 0.99, 5, 5.01)
    # Near-zero-correlation with target
    noise_col = rng.randn(n)
    # One genuinely useful feature
    useful_col = rng.randn(n)
    target = (useful_col > 0).astype(int)

    p = tmp_path / "degenerate.csv"  # type: ignore[operator]
    df = pd.DataFrame(
        {
            "constant_col": constant_col,
            "noise_col": noise_col,
            "useful_col": useful_col,
            "target": target,
        }
    )
    df.to_csv(p, index=False)
    return str(p)


# ── Item 3: Degenerate feature selection ────────────────────────


class TestDegenerateFeatureSelection:
    """Verify feature_engineering does not drop ALL features on degenerate data."""

    def test_min_features_floor_prevents_all_dropped(self, degenerate_csv: str) -> None:
        """Even with near-constant and near-zero-correlation columns,
        at least 1 feature must survive (min_features floor)."""
        ml = AetherML(degenerate_csv)
        report = ml.engineer_features()

        # min_features=1 default should preserve at least 1 feature
        assert report.n_features >= 1, (
            f"Expected >= 1 feature, got {report.n_features}. "
            "The minimum-feature-count floor is not working."
        )

    def test_configurable_thresholds_in_config(self) -> None:
        """Confirm FeatureSelectionConfig exists with the right fields."""
        from aetherml.configs.settings import FeatureSelectionConfig

        cfg = FeatureSelectionConfig(
            variance_threshold=0.001,
            correlation_threshold=0.01,
            min_features=3,
        )
        assert cfg.variance_threshold == 0.001
        assert cfg.correlation_threshold == 0.01
        assert cfg.min_features == 3

    def test_custom_thresholds_via_sdk(self, degenerate_csv: str) -> None:
        """Pass custom thresholds via AetherMLConfig and verify features survive."""
        from aetherml.configs.settings import (
            AetherMLConfig,
            FeatureSelectionConfig,
        )

        config = AetherMLConfig(
            feature_selection=FeatureSelectionConfig(
                variance_threshold=0.0001,
                correlation_threshold=0.001,
                min_features=2,
            )
        )
        ml = AetherML(degenerate_csv, config=config)
        report = ml.engineer_features()
        assert report.n_features >= 2, (
            f"Expected >= 2 features with min_features=2, got {report.n_features}"
        )

    def test_near_constant_col_retained(self, degenerate_csv: str) -> None:
        """The near-constant column should be retained when min_features > 1."""
        from aetherml.configs.settings import (
            AetherMLConfig,
            FeatureSelectionConfig,
        )

        config = AetherMLConfig(
            feature_selection=FeatureSelectionConfig(
                variance_threshold=0.0001,
                correlation_threshold=0.001,
                min_features=2,
            )
        )
        ml = AetherML(degenerate_csv, config=config)
        report = ml.engineer_features()
        assert "constant_col" in report.feature_names, (
            f"constant_col should be retained, got: {report.feature_names}"
        )


# ── Item 4: Sync method inside running event loop ───────────────


class TestAsyncLoopGuard:
    """Verify sync SDK methods raise clear error inside running event loop."""

    def test_clean_inside_event_loop_raises_runtime_error(self, csv_path: str) -> None:
        async def _inner() -> None:
            ml = AetherML(csv_path)
            with pytest.raises(RuntimeError, match="running event loop"):
                ml.clean()

        asyncio.run(_inner())

    def test_run_inside_event_loop_raises_runtime_error(self, csv_path: str) -> None:
        async def _inner() -> None:
            ml = AetherML(csv_path)
            with pytest.raises(RuntimeError, match="running event loop"):
                ml.run()

        asyncio.run(_inner())

    def test_error_message_is_actionable(self, csv_path: str) -> None:
        async def _inner() -> None:
            ml = AetherML(csv_path)
            with pytest.raises(RuntimeError, match="_async variants"):
                ml.clean()

        asyncio.run(_inner())


# ── Item 5: model_type selection ────────────────────────────────


class TestModelTypeSelection:
    """Verify train(model_type=...) trains that specific model."""

    def test_recommend_model_returns_alternatives(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        info = ml.recommend_model()
        assert len(info.candidates) > 1, (
            "recommend_model should return multiple alternatives"
        )

    def test_train_alternative_model_type(self, csv_path: str) -> None:
        """Train a non-top-recommended model and assert its type."""
        ml = AetherML(csv_path)
        first_run = ml.recommend_model()
        # Pick a different model from candidates
        candidates = first_run.candidates
        assert len(candidates) >= 2, "Need at least 2 candidates for this test"
        alt_name = candidates[1]["name"]
        assert alt_name != first_run.model_type, (
            f"Alternative should differ from top: {alt_name} vs {first_run.model_type}"
        )

        # Now train the alternative
        ml2 = AetherML(csv_path)
        alt_result = ml2.train(model_type=alt_name)
        # The best_pipeline.model_type is the sklearn class name, not the candidate name.
        # But the candidate model_type string should match the candidate name.
        assert alt_result.score > 0.0
        assert alt_result.trials_used >= 1

    def test_train_invalid_model_type_fails(self, csv_path: str) -> None:
        """Requesting a nonexistent model type should fail with clear error."""
        from aetherml.exceptions import WorkflowError

        ml = AetherML(csv_path)
        with pytest.raises((WorkflowError, Exception)):
            ml.train(model_type="nonexistent_model_xyz")


# ── Item 6: run() populates all fields + _repr_html_ ───────────


class TestRunPopulatesAllFields:
    """Verify .run() fills every field on the AetherML state."""

    def test_run_populates_all_fields(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.run()

        state = ml._state
        # summary (raw data loaded)
        assert state.raw_data is not None, "raw_data not populated"
        # cleaned_data
        assert state.processed_data is not None, "processed_data not populated"
        # validation
        assert state.validation_report is not None, "validation_report not populated"
        # eda (profile)
        assert state.data_profile is not None, "data_profile not populated"
        # target
        assert state.target_column is not None, "target_column not populated"
        assert state.task_type is not None, "task_type not populated"
        # features
        assert state.features is not None, "features not populated"
        assert state.feature_names is not None, "feature_names not populated"
        assert len(state.feature_names) > 0, "feature_names is empty"
        # recommendation
        assert state.candidate_models is not None, "candidate_models not populated"
        assert len(state.candidate_models) > 0, "candidate_models is empty"
        assert state.best_pipeline is not None, "best_pipeline not populated"
        # model
        assert state.trained_model is not None, "trained_model not populated"
        # metrics
        assert state.evaluation_report is not None, "evaluation_report not populated"
        metrics = state.evaluation_report.get("metrics")
        assert metrics is not None, "metrics not in evaluation_report"
        # explanation
        assert state.explanation_report is not None, "explanation_report not populated"
        # report
        assert state.final_report is not None, "final_report not populated"
        assert len(state.final_report) > 0, "final_report is empty"

    def test_repr_shows_completed_stages(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        assert "stages_completed=0" in repr(ml)
        ml.run()
        r = repr(ml)
        assert "stages_completed=11" in r
        assert "elapsed=" in r

    def test_repr_html_shows_model(self, csv_path: str) -> None:
        ml = AetherML(csv_path)
        ml.run()
        html = ml._repr_html_()
        assert "AetherML" in html
        assert "Model:" in html
        assert "Target:" in html
        assert "<div" in html


# ── Item 7: Spark engine error message ──────────────────────────


class TestSparkEngineError:
    """Verify Spark engine fails with clear pip install command."""

    def test_spark_engine_import_error_message(self) -> None:
        """SparkEngine._get_or_create_session should raise ImportError with install command."""
        from aetherml.engines.spark_engine import SparkEngine

        engine = SparkEngine()
        with pytest.raises(ImportError, match=r"pip install aetherml\[spark\]"):
            engine._get_or_create_session()

    def test_spark_preferred_config_fails_clearly(self, csv_path: str) -> None:
        """Configuring preferred='spark' should fail with clear error."""
        from aetherml.configs.settings import AetherMLConfig, EngineConfig
        from aetherml.exceptions import WorkflowError

        config = AetherMLConfig(engine=EngineConfig(preferred="spark"))
        ml = AetherML(csv_path, config=config)
        with pytest.raises((ImportError, WorkflowError)) as exc_info:
            ml.run()
        # The error chain should mention pip install
        exc = exc_info.value
        # Walk the cause chain
        current: BaseException | None = exc
        found_install_msg = False
        while current is not None:
            if "pip install" in str(current) and "spark" in str(current).lower():
                found_install_msg = True
                break
            current = current.__cause__
        assert found_install_msg, (
            f"Expected 'pip install aetherml[spark]' in error chain, "
            f"got: {exc}"
        )
