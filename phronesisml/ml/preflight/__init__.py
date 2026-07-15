"""Pre-flight resource estimation and sampling for PhronesisML.

This module provides pre-flight checks that run BEFORE expensive pipeline
stages (EDA, Feature Engineering, Target Detection, Model Selection,
Explainability, Reporting) to prevent OOM crashes and excessive runtime.

Components:
- ``SamplingConfig``: configurable thresholds and strategy.
- ``ResourceEstimator``: estimates memory, feature count, runtime.
- ``Sampler``: applies configurable sampling (auto, random, stratified, etc.).
- ``MemorySafety``: detects system RAM, enforces safe limits.

Usage::

    from phronesisml.ml.preflight import SamplingConfig, ResourceEstimator, Sampler

    config = SamplingConfig(sample_strategy="auto", sample_size=50000)
    estimator = ResourceEstimator(config)
    report = estimator.estimate(df, engine, task_type="classification")

    if report.requires_sampling:
        sampler = Sampler(config)
        df_sampled = sampler.sample(df, engine, task_type="classification",
                                     target_column="churn")
"""

from phronesisml.ml.preflight.config import SamplingConfig, SamplingMode
from phronesisml.ml.preflight.estimator import ResourceEstimator, ResourceReport
from phronesisml.ml.preflight.memory import MemorySafety, MemoryStatus
from phronesisml.ml.preflight.sampler import Sampler, SamplingMetadata

__all__ = [
    "MemorySafety",
    "MemoryStatus",
    "ResourceEstimator",
    "ResourceReport",
    "Sampler",
    "SamplingConfig",
    "SamplingMetadata",
    "SamplingMode",
]
