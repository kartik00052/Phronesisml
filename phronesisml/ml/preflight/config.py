"""Sampling configuration for PhronesisML pre-flight system.

Defines the ``SamplingMode`` enum and ``SamplingConfig`` dataclass that
control how and when the framework samples large datasets before
expensive pipeline stages.

Design:
- All thresholds are configurable with sensible defaults.
- ``auto`` mode uses task-aware sampling (stratified for classification,
  random for regression, time-preserving for time series).
- ``disabled`` mode turns off all automatic sampling.
- Deterministic via ``random_state`` for reproducibility.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class SamplingMode(StrEnum):
    """Sampling strategy modes.

    Attributes:
        auto: Task-aware sampling (stratified for classification, random
            for regression, time-preserving for time series). Default.
        random: Uniform random sampling without stratification.
        stratified: Stratified sampling preserving class distribution.
        time_aware: Preserve chronological ordering (for time series).
        head: Take the first N rows (deterministic, no randomness).
        diversity: Diversity-preserving sampling for clustering.
        anomaly_preserving: Preserve anomaly ratio for anomaly detection.
        text_balanced: Preserve label balance and document diversity.
        disabled: No automatic sampling — process entire dataset.
    """

    AUTO = "auto"
    RANDOM = "random"
    STRATIFIED = "stratified"
    TIME_AWARE = "time_aware"
    HEAD = "head"
    DIVERSITY = "diversity"
    ANOMALY_PRESERVING = "anomaly_preserving"
    TEXT_BALANCED = "text_balanced"
    DISABLED = "disabled"


class SamplingConfig(BaseModel):
    """Configurable sampling parameters.

    All thresholds use sensible defaults that work for most datasets.
    Users can override any value via the SDK config or function arguments.

    Example::

        config = SamplingConfig(
            sample_strategy="auto",
            sample_size=50000,
            sample_fraction=0.10,
            random_state=42,
        )
    """

    # ── Strategy ─────────────────────────────────────────────────────
    sample_strategy: (
        SamplingMode
        | Literal[
            "auto",
            "random",
            "stratified",
            "time_aware",
            "head",
            "diversity",
            "anomaly_preserving",
            "text_balanced",
            "disabled",
        ]
    ) = Field(
        default=SamplingMode.AUTO,
        description="Sampling strategy. 'auto' uses task-aware sampling.",
    )

    # ── Size limits ──────────────────────────────────────────────────
    sample_size: int = Field(
        default=50_000,
        ge=100,
        description="Maximum number of rows after sampling.",
    )
    sample_fraction: float = Field(
        default=0.10,
        gt=0.0,
        le=1.0,
        description="Maximum fraction of rows to sample (used when sample_size is not set).",
    )
    min_sample_size: int = Field(
        default=500,
        ge=10,
        description="Minimum rows needed for reliable statistical analysis.",
    )

    # ── Row thresholds (auto mode) ───────────────────────────────────
    row_threshold_small: int = Field(
        default=50_000,
        ge=1_000,
        description="Datasets below this row count are processed in full.",
    )
    row_threshold_medium: int = Field(
        default=250_000,
        ge=10_000,
        description="Medium datasets: sample up to medium_sample_target rows.",
    )
    row_threshold_large: int = Field(
        default=1_000_000,
        ge=100_000,
        description="Large datasets: sample up to large_sample_target rows.",
    )
    medium_sample_target: int = Field(
        default=35_000,
        ge=1_000,
        description="Target sample size for medium datasets (50K–250K rows).",
    )
    large_sample_target: int = Field(
        default=75_000,
        ge=5_000,
        description="Target sample size for large datasets (250K–1M rows).",
    )

    # ── Memory limits ────────────────────────────────────────────────
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

    # ── Determinism ──────────────────────────────────────────────────
    random_state: int | None = Field(
        default=42,
        description="Random seed for reproducible sampling. None for non-deterministic.",
    )

    # ── Transparency ─────────────────────────────────────────────────
    log_sampling: bool = Field(
        default=True,
        description="Log sampling decisions for transparency.",
    )

    model_config = {"extra": "ignore"}
