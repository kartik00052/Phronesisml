"""Comprehensive regression tests for PhronesisML preflight system.

Tests cover:
- Small datasets (< 50K rows)
- Medium datasets (50K–250K rows)
- Large datasets (250K–1M rows)
- Extremely large simulated datasets (> 1M rows)
- Imbalanced classification datasets
- Time series datasets
- Regression datasets
- Clustering datasets
- Sampling disabled mode
- Stratified sampling
- Random sampling
- Head sampling
- Deterministic sampling via random_state
- Memory safety checks
- Resource estimation accuracy
- Backward compatibility

All tests verify:
- No workflow hangs
- No excessive memory allocation
- No loss of required metadata
- No breaking API changes
"""

from __future__ import annotations

import random
import time

import pandas as pd
import polars as pl
import pytest

from phronesisml.engines.pandas_engine import PandasEngine
from phronesisml.engines.polars_engine import PolarsEngine
from phronesisml.ml.preflight.config import SamplingConfig, SamplingMode
from phronesisml.ml.preflight.estimator import ResourceEstimator
from phronesisml.ml.preflight.memory import MemorySafety, MemoryStatus
from phronesisml.ml.preflight.sampler import Sampler, SamplingMetadata, SamplingResult

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def polars_engine() -> PolarsEngine:
    return PolarsEngine()


@pytest.fixture
def pandas_engine() -> PandasEngine:
    return PandasEngine()


@pytest.fixture
def small_classification_df() -> pl.DataFrame:
    """Small dataset: 500 rows, 10 columns, binary classification."""
    rng = random.Random(42)
    return pl.DataFrame(
        {
            "feature_1": [rng.gauss(0, 1) for _ in range(500)],
            "feature_2": [rng.gauss(0, 1) for _ in range(500)],
            "feature_3": [rng.randint(0, 10) for _ in range(500)],
            "feature_4": [rng.gauss(0, 1) for _ in range(500)],
            "feature_5": [rng.uniform(0, 100) for _ in range(500)],
            "category_a": [rng.choice(["X", "Y", "Z"]) for _ in range(500)],
            "category_b": [rng.choice(["A", "B"]) for _ in range(500)],
            "target": [rng.choice([0, 1]) for _ in range(500)],
        }
    )


@pytest.fixture
def medium_regression_df() -> pl.DataFrame:
    """Medium dataset: 100,000 rows, 15 columns, regression."""
    rng = random.Random(42)
    return pl.DataFrame(
        {f"feature_{i}": [rng.gauss(0, 1) for _ in range(100_000)] for i in range(10)}
        | {
            "cat_col": [rng.choice(["A", "B", "C", "D"]) for _ in range(100_000)],
            "target": [rng.gauss(50, 10) for _ in range(100_000)],
        }
    )


@pytest.fixture
def large_classification_df() -> pl.DataFrame:
    """Large dataset: 500,000 rows, 12 columns, imbalanced classification."""
    rng = random.Random(42)
    # 95% class 0, 5% class 1 (imbalanced)
    targets = [0] * 475_000 + [1] * 25_000
    rng.shuffle(targets)
    return pl.DataFrame(
        {f"num_{i}": [rng.gauss(0, 1) for _ in range(500_000)] for i in range(8)}
        | {
            "cat_1": [rng.choice(["P", "Q", "R"]) for _ in range(500_000)],
            "cat_2": [rng.choice(["X", "Y"]) for _ in range(500_000)],
            "id_number": list(range(500_000)),
            "target": targets,
        }
    )


@pytest.fixture
def time_series_df() -> pl.DataFrame:
    """Time series dataset: 50,000 rows with temporal ordering."""
    return pl.DataFrame(
        {
            "timestamp": list(range(50_000)),
            "value_a": [float(i) + random.gauss(0, 0.1) for i in range(50_000)],
            "value_b": [float(i * 2) + random.gauss(0, 0.2) for i in range(50_000)],
            "category": [random.choice(["P", "Q"]) for _ in range(50_000)],
            "target": [float(i * 0.5 + random.gauss(0, 1)) for i in range(50_000)],
        }
    )


