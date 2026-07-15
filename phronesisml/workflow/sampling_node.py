"""Sampling node — applies pre-flight sampling before expensive stages.

This node runs before EDA, Feature Engineering, Target Detection,
Model Selection, and Explainability to prevent OOM and excessive runtime.

The node:
1. Estimates resource requirements using ``ResourceEstimator``.
   Result is cached in ``WorkflowState.resource_report`` — subsequent
   nodes reuse the cached estimate without re-computing.
2. Applies sampling if needed using ``Sampler``.
3. Stores the sampled DataFrame in ``WorkflowState.processed_data``
   (or ``validated_data``) and sampling metadata in ``WorkflowState.sampling_metadata``.

The original dataset remains unchanged — only the working DataFrame
is sampled.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.engines.base_engine import BaseEngine
from phronesisml.ml.preflight.config import SamplingConfig
from phronesisml.ml.preflight.estimator import ResourceEstimator
from phronesisml.ml.preflight.sampler import Sampler

logger = logging.getLogger(__name__)


def create_sampling_node(
    engine: BaseEngine,
    config: SamplingConfig | None = None,
) -> Any:
    """Create a LangGraph node that applies pre-flight sampling.

    Args:
        engine: The active computation engine.
        config: Sampling configuration.  If ``None``, uses defaults.

    Returns:
        An async callable suitable for use as a LangGraph node.

    """

    async def sampling_node(state: Any) -> dict[str, Any]:
        """Apply pre-flight sampling to the working DataFrame.

        Reads from: ``state.processed_data`` or ``state.validated_data``
        Writes to: ``state.processed_data`` (sampled version),
            ``state.sampling_metadata``, ``state.resource_report``
        """
        # ── Resolve input DataFrame ──────────────────────────────────
        df = state.processed_data if state.processed_data is not None else state.validated_data
        if df is None:
            logger.debug("No data to sample — skipping sampling node.")
            return {}

        # ── Check if sampling is disabled ────────────────────────────
        effective_config = config or SamplingConfig()
        if effective_config.sample_strategy == "disabled":
            logger.debug("Sampling is disabled — skipping.")
            return {}

        # ── Check if we already sampled (idempotency) ────────────────
        existing_metadata = getattr(state, "sampling_metadata", None)
        if existing_metadata and existing_metadata.get("was_sampled"):
            logger.debug("Data already sampled — skipping.")
            return {}

        # ── Use cached resource report if available ──────────────────
        resource_dict = getattr(state, "resource_report", None)
        if resource_dict is not None:
            logger.debug("Reusing cached resource report — skipping estimation.")
            # Check if cached report says sampling is needed
            if not resource_dict.get("requires_sampling", False):
                return {"resource_report": resource_dict}
            # If sampling was already recommended and data hasn't changed,
            # skip re-estimation but still apply sampling
            cached_sample_size = resource_dict.get("recommended_sample_size")
        else:
            cached_sample_size = None

        # ── Resolve task type and target column ──────────────────────
        task_type = getattr(state, "task_type", None)
        target_column = getattr(state, "target_column", None)
        data_profile = getattr(state, "data_profile", None)

        # ── Resource estimation (only if not cached) ─────────────────
        if resource_dict is None:
            estimator = ResourceEstimator(effective_config)
            report = estimator.estimate(
                df,
                engine,
                task_type=task_type,
                target_column=target_column,
                data_profile=data_profile,
            )
            resource_dict = report.to_dict()

            if not report.requires_sampling:
                logger.info(
                    "No sampling needed: %d rows, %.1f MB, %d features. %s",
                    report.n_rows,
                    report.estimated_memory_mb,
                    report.estimated_encoded_features,
                    report.sampling_reason,
                )
                return {"resource_report": resource_dict}

            sample_size = report.recommended_sample_size
            sample_fraction = report.recommended_sample_fraction
        else:
            sample_size = cached_sample_size
            sample_fraction = resource_dict.get("recommended_sample_fraction", 0.1)

        # ── Apply sampling ───────────────────────────────────────────
        logger.info(
            "Pre-flight: sampling %d rows → %d rows using strategy '%s'",
            len(df),
            sample_size,
            effective_config.sample_strategy,
        )

        sampler = Sampler(effective_config)
        result = sampler.sample(
            df,
            engine,
            task_type=task_type,
            target_column=target_column,
            sample_size=sample_size,
            sample_fraction=sample_fraction,
        )

        # ── Store results ────────────────────────────────────────────
        state_update: dict[str, Any] = {
            "processed_data": result.dataframe,
            "sampling_metadata": result.metadata.to_dict(),
            "resource_report": resource_dict,
        }

        logger.info(
            "Sampling complete: %d → %d rows (%.1f%%) using %s.",
            result.metadata.original_rows,
            result.metadata.sample_rows,
            result.metadata.sampling_ratio * 100,
            result.metadata.sampling_method,
        )

        return state_update

    sampling_node.__name__ = "node_sampling"
    sampling_node.__doc__ = "LangGraph node for pre-flight sampling."
    return sampling_node
