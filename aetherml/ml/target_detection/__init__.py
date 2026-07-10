"""Target detection — heuristic identification of the target column and task type.

``ml.target_detection.detector`` contains the real detection logic,
called by the Target Detection agent.
"""

from aetherml.ml.target_detection.detector import (
    AMBIGUITY_THRESHOLD,
    detect_target,
)

__all__ = ["AMBIGUITY_THRESHOLD", "detect_target"]