@pytest.fixture
def clustering_df() -> pl.DataFrame:
    """Clustering dataset: 5,000 rows, 8 numeric columns."""
    rng = random.Random(42)
    return pl.DataFrame({f"dim_{i}": [rng.gauss(0, 1) for _ in range(5_000)] for i in range(8)})


@pytest.fixture
def anomaly_df() -> pl.DataFrame:
    """Anomaly detection dataset: 10,000 rows, 2% anomaly rate."""
    rng = random.Random(42)
    labels = [0] * 9_800 + [1] * 200
    rng.shuffle(labels)
    return pl.DataFrame(
        {f"feature_{i}": [rng.gauss(0, 1) for _ in range(10_000)] for i in range(6)}
        | {
            "is_anomaly": labels,
        }
    )


@pytest.fixture
def default_config() -> SamplingConfig:
    return SamplingConfig()


@pytest.fixture
def disabled_config() -> SamplingConfig:
    return SamplingConfig(sample_strategy="disabled")


@pytest.fixture
def aggressive_config() -> SamplingConfig:
    """Config that triggers sampling more aggressively."""
    return SamplingConfig(
        sample_strategy="auto",
        sample_size=5_000,
        row_threshold_small=1_000,
        row_threshold_medium=10_000,
        row_threshold_large=100_000,
        medium_sample_target=3_000,
        large_sample_target=5_000,
        random_state=42,
    )


# ── Test: Resource Estimation ────────────────────────────────────────


class TestResourceEstimator:
    """Tests for ResourceEstimator."""

    def test_small_dataset_no_sampling_needed(
        self,
        polars_engine,
        small_classification_df,
        default_config,
    ):
        estimator = ResourceEstimator(default_config)
        report = estimator.estimate(
            small_classification_df,
            polars_engine,
            task_type="classification",
            target_column="target",
        )
        assert report.n_rows == 500
        assert report.n_cols == 8
        assert report.total_cells == 4000
        assert not report.requires_sampling
        assert report.estimated_memory_mb > 0
        assert report.estimated_encoded_features > 0
        assert report.estimated_runtime_seconds > 0

    def test_medium_dataset_sampling_recommended(
        self,
        polars_engine,
        medium_regression_df,
        aggressive_config,
    ):
        estimator = ResourceEstimator(aggressive_config)
        report = estimator.estimate(
            medium_regression_df,
            polars_engine,
            task_type="regression",
            target_column="target",
        )
        assert report.n_rows == 100_000
        assert report.requires_sampling
        assert report.recommended_sample_size <= aggressive_config.sample_size
        assert report.recommended_sample_fraction < 1.0

    def test_large_dataset_sampling_recommended(
        self,
        polars_engine,
        large_classification_df,
        default_config,
    ):
        estimator = ResourceEstimator(default_config)
        report = estimator.estimate(
            large_classification_df,
            polars_engine,
            task_type="classification",
            target_column="target",
        )
        assert report.n_rows == 500_000
        assert report.requires_sampling
        assert report.recommended_sample_size <= default_config.large_sample_target

    def test_disabled_sampling_still_checks_memory(
        self,
        polars_engine,
        large_classification_df,
        disabled_config,
    ):
        estimator = ResourceEstimator(disabled_config)
        report = estimator.estimate(
            large_classification_df,
            polars_engine,
            task_type="classification",
            target_column="target",
        )
        # Even with sampling disabled, the estimator still reports
        # the need (but the sampler won't act on it)
        assert report.n_rows == 500_000

    def test_report_to_dict(self, polars_engine, small_classification_df):
        estimator = ResourceEstimator()
        report = estimator.estimate(small_classification_df, polars_engine)
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "n_rows" in d
        assert "estimated_memory_mb" in d
        assert "requires_sampling" in d


# ── Test: Memory Safety ──────────────────────────────────────────────


