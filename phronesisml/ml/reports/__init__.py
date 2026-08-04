"""Reports — template-based Markdown report assembly from pipeline outputs.

Public API:
    - ``build_report(state)``: Assemble a Markdown report from WorkflowState.
    - ``build_html_report(state)``: Assemble an HTML report.
    - ``build_json_report(state)``: JSON-serializable report dict.
    - ``build_run_report(state, run_dir)``: run-scoped dataset analysis report.
    - ``write_report(report, path)``: Persist a report to disk.
    - ``report_to_dict(state)``: JSON-able summary of pipeline state.
    - ``render_metrics_table(metrics)``: Markdown table from a metrics dict.
"""

from phronesisml.ml.reports.builder import build_html_report, build_report
from phronesisml.ml.reports.io import (
    build_json_report,
    build_run_report,
    render_metrics_table,
    report_to_dict,
    write_report,
)

__all__ = [
    "build_html_report",
    "build_json_report",
    "build_report",
    "build_run_report",
    "render_metrics_table",
    "report_to_dict",
    "write_report",
]
