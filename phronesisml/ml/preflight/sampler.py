"""Configurable sampler for PhronesisML.

Provides multiple sampling strategies that integrate with all engine
backends (Polars, Pandas, PySpark). Sampling occurs BEFORE expensive
pipeline stages and the original dataset remains unchanged.

Sampling modes:
- ``auto``: Task-aware (stratified for classification, random for
  regression, etc.)
- ``random``: Uniform random sampling.
- ``stratified``: Preserve class distribution.
- ``time_aware``: Preserve chronological ordering.
- ``head``: Take first N rows.
- ``diversity``: Diversity-preserving for clustering.
- ``anomaly_preserving``: Preserve anomaly ratio.
- ``text_balanced``: Preserve label balance and document diversity.
- ``disabled``: No sampling.

Design:
- Returns a ``SamplingResult`` with the sampled DataFrame and metadata.
- The original DataFrame is NEVER modified.
- All sampling is deterministic when ``random_state`` is set.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from phronesisml.engines.base_engine import BaseEngine
from phronesisml.ml.preflight.config import SamplingConfig, SamplingMode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SamplingMetadata:
    """Metadata about a sampling operation.

    Included in reports and PipelineResult for transparency.
    """

    original_rows: int
    sample_rows: int
    sampling_ratio: float
    sampling_method: str
    random_state: int | None
    was_sampled: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a serializable dict."""
        return {
            "original_rows": self.original_rows,
            "sample_rows": self.sample_rows,
            "sampling_ratio": self.sampling_ratio,
            "sampling_method": self.sampling_method,
            "random_state": self.random_state,
            "was_sampled": self.was_sampled,
            "reason": self.reason,
        }