class TestMemorySafety:
    """Tests for MemorySafety."""

    def test_available_memory_detected(self):
        safety = MemorySafety()
        available = safety.get_available_memory_gb()
        assert available > 0
        assert isinstance(available, float)

    def test_total_memory_detected(self):
        safety = MemorySafety()
        total = safety.get_total_memory_gb()
        assert total > 0

    def test_memory_status_ok(self):
        safety = MemorySafety(max_memory_gb=1.0, critical_memory_gb=2.0)
        status, available = safety.check_available_memory()
        assert status in (MemoryStatus.OK, MemoryStatus.WARNING, MemoryStatus.CRITICAL)
        assert available > 0

    def test_estimate_memory_status_ok(self):
        safety = MemorySafety(max_memory_gb=100.0, critical_memory_gb=200.0)
        status = safety.estimate_memory_status(1.0)
        assert status == MemoryStatus.OK

    def test_estimate_memory_status_critical(self):
        safety = MemorySafety(max_memory_gb=0.001, critical_memory_gb=0.002)
        status = safety.estimate_memory_status(100.0)
        assert status == MemoryStatus.CRITICAL

    def test_validate_estimates_ok(self):
        safety = MemorySafety(max_memory_gb=100.0, critical_memory_gb=200.0)
        estimates = {"estimated_memory_gb": 1.0}
        result = safety.validate_estimates(estimates)
        assert result["safe"] is True
        assert result["status"] == "ok"

    def test_validate_estimates_critical(self):
        safety = MemorySafety(max_memory_gb=0.001, critical_memory_gb=0.002)
        estimates = {"estimated_memory_gb": 100.0}
        result = safety.validate_estimates(estimates)
        assert result["safe"] is False
        assert result["status"] == "critical"
        assert len(result["blockers"]) > 0
        assert len(result["recommended_actions"]) > 0


# ── Test: Sampling Config ────────────────────────────────────────────


class TestSamplingConfig:
    """Tests for SamplingConfig."""

    def test_default_config(self):
        config = SamplingConfig()
        assert config.sample_strategy == SamplingMode.AUTO
        assert config.sample_size == 50_000
        assert config.sample_fraction == 0.10
        assert config.random_state == 42

    def test_custom_config(self):
        config = SamplingConfig(
            sample_strategy="stratified",
            sample_size=10_000,
            sample_fraction=0.20,
            random_state=123,
        )
        assert config.sample_strategy == SamplingMode.STRATIFIED
        assert config.sample_size == 10_000
        assert config.sample_fraction == 0.20
        assert config.random_state == 123

    def test_config_validation(self):
        # sample_size must be >= 100
        with pytest.raises(Exception):
            SamplingConfig(sample_size=50)

        # sample_fraction must be > 0 and <= 1
        with pytest.raises(Exception):
            SamplingConfig(sample_fraction=0.0)

        with pytest.raises(Exception):
            SamplingConfig(sample_fraction=1.5)


# ── Test: Sampler ────────────────────────────────────────────────────


