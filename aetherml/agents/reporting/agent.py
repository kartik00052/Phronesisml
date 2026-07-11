"""Reporting agent — assembles a Markdown pipeline report.

This is the final aggregation agent in the pipeline.  It reads outputs
from all upstream agents (Validation, EDA, Target Detection, Feature
Engineering, Model Selection, Evaluation, Explainability) and assembles
a human-readable Markdown summary.

When LLM narrative generation is enabled (``use_llm_narrative=True`` in
``LLMConfig``), the agent optionally retrieves RAG context from the
knowledge base (if ``RAGConfig.enabled=True``), then generates a
natural-language narrative summary via the ``llm/`` module and appends
it to the report.  The structured data sections remain the source of
truth — the narrative is additive framing, not a replacement.

Responsibilities:
- Aggregate outputs from all upstream agents.
- Handle partial pipelines gracefully (missing sections get stubs).
- Propagate ambiguity caveats from Target Detection and Evaluation
  into the report notes.
- Produce a Markdown string stored in ``WorkflowState.final_report``.
- Optionally retrieve RAG context and generate LLM narrative with
  graceful degradation on failure.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Template-based: structured sections use pure string formatting.
- RAG retrieval is optional and happens BEFORE the LLM call.
- LLM-narrative is optional and additive: when enabled, it layers a
  narrative section on top of the structured report.
- Graceful degradation: if RAG or LLM calls fail, the report is still
  produced with a stub narrative, and the failure is visible in the
  result metadata.
- The Reporting agent is the natural checkpoint for validating that
  ``WorkflowState`` carries everything correctly end-to-end.
"""

from __future__ import annotations

import logging
from typing import Any

from aetherml.agents.base import AgentResult, Tool
from aetherml.configs.settings import LLMConfig, QdrantConfig, RAGConfig
from aetherml.ml.reports.builder import build_report

logger = logging.getLogger(__name__)


