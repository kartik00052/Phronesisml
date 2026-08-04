"""Pipeline stage constants for the simple API.

Single source of truth for the canonical pipeline stage order:
``_FULL_PIPELINE_STAGES`` defines the ordered 11-stage pipeline.
Every ``_STAGES_*`` constant is derived from it, and both
``workflow.graph.PIPELINE_ORDER`` and ``run_pipeline`` re-export it.
"""

from __future__ import annotations

__all__ = [
    "_FULL_PIPELINE_STAGES",
    "_STAGES_ANALYZE",
    "_STAGES_CLEAN",
    "_STAGES_VALIDATE",
    "_STAGES_DETECT_TARGET",
    "_STAGES_ENGINEER",
    "_STAGES_SELECT_MODEL",
    "_STAGES_EVALUATE",
    "_STAGES_EXPLAIN",
    "_STAGES_REPORT",
    "_STAGES_TRAIN",
    "_STAGES_CLUSTER",
    "_STAGES_ANOMALY",
    "_STAGES_DETECT_TASK",
]

# Canonical pipeline order — stages must appear in this sequence.
# Target detection must run before feature engineering (FE needs to
# know which column is the target to exclude it from transforms).
_FULL_PIPELINE_STAGES: list[str] = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "explainability",
    "reporting",
    "storage",
]

_STAGES_ANALYZE = _FULL_PIPELINE_STAGES[:4]
_STAGES_CLEAN = _FULL_PIPELINE_STAGES[:2]
_STAGES_VALIDATE = _FULL_PIPELINE_STAGES[:3]
_STAGES_DETECT_TARGET = _FULL_PIPELINE_STAGES[:5]
_STAGES_ENGINEER = _FULL_PIPELINE_STAGES[:6]
_STAGES_SELECT_MODEL = _FULL_PIPELINE_STAGES[:8]
_STAGES_EVALUATE = _STAGES_SELECT_MODEL
_STAGES_EXPLAIN = _FULL_PIPELINE_STAGES[:9]
_STAGES_REPORT = _FULL_PIPELINE_STAGES[:10]
_STAGES_TRAIN = list(_FULL_PIPELINE_STAGES)
_STAGES_CLUSTER = [
    stage for stage in _FULL_PIPELINE_STAGES if stage not in {"explainability", "storage"}
]
_STAGES_ANOMALY = _STAGES_CLUSTER
_STAGES_DETECT_TASK = _FULL_PIPELINE_STAGES[:5]