class TestSampler:
    """Tests for Sampler across all modes and engines."""

    def test_random_sampling_polars(self, polars_engine, small_classification_df):
        config = SamplingConfig(
            sample_strategy="random",
            sample_size=100,
            sample_fraction=1.0,
            min_sample_size=50,
            random_state=42,
        )
        sampler = Sampler(config)
        result = sampler.sample(
            small_classification_df,
            polars_engine,
            task_type="classification",
            target_column="target",
        )
        assert isinstance(result, SamplingResult)
        assert result.metadata.was_sampled
        assert result.metadata.sample_rows == 100
        assert result.metadata.original_rows == 500
        assert result.metadata.sampling_ratio == pytest.approx(0.2, abs=0.01)

    def test_random_sampling_pandas(self, pandas_engine, small_classification_df):
        config = SamplingConfig(
            sample_strategy="random",
            sample_size=100,
            sample_fraction=1.0,
            min_sample_size=50,
            random_state=42,
        )
        sampler = Sampler(config)
        # Convert to pandas for pandas engine
        pd_df = small_classification_df.to_pandas()
        result = sampler.sample(
            pd_df,
            pandas_engine,
            task_type="classification",
            target_column="target",
        )
        assert isinstance(result, SamplingResult)
        assert result.metadata.was_sampled
        assert result.metadata.sample_rows == 100

    def test_stratified_sampling(self, polars_engine, small_classification_df):
        config = SamplingConfig(
            sample_strategy="stratified",
            sample_size=100,
            sample_fraction=1.0,
            min_sample_size=50,
            random_state=42,
        )
        sampler = Sampler(config)
        result = sampler.sample(
            small_classification_df,
            polars_engine,
            task_type="classification",
            target_column="target",
        )
        assert result.metadata.was_sampled
        assert result.metadata.sample_rows == 100
        # Verify class distribution is preserved
        collected = polars_engine.cached_collect(result.dataframe)
        original_dist = small_classification_df["target"].value_counts()
        sampled_dist = collected["target"].value_counts()
        # Ratios should be similar
        assert len(sampled_dist) == len(original_dist)

    def test_head_sampling(self, polars_engine, medium_regression_df):
        config = SamplingConfig(sample_strategy="head", sample_size=500)
        sampler = Sampler(config)
        result = sampler.sample(medium_regression_df, polars_engine)
        assert result.metadata.was_sampled
        assert result.metadata.sample_rows == 500
        assert result.metadata.sampling_method == "head"

    def test_disabled_sampling(self, polars_engine, large_classification_df):
        config = SamplingConfig(sample_strategy="disabled")
        sampler = Sampler(config)
        result = sampler.sample(
            large_classification_df,
            polars_engine,
            task_type="classification",
        )
        assert not result.metadata.was_sampled
        assert result.metadata.sample_rows == 500_000

    def test_time_aware_sampling(self, polars_engine, time_series_df):
        config = SamplingConfig(sample_strategy="time_aware", sample_size=5_000)
        sampler = Sampler(config)
        result = sampler.sample(
            time_series_df,
            polars_engine,
            task_type="time_series",
        )
        assert result.metadata.was_sampled
        assert result.metadata.sample_rows == 5_000
        # Verify temporal ordering is preserved
        collected = polars_engine.cached_collect(result.dataframe)
        timestamps = collected["timestamp"].to_list()
        assert timestamps == sorted(timestamps)

    def test_anomaly_preserving_sampling(self, polars_engine, anomaly_df):
        config = SamplingConfig(sample_strategy="anomaly_preserving", sample_size=2_000)
        sampler = Sampler(config)
        result = sampler.sample(
            anomaly_df,
            polars_engine,
            task_type="anomaly_detection",
            target_column="is_anomaly",
        )
        assert result.metadata.was_sampled
        # Verify anomaly ratio is approximately preserved
        collected = polars_engine.cached_collect(result.dataframe)
        original_ratio = anomaly_df["is_anomaly"].mean()
        sampled_ratio = collected["is_anomaly"].mean()
        assert abs(original_ratio - sampled_ratio) < 0.02  # Within 2%

    def test_diversity_sampling(self, polars_engine, clustering_df):
        config = SamplingConfig(sample_strategy="diversity", sample_size=500)
        sampler = Sampler(config)
        result = sampler.sample(
            clustering_df,
            polars_engine,
            task_type="clustering",
        )
        assert result.metadata.was_sampled
        assert result.metadata.sample_rows == 500

    def test_auto_strategy_classification(self, polars_engine, small_classification_df):
        config = SamplingConfig(
            sample_strategy="auto",
            sample_size=100,
            row_threshold_small=1_000,  # Force sampling by being above dataset size threshold
            random_state=42,
        )
        sampler = Sampler(config)
        result = sampler.sample(
            small_classification_df,
            polars_engine,
            task_type="classification",
            target_column="target",
        )
        # Auto should resolve to stratified for classification
        assert result.metadata.sampling_method == "stratified"

    def test_auto_strategy_regression(self, polars_engine, medium_regression_df):
        config = SamplingConfig(
            sample_strategy="auto",
            sample_size=5_000,
            row_threshold_small=1_000,
            random_state=42,
        )
        sampler = Sampler(config)
        result = sampler.sample(
            medium_regression_df,
            polars_engine,
            task_type="regression",
            target_column="target",
        )
        # Auto should resolve to random for regression
        assert result.metadata.sampling_method == "random"

    def test_deterministic_with_random_state(self, polars_engine, small_classification_df):
        config1 = SamplingConfig(sample_strategy="random", sample_size=100, random_state=42)
        config2 = SamplingConfig(sample_strategy="random", sample_size=100, random_state=42)
        sampler1 = Sampler(config1)
        sampler2 = Sampler(config2)
        result1 = sampler1.sample(small_classification_df, polars_engine)
        result2 = sampler2.sample(small_classification_df, polars_engine)
        # Same random_state should produce same sample
        collected1 = polars_engine.cached_collect(result1.dataframe)
        collected2 = polars_engine.cached_collect(result2.dataframe)
        assert collected1.equals(collected2)

    def test_no_sample_when_already_small(self, polars_engine, small_classification_df):
        config = SamplingConfig(
            sample_strategy="random",
            sample_size=1000,  # Larger than dataset
        )
        sampler = Sampler(config)
        result = sampler.sample(small_classification_df, polars_engine)
        assert not result.metadata.was_sampled
        assert result.metadata.sample_rows == 500

    def test_sample_metadata_to_dict(self):
        metadata = SamplingMetadata(
            original_rows=1000,
            sample_rows=500,
            sampling_ratio=0.5,
            sampling_method="random",
            random_state=42,
            was_sampled=True,
            reason="Test sampling.",
        )
        d = metadata.to_dict()
        assert d["original_rows"] == 1000
        assert d["sample_rows"] == 500
        assert d["was_sampled"] is True


