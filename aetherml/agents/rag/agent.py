"""RAG agent — retrieval-augmented generation for ML decisions.

Orchestrates ``rag.context.get_rag_context()`` to retrieve knowledge
from the Qdrant vector store.  Writes to ``state.rag_context``.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Delegates to ``get_rag_context()`` which handles connection,
  embedding, ingestion, and retrieval.
- Degrades gracefully: if Qdrant is unreachable or embedding model
  is unavailable, ``get_rag_context()`` returns empty results and
  the agent stores them without failing the pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from aetherml.agents.base import AgentResult, Tool

logger = logging.getLogger(__name__)


class RAGAgent:
    """Agent responsible for retrieving knowledge from the vector store.

    Args:
        qdrant_url: Qdrant server URL.
        qdrant_api_key: Optional API key for Qdrant Cloud.
        qdrant_collection: Collection name.
        qdrant_timeout: Timeout for Qdrant operations.
        embedding_model: Sentence-transformers model name.
        max_retrieved_chunks: Maximum chunks to retrieve.
        similarity_threshold: Minimum similarity score.

    """

    name = "rag"
    description = "Retrieve knowledge for augmented ML decisions."

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: str | None = None,
        qdrant_collection: str = "aetherml_knowledge",
        qdrant_timeout: float = 5.0,
        embedding_model: str = "all-MiniLM-L6-v2",
        max_retrieved_chunks: int = 5,
        similarity_threshold: float = 0.3,
    ) -> None:
        self._qdrant_url = qdrant_url
        self._qdrant_api_key = qdrant_api_key
        self._qdrant_collection = qdrant_collection
        self._qdrant_timeout = qdrant_timeout
        self._embedding_model = embedding_model
        self._max_retrieved_chunks = max_retrieved_chunks
        self._similarity_threshold = similarity_threshold

    async def run(self, state: Any) -> AgentResult:
        """Retrieve RAG context for the current pipeline state.

        Reads from: ``state.target_column``, ``state.task_type``,
        ``state.best_pipeline``, ``state.evaluation_report``.

        Writes to: ``state.rag_context``.

        """
        from aetherml.rag.context import get_rag_context

        logger.info("RAG agent: retrieving knowledge context.")

        try:
            result = get_rag_context(
                state=state,
                qdrant_url=self._qdrant_url,
                qdrant_api_key=self._qdrant_api_key,
                qdrant_collection=self._qdrant_collection,
                qdrant_timeout=self._qdrant_timeout,
                embedding_model=self._embedding_model,
                max_retrieved_chunks=self._max_retrieved_chunks,
                similarity_threshold=self._similarity_threshold,
            )

            logger.info(
                "RAG agent: retrieved %d chunks (status=%s).",
                len(result.get("chunks", [])),
                result.get("status", "unknown"),
            )

            return AgentResult(
                success=True,
                data={"rag_context": result},
                metadata={
                    "chunks_retrieved": len(result.get("chunks", [])),
                    "status": result.get("status", "unknown"),
                },
            )

        except Exception as exc:
            msg = f"RAG retrieval failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="retrieve_knowledge",
                description="Retrieve relevant knowledge chunks from the vector store.",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Optional custom query override.",
                    },
                },
            ),
        ]