class ReportingAgent:
    """Agent responsible for assembling the final pipeline report.

    Consumes outputs from all upstream agents and produces a
    Markdown-formatted report.  Handles partial pipelines gracefully.

    Args:
        llm_config: Optional LLM configuration.  When provided with
            ``use_narrative=True``, the agent generates a narrative
            summary via the LLM and appends it to the report.
        rag_config: Optional RAG configuration.  When provided with
            ``enabled=True`` and LLM narrative is also enabled, the
            agent retrieves knowledge context before calling the LLM.
        qdrant_config: Optional Qdrant configuration for vector store
            connection details.
    """

    name = "reporting"
    description = "Assemble a Markdown pipeline report from all upstream agent outputs."

    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        rag_config: RAGConfig | None = None,
        qdrant_config: QdrantConfig | None = None,
    ) -> None:
        self._llm_config = llm_config
        self._rag_config = rag_config
        self._qdrant_config = qdrant_config

    async def run(self, state: Any) -> AgentResult:
        """Build the final report from WorkflowState.

        Reads from: ``state.validation_report``, ``state.data_profile``,
        ``state.target_column``, ``state.task_type``,
        ``state.target_detection_confidence``, ``state.ambiguity_reason``,
        ``state.feature_names``, ``state.candidate_models``,
        ``state.best_pipeline``, ``state.evaluation_report``,
        ``state.explanation_report``, ``state.run_id``, ``state.status``

        Returns: dict with ``final_report`` and optionally
        ``narrative_generation_status`` and ``rag_retrieval_status``.
        """
        narrative = None
        narrative_status = "disabled"
        rag_status = "disabled"

        # ── RAG retrieval (optional, before LLM) ────────────────────
        rag_context: dict[str, Any] | None = None
        if (
            self._rag_config
            and self._rag_config.enabled
            and self._llm_config
            and self._llm_config.use_narrative
        ):
            rag_context, rag_status = await self._retrieve_rag_context(state)

        # ── LLM narrative generation (optional) ──────────────────────
        if self._llm_config and self._llm_config.use_narrative:
            narrative, narrative_status = await self._generate_narrative(
                state, rag_context=rag_context,
            )

        # ── Build the structured report ──────────────────────────────
        try:
            report_text = build_report(state, narrative=narrative)
        except Exception as exc:
            msg = f"Report assembly failed: {exc}"
            logger.exception(msg)
            return AgentResult(success=False, error=msg)

        logger.info(
            "Report assembled: %d characters, %d lines.",
            len(report_text),
            report_text.count("\n") + 1,
        )

        data: dict[str, Any] = {"final_report": report_text}
        metadata: dict[str, Any] = {
            "report_length": len(report_text),
            "report_lines": report_text.count("\n") + 1,
            "narrative_generation_status": narrative_status,
            "rag_retrieval_status": rag_status,
        }

        return AgentResult(
            success=True,
            data=data,
            metadata=metadata,
        )

    async def _retrieve_rag_context(
        self, state: Any
    ) -> tuple[dict[str, Any] | None, str]:
        """Retrieve RAG context from the knowledge base.

        Returns:
            A tuple of (rag_context_dict, status_string).
            On failure, returns (None, "failed: <reason>").
        """
        try:
            from aetherml.rag.context import get_rag_context
        except ImportError as exc:
            msg = f"RAG module not available: {exc}"
            logger.warning(msg)
            return None, f"failed: {msg}"

        qdrant = self._qdrant_config or QdrantConfig()
        rag = self._rag_config or RAGConfig()

        try:
            context = get_rag_context(
                state,
                qdrant_url=qdrant.url,
                qdrant_api_key=qdrant.api_key,
                qdrant_collection=qdrant.collection_name,
                qdrant_timeout=qdrant.timeout_seconds,
                embedding_model=rag.embedding_model,
                max_retrieved_chunks=rag.max_retrieved_chunks,
                similarity_threshold=rag.similarity_threshold,
            )
            return context, context.get("status", "unknown")

        except Exception as exc:
            msg = f"RAG retrieval failed: {exc}"
            logger.warning(msg)
            return None, f"failed: {exc}"

    async def _generate_narrative(
        self,
        state: Any,
        rag_context: dict[str, Any] | None = None,
    ) -> tuple[str | None, str]:
        """Generate an LLM narrative summary.

        Args:
            state: Pipeline state with upstream outputs.
            rag_context: Optional RAG context dict with ``chunks`` and
                ``query`` keys.

        Returns:
            A tuple of (narrative_text, status_string).
            On failure, returns (None, "failed: <reason>").
        """
        try:
            from aetherml.llm.gemma.client import GemmaClient
            from aetherml.llm.parser.response import (
                parse_response,
                validate_response_is_text,
            )
            from aetherml.llm.prompts.narrative import build_narrative_prompt
        except ImportError as exc:
            msg = f"LLM module not available: {exc}"
            logger.warning(msg)
            return None, f"failed: {msg}"

        if self._llm_config is None:
            return None, "failed: LLM config not provided"

        client = GemmaClient(self._llm_config)

        try:
            prompt = build_narrative_prompt(
                state,
                max_sample_rows=self._llm_config.max_sample_rows,
                max_columns=self._llm_config.max_columns,
                rag_context=rag_context,
            )
            raw_response = await client.generate(prompt)
            parsed = parse_response(raw_response)

            if not validate_response_is_text(parsed):
                msg = "LLM response failed safety validation."
                logger.warning(msg)
                return None, f"failed: {msg}"

            if not parsed.strip():
                msg = "LLM returned empty narrative."
                logger.warning(msg)
                return None, f"failed: {msg}"

            logger.info("LLM narrative generated: %d characters.", len(parsed))
            return parsed, "success"

        except Exception as exc:
            msg = f"LLM narrative generation failed: {exc}"
            logger.warning(msg)
            return None, f"failed: {exc}"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="build_report",
                description="Assemble a Markdown report from pipeline outputs.",
                parameters={},
            )
        ]
