"""Minimal configuration for Phronesis.

Uses Pydantic ``BaseSettings`` so that values can be overridden via
environment variables or constructor arguments.  This is the minimal
configuration needed to make the Upload → ETL vertical slice runnable.
Full configuration infrastructure is deferred to a later pass.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "PhronesisConfig",
    "DataConfig",
    "EngineConfig",
    "FeatureSelectionConfig",
    "SamplingConfig",
]


class EngineConfig(BaseModel):
    """Engine selection preferences."""

    preferred: Literal["pandas", "polars", "spark"] | None = Field(
        default=None,
        description="Force a specific engine ('pandas', 'polars', 'spark'). None = auto-select.",
    )
    spark_master: str = Field(
        default="local[*]",
        description="Spark master URL (only used when Spark is selected).",
    )


class DataConfig(BaseModel):
    """Data loading defaults."""

    default_format: str = Field(
        default="auto",
        description=(
            "Default file format when not inferred from extension "
            "('auto', 'csv', 'parquet', 'json')."
        ),
    )
    max_memory_bytes: int = Field(
        default=500 * 1024 * 1024,  # 500 MB
        description=(
            "Memory threshold (bytes) above which Spark is preferred over in-process engines."
        ),
    )
    max_file_size_bytes: int = Field(
        default=2 * 1024 * 1024 * 1024,  # 2 GB
        description=(
            "Maximum file size (bytes) allowed for upload. "
            "Files exceeding this limit are rejected before loading."
        ),
    )


class FeatureSelectionConfig(BaseModel):
    """Feature selection thresholds for Feature Engineering.

    These control the variance-threshold and correlation-based feature
    selection in ``_select_features()``.  Adjusting these allows tuning
    for datasets where the defaults are too aggressive or too lenient.
    """

    variance_threshold: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description=(
            "Features with variance below this are dropped. Lower values retain more features."
        ),
    )
    correlation_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description=(
            "Features with absolute correlation to the target below "
            "this are dropped (supervised selection).  Lower values "
            "retain more features."
        ),
    )
    min_features: int = Field(
        default=1,
        ge=1,
        description=(
            "Minimum number of features to retain.  Prevents feature "
            "selection from dropping ALL features on small datasets."
        ),
    )


class SamplingConfig(BaseModel):
    """Pre-flight sampling and resource estimation configuration.

    Controls automatic sampling of large datasets before expensive
    pipeline stages (EDA, Feature Engineering, Model Selection, etc.).

    Example::

        config = PhronesisConfig(
            sampling=SamplingConfig(
                sample_strategy="auto",
                sample_size=50000,
                random_state=42,
            )
        )
    """

    sample_strategy: Literal[
        "auto",
        "random",
        "stratified",
        "time_aware",
        "head",
        "diversity",
        "anomaly_preserving",
        "text_balanced",
        "disabled",
    ] = Field(
        default="auto",
        description="Sampling strategy. 'auto' uses task-aware sampling.",
    )
    sample_size: int = Field(
        default=50_000,
        ge=100,
        description="Maximum number of rows after sampling.",
    )
    sample_fraction: float = Field(
        default=0.10,
        gt=0.0,
        le=1.0,
        description="Maximum fraction of rows to sample.",
    )
    min_sample_size: int = Field(
        default=500,
        ge=10,
        description="Minimum rows needed for reliable statistical analysis.",
    )
    row_threshold_small: int = Field(
        default=50_000,
        ge=1_000,
        description="Datasets below this row count are processed in full.",
    )
    row_threshold_medium: int = Field(
        default=250_000,
        ge=10_000,
        description="Medium datasets: sample to medium_sample_target rows.",
    )
    row_threshold_large: int = Field(
        default=1_000_000,
        ge=100_000,
        description="Large datasets: sample to large_sample_target rows.",
    )
    medium_sample_target: int = Field(
        default=35_000,
        ge=1_000,
        description="Target sample size for medium datasets.",
    )
    large_sample_target: int = Field(
        default=75_000,
        ge=5_000,
        description="Target sample size for large datasets.",
    )
    max_memory_gb: float = Field(
        default=4.0,
        gt=0.0,
        description="Maximum estimated memory (GB) before sampling is forced.",
    )
    critical_memory_gb: float = Field(
        default=8.0,
        gt=0.0,
        description="Critical memory threshold — stop if sampling cannot fit.",
    )
    random_state: int | None = Field(
        default=42,
        description="Random seed for reproducible sampling.",
    )
    log_sampling: bool = Field(
        default=True,
        description="Log sampling decisions for transparency.",
    )


class PhronesisConfig(BaseModel):
    """Top-level SDK configuration."""

    engine: EngineConfig = Field(default_factory=EngineConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    feature_selection: FeatureSelectionConfig = Field(default_factory=FeatureSelectionConfig)
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)
    null_strategy: str = Field(
        default="drop",
        description="Null handling strategy for ETL ('drop', 'fill', 'flag').",
    )

    model_config = {"extra": "ignore"}
