"""Reports — template-based Markdown report assembly from pipeline outputs.

Public API:
    - ``build_report(state)``: Assemble a Markdown report from WorkflowState.
"""

from phronesisml.ml.reports.builder import build_report

__all__ = ["build_report"]
