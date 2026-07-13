"""Reporting agent — assembles a Markdown pipeline report.

This is the final aggregation agent in the pipeline.  It reads outputs
from all upstream agents (Validation, EDA, Target Detection, Feature
Engineering, Model Selection, Evaluation, Explainability) and assembles
a human-readable Markdown summary.

Responsibilities:
- Aggregate outputs from all upstream agents.
- Handle partial pipelines gracefully (missing sections get stubs).
- Propagate ambiguity caveats from Target Detection and Evaluation
  into the report notes.
- Produce a Markdown string stored in ``WorkflowState.final_report``.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Template-based: structured sections use pure string formatting.
- The Reporting agent is the natural checkpoint for validating that
  ``WorkflowState`` carries everything correctly end-to-end.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesisml.agents.base import AgentResult, Tool
from phronesisml.ml.reports.builder import build_report

logger = logging.getLogger(__name__)


class ReportingAgent:
    """Agent responsible for assembling the final pipeline report.

    Consumes outputs from all upstream agents and produces a
    Markdown-formatted report.  Handles partial pipelines gracefully.
    """

    name = "reporting"
    description = "Assemble a Markdown pipeline report from all upstream agent outputs."

    async def run(self, state: Any) -> AgentResult:
        """Build the final report from WorkflowState.

        Reads from: ``state.validation_report``, ``state.data_profile``,
        ``state.target_column``, ``state.task_type``,
        ``state.target_detection_confidence``, ``state.ambiguity_reason``,
        ``state.feature_names``, ``state.candidate_models``,
        ``state.best_pipeline``, ``state.evaluation_report``,
        ``state.explanation_report``, ``state.run_id``, ``state.status``

        Returns: dict with ``final_report``.
        """
        # ── Build the structured report ──────────────────────────────
        try:
            report_text = build_report(state)
        except Exception as exc:
            msg = f"Report assembly failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        logger.info(
            "Report assembled: %d characters, %d lines.",
            len(report_text),
            report_text.count("\n") + 1,
        )

        return AgentResult(
            success=True,
            data={"final_report": report_text},
            metadata={
                "report_length": len(report_text),
                "report_lines": report_text.count("\n") + 1,
            },
        )

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="build_report",
                description="Assemble a Markdown report from pipeline outputs.",
                parameters={},
            ),
        ]