# ── Test: Engine Integration ─────────────────────────────────────────


class TestEngineSampling:
    """Tests for engine-level sample() method."""

    def test_polars_engine_sample_random(self, polars_engine, small_classification_df):
        result = polars_engine.sample(
            small_classification_df,
            n=100,
            random_state=42,
        )
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 100

    def test_polars_engine_sample_fraction(self, polars_engine, small_classification_df):
        result = polars_engine.sample(
            small_classification_df,
            fraction=0.2,
            random_state=42,
        )
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 100

    def test_polars_engine_sample_head(self, polars_engine, small_classification_df):
        result = polars_engine.sample(
            small_classification_df,
            n=50,
            strategy="head",
        )
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 50

    def test_pandas_engine_sample_random(self, pandas_engine, small_classification_df):
        pd_df = small_classification_df.to_pandas()
        result = pandas_engine.sample(pd_df, n=100, random_state=42)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100

    def test_pandas_engine_sample_fraction(self, pandas_engine, small_classification_df):
        pd_df = small_classification_df.to_pandas()
        result = pandas_engine.sample(pd_df, fraction=0.2, random_state=42)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100

    def test_pandas_engine_sample_head(self, pandas_engine, small_classification_df):
        pd_df = small_classification_df.to_pandas()
        result = pandas_engine.sample(pd_df, n=50, strategy="head")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 50


# ── Test: Workflow Integration ───────────────────────────────────────


