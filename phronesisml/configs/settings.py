"""Minimal configuration for Phronesis.

Uses Pydantic ``BaseSettings`` so that values can be overridden via
environment variables or constructor arguments.  This is the minimal
configuration needed to make the Upload → ETL vertical slice runnable.
Full configuration infrastructure is deferred to a later pass.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "PhronesisConfig",
    "DataConfig",
    "EngineConfig",
    "FeatureSelectionConfig",
]


class EngineConfig(BaseModel):
    """Engine selection preferences."""

    preferred: str | None = Field(
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
        description=(
            "Features with variance below this are dropped. Lower values retain more features."
        ),
    )
    correlation_threshold: float = Field(
        default=0.05,
        description=(
            "Features with absolute correlation to the target below "
            "this are dropped (supervised selection).  Lower values "
            "retain more features."
        ),
    )
    min_features: int = Field(
        default=1,
        description=(
            "Minimum number of features to retain.  Prevents feature "
            "selection from dropping ALL features on small datasets."
        ),
    )


class PhronesisConfig(BaseModel):
    """Top-level SDK configuration."""

    engine: EngineConfig = Field(default_factory=EngineConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    feature_selection: FeatureSelectionConfig = Field(default_factory=FeatureSelectionConfig)

    model_config = {"extra": "ignore"}
