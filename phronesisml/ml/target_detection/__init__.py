"""Target detection — heuristic identification of the target column and task type.

``ml.target_detection.detector`` contains the real detection logic,
called by the Target Detection agent.  ``ml.target_detection.analysis``
adds engine-light quality/balance reports for a known target.
"""

from phronesisml.ml.target_detection.analysis import (
    class_balance_report,
    target_quality_report,
)
from phronesisml.ml.target_detection.detector import (
    AMBIGUITY_THRESHOLD,
    detect_target,
    validate_target_safety,
)

__all__ = [
    "AMBIGUITY_THRESHOLD",
    "class_balance_report",
    "detect_target",
    "target_quality_report",
    "validate_target_safety",
]