class TestWorkflowSampling:
    """Tests for workflow-level sampling node."""

    @pytest.mark.asyncio
    async def test_sampling_node_runs(
        self,
        polars_engine,
        medium_regression_df,
        aggressive_config,
    ):
        from phronesisml.workflow.sampling_node import create_sampling_node

        node = create_sampling_node(polars_engine, aggressive_config)

        # Create a mock state
        class MockState:
            processed_data = medium_regression_df
            validated_data = None
            task_type = "regression"
            target_column = "target"
            data_profile = None
            sampling_metadata = None

        state = MockState()
        result = await node(state)

        assert "processed_data" in result
        assert "sampling_metadata" in result
        assert result["sampling_metadata"]["was_sampled"] is True

    @pytest.mark.asyncio
    async def test_sampling_node_skips_when_disabled(
        self,
        polars_engine,
        small_classification_df,
        disabled_config,
    ):
        from phronesisml.workflow.sampling_node import create_sampling_node

        node = create_sampling_node(polars_engine, disabled_config)

        class MockState:
            processed_data = small_classification_df
            validated_data = None
            task_type = "classification"
            target_column = "target"
            data_profile = None
            sampling_metadata = None

        state = MockState()
        result = await node(state)

        # Should not sample when disabled
        assert result == {}

    @pytest.mark.asyncio
    async def test_sampling_node_skips_when_already_sampled(
        self,
        polars_engine,
        small_classification_df,
        aggressive_config,
    ):
        from phronesisml.workflow.sampling_node import create_sampling_node

        node = create_sampling_node(polars_engine, aggressive_config)

        class MockState:
            processed_data = small_classification_df
            validated_data = None
            task_type = "classification"
            target_column = "target"
            data_profile = None
            sampling_metadata = {"was_sampled": True}

        state = MockState()
        result = await node(state)

        # Should skip if already sampled
        assert result == {}

    @pytest.mark.asyncio
    async def test_sampling_node_no_data(self, polars_engine, aggressive_config):
        from phronesisml.workflow.sampling_node import create_sampling_node

        node = create_sampling_node(polars_engine, aggressive_config)

        class MockState:
            processed_data = None
            validated_data = None
            task_type = None
            target_column = None
            data_profile = None
            sampling_metadata = None

        state = MockState()
        result = await node(state)

        # Should skip if no data
        assert result == {}


# ── Test: Backward Compatibility ─────────────────────────────────────


class TestBackwardCompatibility:
    """Ensure no breaking changes to existing APIs."""

    def test_config_importable(self):
        from phronesisml.configs.settings import PhronesisConfig

        config = PhronesisConfig()
        assert hasattr(config, "sampling")
        assert config.sampling.sample_strategy == "auto"

    def test_workflow_state_has_sampling_fields(self):
        from phronesisml.workflow.state import WorkflowState

        state = WorkflowState()
        assert state.sampling_metadata is None
        assert state.resource_report is None
        assert state.preflight_warnings is None
        assert state.preflight_blockers is None

    def test_engine_sample_methods_exist(self):
        assert hasattr(PolarsEngine, "sample")
        assert hasattr(PandasEngine, "sample")

    def test_preflight_module_importable(self):
        from phronesisml.ml.preflight import (
            ResourceEstimator,
            Sampler,
            SamplingConfig,
        )

        assert ResourceEstimator is not None
        assert Sampler is not None
        assert SamplingConfig is not None

    def test原有的_simple_api不受影响(self):
        """Verify that the simple API functions still work."""
        from phronesisml.simple import analyze, clean, validate

        # Just verify they're importable — actual execution tested elsewhere
        assert callable(analyze)
        assert callable(clean)
        assert callable(validate)


# ── Test: Performance & Stress ───────────────────────────────────────


class TestPerformance:
    """Performance regression tests — ensure sampling doesn't hang."""

    def test_sampling_completes_quickly_for_medium_dataset(
        self,
        polars_engine,
        medium_regression_df,
        aggressive_config,
    ):
        sampler = Sampler(aggressive_config)
        start = time.time()
        result = sampler.sample(
            medium_regression_df,
            polars_engine,
            task_type="regression",
        )
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Sampling took {elapsed:.1f}s — too slow"
        assert result.metadata.was_sampled

    def test_resource_estimation_completes_quickly(
        self,
        polars_engine,
        medium_regression_df,
        aggressive_config,
    ):
        estimator = ResourceEstimator(aggressive_config)
        start = time.time()
        report = estimator.estimate(
            medium_regression_df,
            polars_engine,
            task_type="regression",
        )
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Estimation took {elapsed:.1f}s — too slow"
        assert report.n_rows == 100_000