class Sampler:
    """Configurable sampler that integrates with all engine backends.

    Args:
        config: Sampling configuration.

    Example::

        config = SamplingConfig(sample_strategy="auto", sample_size=50000)
        sampler = Sampler(config)
        result = sampler.sample(df, engine, task_type="classification",
                                 target_column="churn")
        df_sampled = result.dataframe
        print(result.metadata)
    """

    def __init__(self, config: SamplingConfig | None = None) -> None:
        self._config = config or SamplingConfig()

    def sample(
        self,
        df: Any,
        engine: BaseEngine,
        task_type: str | None = None,
        target_column: str | None = None,
        strategy: SamplingMode | str | None = None,
        sample_size: int | None = None,
        sample_fraction: float | None = None,
        random_state: int | None = None,
    ) -> SamplingResult:
        """Apply sampling to the DataFrame based on configuration.

        Args:
            df: Engine-native DataFrame.
            engine: Active computation engine.
            task_type: Detected task type (classification, regression,
                clustering, anomaly_detection, time_series).
            target_column: Target column name (for stratified sampling).
            strategy: Override the configured sampling strategy.
            sample_size: Override the configured sample size.
            sample_fraction: Override the configured sample fraction.
            random_state: Override the configured random state.

        Returns:
            A ``SamplingResult`` with the sampled DataFrame and metadata.
        """
        config = self._config
        effective_strategy = strategy or config.sample_strategy
        effective_size = sample_size or config.sample_size
        effective_fraction = sample_fraction or config.sample_fraction
        effective_random_state = random_state if random_state is not None else config.random_state

        # Resolve strategy for auto mode — handle both str and enum
        strategy_str = str(effective_strategy)
        if isinstance(effective_strategy, SamplingMode):
            strategy_str = effective_strategy.value

        if strategy_str == SamplingMode.AUTO or strategy_str == "auto":
            effective_strategy = self._resolve_auto_strategy(task_type)
            strategy_str = effective_strategy.value

        n_rows, _ = engine.shape(df)

        # Check if sampling is needed
        if strategy_str == "disabled":
            return SamplingResult(
                dataframe=df,
                metadata=SamplingMetadata(
                    original_rows=n_rows,
                    sample_rows=n_rows,
                    sampling_ratio=1.0,
                    sampling_method="disabled",
                    random_state=effective_random_state,
                    was_sampled=False,
                    reason="Sampling is disabled by configuration.",
                ),
            )

        # Compute target sample size
        target_size = self._compute_target_size(n_rows, effective_size, effective_fraction)

        # If dataset is already small enough, skip sampling
        if target_size >= n_rows:
            return SamplingResult(
                dataframe=df,
                metadata=SamplingMetadata(
                    original_rows=n_rows,
                    sample_rows=n_rows,
                    sampling_ratio=1.0,
                    sampling_method=strategy_str,
                    random_state=effective_random_state,
                    was_sampled=False,
                    reason=f"Dataset ({n_rows:,} rows) is already within target ({target_size:,}).",
                ),
            )

        # Apply the sampling strategy
        logger.info(
            "Sampling %d rows to %d (%.1f%%) using strategy '%s'",
            n_rows,
            target_size,
            target_size / n_rows * 100,
            strategy_str,
        )

        if strategy_str == "random":
            sampled_pd = self._sample_random(df, engine, target_size, effective_random_state)
        elif strategy_str == "stratified":
            sampled_pd = self._sample_stratified(
                df, engine, target_size, target_column, effective_random_state
            )
        elif strategy_str == "time_aware":
            sampled_pd = self._sample_time_aware(df, engine, target_size, effective_random_state)
        elif strategy_str == "head":
            sampled_pd = self._sample_head(df, engine, target_size)
        elif strategy_str == "diversity":
            sampled_pd = self._sample_diversity(df, engine, target_size, effective_random_state)
        elif strategy_str == "anomaly_preserving":
            sampled_pd = self._sample_anomaly_preserving(
                df, engine, target_size, target_column, effective_random_state
            )
        elif strategy_str == "text_balanced":
            sampled_pd = self._sample_stratified(
                df, engine, target_size, target_column, effective_random_state
            )
        else:
            # Fallback to random
            sampled_pd = self._sample_random(df, engine, target_size, effective_random_state)

        # Convert back to engine-native format
        sampled_engine = self._to_engine_native(sampled_pd, engine)

        actual_rows = len(sampled_pd)
        metadata = SamplingMetadata(
            original_rows=n_rows,
            sample_rows=actual_rows,
            sampling_ratio=round(actual_rows / max(n_rows, 1), 4),
            sampling_method=strategy_str,
            random_state=effective_random_state,
            was_sampled=True,
            reason=(
                f"Sampled {n_rows:,} → {actual_rows:,} rows "
                f"({actual_rows / n_rows:.1%}) using {strategy_str}."
            ),
        )

        if config.log_sampling:
            logger.info(
                "Sampling complete: %d → %d rows (%.1f%%) using %s",
                n_rows,
                actual_rows,
                actual_rows / n_rows * 100,
                effective_strategy,
            )

        return SamplingResult(dataframe=sampled_engine, metadata=metadata)

    # ── Strategy resolution ──────────────────────────────────────────

    def _resolve_auto_strategy(self, task_type: str | None) -> SamplingMode:
        """Resolve 'auto' to a concrete strategy based on task type."""
        strategy_map = {
            "classification": SamplingMode.STRATIFIED,
            "regression": SamplingMode.RANDOM,
            "clustering": SamplingMode.DIVERSITY,
            "anomaly_detection": SamplingMode.ANOMALY_PRESERVING,
            "time_series": SamplingMode.TIME_AWARE,
        }
        return strategy_map.get(task_type, SamplingMode.RANDOM)

    def _compute_target_size(
        self,
        n_rows: int,
        sample_size: int,
        sample_fraction: float,
    ) -> int:
        """Compute the target sample size."""
        fraction_based = int(n_rows * sample_fraction)
        return max(self._config.min_sample_size, min(fraction_based, sample_size))

    # ── Sampling implementations ─────────────────────────────────────

    def _to_engine_native(self, pd_df: pd.DataFrame, engine: BaseEngine) -> Any:
        """Convert a Pandas DataFrame back to engine-native format.

        For Polars engine, converts back to Polars DataFrame.
        For Pandas engine, returns as-is.
        """
        engine_type = engine.engine_type.value

        if engine_type == "polars":
            try:
                import polars as pl

                return pl.from_pandas(pd_df)
            except Exception:
                return pd_df
        else:
            return pd_df

    def _sample_random(
        self,
        df: Any,
        engine: BaseEngine,
        target_size: int,
        random_state: int | None,
    ) -> pd.DataFrame:
        """Uniform random sampling."""
        collected = engine.cached_collect(df)
        return collected.sample(
            n=min(target_size, len(collected)),
            random_state=random_state,
        ).reset_index(drop=True)

    def _sample_stratified(
        self,
        df: Any,
        engine: BaseEngine,
        target_size: int,
        target_column: str | None,
        random_state: int | None,
    ) -> pd.DataFrame:
        """Stratified sampling preserving class distribution."""
        collected = engine.cached_collect(df)

        if target_column is None or target_column not in collected.columns:
            # Fallback to random if no target column
            return collected.sample(
                n=min(target_size, len(collected)),
                random_state=random_state,
            ).reset_index(drop=True)

        try:
            # Use sklearn for stratified sampling
            from sklearn.model_selection import train_test_split

            fraction = target_size / len(collected)
            if fraction >= 1.0:
                return collected

            sampled, _ = train_test_split(
                collected,
                train_size=fraction,
                stratify=collected[target_column],
                random_state=random_state,
            )
            return sampled.reset_index(drop=True)
        except ValueError:
            # stratify fails if a class has only 1 sample — fallback to random
            logger.warning(
                "Stratified sampling failed (class imbalance too severe) — "
                "falling back to random sampling."
            )
            return collected.sample(
                n=min(target_size, len(collected)),
                random_state=random_state,
            ).reset_index(drop=True)

    def _sample_time_aware(
        self,
        df: Any,
        engine: BaseEngine,
        target_size: int,
        random_state: int | None,
    ) -> pd.DataFrame:
        """Time-aware sampling preserving chronological ordering.

        Takes evenly-spaced samples from the dataset to maintain
        temporal structure.
        """
        collected = engine.cached_collect(df)
        n_rows = len(collected)

        if target_size >= n_rows:
            return collected

        # Evenly spaced indices
        step = n_rows / target_size
        indices = [int(i * step) for i in range(target_size)]
        return collected.iloc[indices].reset_index(drop=True)

    def _sample_head(
        self,
        df: Any,
        engine: BaseEngine,
        target_size: int,
    ) -> pd.DataFrame:
        """Take the first N rows (deterministic, no randomness)."""
        collected = engine.cached_collect(df)
        return collected.head(target_size).reset_index(drop=True)

    def _sample_diversity(
        self,
        df: Any,
        engine: BaseEngine,
        target_size: int,
        random_state: int | None,
    ) -> pd.DataFrame:
        """Diversity-preserving sampling for clustering.

        Uses a simple greedy approach: pick points that maximize
        minimum distance to already-selected points.
        Falls back to random if too slow.
        """
        collected = engine.cached_collect(df)
        n_rows = len(collected)

        if target_size >= n_rows:
            return collected

        # For large datasets, use random sampling (diversity is expensive)
        if n_rows > 10_000:
            return collected.sample(n=target_size, random_state=random_state).reset_index(drop=True)

        # Greedy diversity sampling for smaller datasets
        try:
            import numpy as np

            numeric_cols = collected.select_dtypes(include=["number"]).columns
            if len(numeric_cols) == 0:
                return collected.sample(n=target_size, random_state=random_state).reset_index(
                    drop=True
                )

            data = collected[numeric_cols].values
            # Normalize
            stds = np.std(data, axis=0)
            stds[stds == 0] = 1
            data = (data - np.mean(data, axis=0)) / stds

            selected = [0]  # Start with first point
            remaining = set(range(1, n_rows))

            for _ in range(target_size - 1):
                if not remaining:
                    break
                # Find point furthest from any selected point
                best_idx = -1
                best_min_dist = -1
                selected_data = data[selected]

                for idx in remaining:
                    dists = np.linalg.norm(selected_data - data[idx], axis=1)
                    min_dist = np.min(dists)
                    if min_dist > best_min_dist:
                        best_min_dist = min_dist
                        best_idx = idx

                selected.append(best_idx)
                remaining.discard(best_idx)

            return collected.iloc[selected].reset_index(drop=True)
        except ImportError:
            return collected.sample(n=target_size, random_state=random_state).reset_index(drop=True)

    def _sample_anomaly_preserving(
        self,
        df: Any,
        engine: BaseEngine,
        target_size: int,
        target_column: str | None,
        random_state: int | None,
    ) -> pd.DataFrame:
        """Preserve anomaly ratio when sampling for anomaly detection.

        If target_column contains binary labels, stratified sampling
        preserves the anomaly ratio. Otherwise falls back to random.
        """
        collected = engine.cached_collect(df)

        if target_column is None or target_column not in collected.columns:
            return collected.sample(
                n=min(target_size, len(collected)),
                random_state=random_state,
            ).reset_index(drop=True)

        # Check if target is binary (0/1 anomaly labels)
        unique_vals = collected[target_column].unique()
        if len(unique_vals) == 2:
            return self._sample_stratified(df, engine, target_size, target_column, random_state)

        return collected.sample(
            n=min(target_size, len(collected)),
            random_state=random_state,
        ).reset_index(drop=True)


@dataclass
class SamplingResult:
    """Result of a sampling operation.

    Attributes:
        dataframe: The sampled DataFrame (engine-native format).
        metadata: Metadata about the sampling operation.
    """

    dataframe: Any
    metadata: SamplingMetadata

    def __repr__(self) -> str:
        return (
            f"SamplingResult(rows={self.metadata.sample_rows}, "
            f"ratio={self.metadata.sampling_ratio:.1%}, "
            f"method={self.metadata.sampling_method})"
        )
