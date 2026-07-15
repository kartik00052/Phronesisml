"""Pipeline stage constants for the simple API.

Each constant defines the ordered list of pipeline stages for a
specific operation.  Imported by ``simple.py`` and ``_result_builders.py``.
"""

from __future__ import annotations

__all__ = [
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

_STAGES_ANALYZE = ["upload", "etl", "validation", "eda"]
_STAGES_CLEAN = ["upload", "etl"]
_STAGES_VALIDATE = ["upload", "etl", "validation"]
_STAGES_DETECT_TARGET = ["upload", "etl", "validation", "eda", "target_detection"]
_STAGES_ENGINEER = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
]
_STAGES_SELECT_MODEL = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
]
_STAGES_EVALUATE = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
]
_STAGES_EXPLAIN = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "explainability",
]
_STAGES_REPORT = [
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
]
_STAGES_TRAIN = [
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
_STAGES_CLUSTER = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "reporting",
]
_STAGES_ANOMALY = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
    "feature_engineering",
    "model_selection",
    "evaluation",
    "reporting",
]
_STAGES_DETECT_TASK = [
    "upload",
    "etl",
    "validation",
    "eda",
    "target_detection",
]
