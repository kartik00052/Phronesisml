"""Resource estimation for PhronesisML pipeline stages.

Estimates memory, feature count, and runtime requirements BEFORE
expensive operations to enable intelligent sampling decisions.

Estimates produced:
- ``n_rows``: Number of rows in the dataset.
- ``n_cols``: Number of columns.
- ``total_cells``: Total cells (rows x columns).
- ``estimated_memory_mb``: DataFrame memory footprint in MB.
- ``estimated_encoded_features``: Feature count after one-hot encoding.
- ``estimated_encoded_memory_mb``: Memory after encoding.
- ``estimated_train_test_memory_mb``: Memory for train/test split.
- ``estimated_shap_memory_mb``: Memory for SHAP computation.
- ``estimated_runtime_seconds``: Rough runtime estimate.
- ``requires_sampling``: Whether sampling is recommended.
- ``recommended_sample_size``: Suggested sample size if sampling needed.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.engines.base_engine import BaseEngine
from phronesisml.ml.preflight.config import SamplingConfig, SamplingMode

logger = logging.getLogger(__name__)


class ResourceReport:
    """Structured report from resource estimation.

    All fields are populated by ``ResourceEstimator.estimate()``.
    """

    __slots__ = (
        "n_rows",
        "n_cols",
        "total_cells",
        "estimated_memory_mb",
        "estimated_encoded_features",
        "estimated_encoded_memory_mb",
        "estimated_train_test_memory_mb",
        "estimated_shap_memory_mb",
        "estimated_runtime_seconds",
        "requires_sampling",
        "recommended_sample_size",
        "recommended_sample_fraction",
        "sampling_reason",
        "auto_sample_size",
        "available_memory_gb",
    )

    def __init__(
        self,
        n_rows: int = 0,
        n_cols: int = 0,
        total_cells: int = 0,
        estimated_memory_mb: float = 0.0,
        estimated_encoded_features: int = 0,
        estimated_encoded_memory_mb: float = 0.0,
        estimated_train_test_memory_mb: float = 0.0,
        estimated_shap_memory_mb: float = 0.0,
        estimated_runtime_seconds: float = 0.0,
        requires_sampling: bool = False,
        recommended_sample_size: int = 0,
        recommended_sample_fraction: float = 0.0,
        sampling_reason: str = "",
        auto_sample_size: int = 0,
        available_memory_gb: float = 0.0,
    ) -> None:
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.total_cells = total_cells
        self.estimated_memory_mb = estimated_memory_mb
        self.estimated_encoded_features = estimated_encoded_features
        self.estimated_encoded_memory_mb = estimated_encoded_memory_mb
        self.estimated_train_test_memory_mb = estimated_train_test_memory_mb
        self.estimated_shap_memory_mb = estimated_shap_memory_mb
        self.estimated_runtime_seconds = estimated_runtime_seconds
        self.requires_sampling = requires_sampling
        self.recommended_sample_size = recommended_sample_size
        self.recommended_sample_fraction = recommended_sample_fraction
        self.sampling_reason = sampling_reason
        self.auto_sample_size = auto_sample_size
        self.available_memory_gb = available_memory_gb

    def to_dict(self) -> dict[str, Any]:
        """Convert to a serializable dict."""
        return {s: getattr(self, s) for s in self.__slots__}

    def __repr__(self) -> str:
        return (
            f"ResourceReport(rows={self.n_rows}, cols={self.n_cols}, "
            f"mem={self.estimated_memory_mb:.1f}MB, "
            f"encoded_features={self.estimated_encoded_features}, "
            f"requires_sampling={self.requires_sampling})"
        )


class ResourceEstimator:
    """Estimates resource requirements for a dataset before processing.

    Args:
        config: Sampling configuration with thresholds.
        memory_gb: Available memory in GB (auto-detected if not provided).

    Example::

        estimator = ResourceEstimator(SamplingConfig())
        report = estimator.estimate(df, engine, task_type="classification")
        if report.requires_sampling:
            print(f"Recommended sample: {report.recommended_sample_size} rows")
    """

    def __init__(
        self,
        config: SamplingConfig | None = None,
        memory_gb: float | None = None,
    ) -> None:
        self._config = config or SamplingConfig()
        self._memory_gb = memory_gb

    def estimate(
        self,
        df: Any,
        engine: BaseEngine,
        task_type: str | None = None,
        target_column: str | None = None,
        data_profile: dict[str, Any] | None = None,
    ) -> ResourceReport:
        """Estimate resource requirements for the given dataset.

        Args:
            df: Engine-native DataFrame.
            engine: Active computation engine.
            task_type: Detected task type (classification, regression, etc.).
            target_column: Detected target column name.
            data_profile: EDA profile dict (if available).

        Returns:
            A ``ResourceReport`` with all estimates and sampling recommendation.
        """
        from phronesisml.ml.preflight.memory import MemorySafety

        # ── Basic dimensions ─────────────────────────────────────────
        n_rows, n_cols = engine.shape(df)
        total_cells = n_rows * n_cols

        # ── Memory estimate ──────────────────────────────────────────
        try:
            estimated_memory_mb = engine.memory_usage(df) / (1024 * 1024)
        except Exception:
            # Fallback: assume 8 bytes per cell (float64)
            estimated_memory_mb = (total_cells * 8) / (1024 * 1024)

        # ── Available memory ─────────────────────────────────────────
        if self._memory_gb is not None:
            available_gb = self._memory_gb
        else:
            safety = MemorySafety()
            available_gb = safety.get_available_memory_gb()

        # ── Categorical cardinality analysis ─────────────────────────
        profile_categorical = {}
        if data_profile is not None:
            profile_categorical = data_profile.get("categorical_summary", {})

        dtypes = engine.dtypes(df)
        n_numeric = sum(1 for d in dtypes.values() if "int" in d.lower() or "float" in d.lower())

        # Estimate encoded feature count
        estimated_new_features = 0
        max_cardinality = 100  # Cap for estimation
        for col, summary in profile_categorical.items():
            if col == target_column:
                continue
            n_unique = summary.get("n_unique", 0)
            estimated_new_features += min(n_unique, max_cardinality)

        estimated_encoded_features = max(
            n_numeric,
            n_cols + estimated_new_features - 1,  # -1 for target
        )

        # ── Encoded memory estimate ──────────────────────────────────
        # After one-hot encoding, each categorical becomes multiple binary columns
        estimated_encoded_memory_mb = (n_rows * estimated_encoded_features * 8) / (1024 * 1024)

        # ── Train/test memory estimate ───────────────────────────────
        # Roughly 2x for keeping both splits in memory
        estimated_train_test_memory_mb = estimated_encoded_memory_mb * 2.0

        # ── SHAP memory estimate ─────────────────────────────────────
        # SHAP needs: model + feature matrix + SHAP values
        # Conservative: same as train/test + model overhead
        max_shap_samples = 100
        estimated_shap_memory_mb = (
            (max_shap_samples * estimated_encoded_features * 8) / (1024 * 1024)
        ) + 50  # 50 MB overhead for model

        # ── Runtime estimate ─────────────────────────────────────────
        # Rough: 1e-6 seconds per cell for basic operations
        # Feature engineering: ~1e-5 per cell
        # Model training: varies wildly, estimate 10-60 seconds base
        runtime_base = 10.0
        runtime_per_cell = 1e-5
        estimated_runtime_seconds = runtime_base + (total_cells * runtime_per_cell)

        # ── Auto sample size calculation ─────────────────────────────
        auto_sample_size = self._compute_auto_sample_size(n_rows)

        # ── Determine if sampling is required ────────────────────────
        requires_sampling = False
        recommended_sample_size = n_rows
        recommended_sample_fraction = 1.0
        sampling_reason = ""

        config = self._config

        if config.sample_strategy == SamplingMode.DISABLED:
            # User explicitly disabled sampling — check memory only
            if estimated_encoded_memory_mb > config.critical_memory_gb * 1024:
                requires_sampling = True
                recommended_sample_size = auto_sample_size
                recommended_sample_fraction = auto_sample_size / max(n_rows, 1)
                sampling_reason = (
                    f"Dataset requires {estimated_encoded_memory_mb:.0f} MB but "
                    f"critical limit is {config.critical_memory_gb * 1024:.0f} MB. "
                    f"Sampling cannot be fully disabled."
                )
        else:
            # Auto sampling logic
            if n_rows < config.row_threshold_small:
                # Small dataset — process in full
                sampling_reason = (
                    f"Dataset ({n_rows:,} rows) is below threshold "
                    f"({config.row_threshold_small:,})."
                )
            elif estimated_encoded_memory_mb > config.max_memory_gb * 1024:
                # Memory limit exceeded — force sampling
                requires_sampling = True
                recommended_sample_size = min(auto_sample_size, config.sample_size)
                recommended_sample_fraction = recommended_sample_size / max(n_rows, 1)
                sampling_reason = (
                    f"Estimated memory ({estimated_encoded_memory_mb:.0f} MB) exceeds "
                    f"limit ({config.max_memory_gb * 1024:.0f} MB)."
                )
            elif n_rows >= config.row_threshold_large:
                # Large dataset — sample
                requires_sampling = True
                recommended_sample_size = min(config.large_sample_target, config.sample_size)
                recommended_sample_fraction = recommended_sample_size / max(n_rows, 1)
                sampling_reason = (
                    f"Large dataset ({n_rows:,} rows) sampled to "
                    f"{recommended_sample_size:,} rows for efficiency."
                )
            elif n_rows >= config.row_threshold_medium:
                # Medium dataset — sample
                requires_sampling = True
                recommended_sample_size = min(config.medium_sample_target, config.sample_size)
                recommended_sample_fraction = recommended_sample_size / max(n_rows, 1)
                sampling_reason = (
                    f"Medium dataset ({n_rows:,} rows) sampled to "
                    f"{recommended_sample_size:,} rows for efficiency."
                )

            # Ensure minimum sample size
            if requires_sampling and recommended_sample_size < config.min_sample_size:
                recommended_sample_size = config.min_sample_size
                recommended_sample_fraction = recommended_sample_size / max(n_rows, 1)

        report = ResourceReport(
            n_rows=n_rows,
            n_cols=n_cols,
            total_cells=total_cells,
            estimated_memory_mb=round(estimated_memory_mb, 2),
            estimated_encoded_features=estimated_encoded_features,
            estimated_encoded_memory_mb=round(estimated_encoded_memory_mb, 2),
            estimated_train_test_memory_mb=round(estimated_train_test_memory_mb, 2),
            estimated_shap_memory_mb=round(estimated_shap_memory_mb, 2),
            estimated_runtime_seconds=round(estimated_runtime_seconds, 1),
            requires_sampling=requires_sampling,
            recommended_sample_size=recommended_sample_size,
            recommended_sample_fraction=round(recommended_sample_fraction, 4),
            sampling_reason=sampling_reason,
            auto_sample_size=auto_sample_size,
            available_memory_gb=round(available_gb, 2),
        )

        logger.info(
            "Resource estimation: %d rows x %d cols, %.1f MB, "
            "encoded=%d features, requires_sampling=%s",
            n_rows,
            n_cols,
            estimated_memory_mb,
            estimated_encoded_features,
            requires_sampling,
        )

        return report

    def _compute_auto_sample_size(self, n_rows: int) -> int:
        """Compute the auto-recommended sample size based on row count.

        Uses the configured thresholds from ``SamplingConfig``.
        """
        config = self._config

        if n_rows < config.row_threshold_small:
            return n_rows

        if n_rows < config.row_threshold_medium:
            # Scale linearly between small and medium thresholds
            ratio = (n_rows - config.row_threshold_small) / (
                config.row_threshold_medium - config.row_threshold_small
            )
            return int(
                config.row_threshold_small
                + ratio * (config.medium_sample_target - config.row_threshold_small)
            )

        if n_rows < config.row_threshold_large:
            # Scale linearly between medium and large thresholds
            ratio = (n_rows - config.row_threshold_medium) / (
                config.row_threshold_large - config.row_threshold_medium
            )
            return int(
                config.medium_sample_target
                + ratio * (config.large_sample_target - config.medium_sample_target)
            )

        # Very large: use fraction-based sampling
        fraction_based = int(n_rows * config.sample_fraction)
        return max(config.min_sample_size, min(fraction_based, config.sample_size))
