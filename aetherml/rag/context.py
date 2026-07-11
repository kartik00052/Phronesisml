"""RAG context orchestration — retrieval entry point for agents.

Provides a single function for agents (primarily the Reporting agent)
to retrieve RAG context.  Handles the full lifecycle: client
initialisation, embedding model loading, pipeline state ingestion,
query construction, and retrieval.

Design:
    - Single entry point: ``get_rag_context()`` does everything.
    - Graceful degradation: if Qdrant is unreachable, embedding model
      missing, or any step fails, returns an empty context dict.
    - Lazy imports: Qdrant client and embedding model are imported
      only when this function is called.
    - Credentials never logged or stored beyond the client instance.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Module-level caches for expensive client/model instances
_qdrant_client_cache: dict[str, Any] = {}
_embedding_wrapper_cache: dict[str, Any] = {}


def get_rag_context(
    state: Any,
    qdrant_url: str = "http://localhost:6333",
    qdrant_api_key: str | None = None,
    qdrant_collection: str = "aetherml_knowledge",
    qdrant_timeout: float = 5.0,
    embedding_model: str = "all-MiniLM-L6-v2",
    max_retrieved_chunks: int = 5,
    similarity_threshold: float = 0.3,
) -> dict[str, Any]:
    """Retrieve RAG context for the current pipeline state.

    This is the main entry point for RAG retrieval.  It:
    1. Connects to Qdrant (degrades if unreachable).
    2. Loads the embedding model (degrades if unavailable).
    3. Ingests current pipeline state into the knowledge base.
    4. Constructs a query from the pipeline state.
    5. Retrieves relevant context chunks.

    Args:
        state: ``WorkflowState`` (or compatible) with pipeline outputs.
        qdrant_url: Qdrant server URL.
        qdrant_api_key: Optional API key for Qdrant Cloud.
        qdrant_collection: Collection name.
        qdrant_timeout: Timeout for Qdrant operations.
        embedding_model: Sentence-transformers model name.
        max_retrieved_chunks: Maximum chunks to retrieve.
        similarity_threshold: Minimum similarity score.

    Returns:
        Dict with keys: ``chunks`` (list), ``query`` (str),
        ``status`` (str).  Empty chunks on any failure.

    """
    result: dict[str, Any] = {
        "chunks": [],
        "query": "",
        "status": "not_attempted",
    }

    # ── Connect to Qdrant ───────────────────────────────────────────
    cache_key = f"{qdrant_url}:{qdrant_collection}"
    try:
        if cache_key not in _qdrant_client_cache:
            from aetherml.database.qdrant.client import QdrantClient

            client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                collection_name=qdrant_collection,
                timeout_seconds=qdrant_timeout,
            )
            client.ensure_collection()
            _qdrant_client_cache[cache_key] = client
        client = _qdrant_client_cache[cache_key]
    except Exception as exc:
        logger.warning("Qdrant connection failed — RAG disabled: %s", exc)
        result["status"] = "failed: qdrant_unreachable"
        return result

    # ── Load embedding model ────────────────────────────────────────
    try:
        if embedding_model not in _embedding_wrapper_cache:
            from aetherml.rag.embeddings.wrapper import EmbeddingWrapper

            _embedding_wrapper_cache[embedding_model] = EmbeddingWrapper(model_name=embedding_model)
        embedding_wrapper = _embedding_wrapper_cache[embedding_model]
    except Exception as exc:
        logger.warning("Embedding model load failed — RAG disabled: %s", exc)
        result["status"] = "failed: embedding_model_unavailable"
        return result

    # ── Ingest pipeline state ───────────────────────────────────────
    try:
        from aetherml.rag.knowledge_base.store import ingest_pipeline_state

        ingest_pipeline_state(client, embedding_wrapper, state)
    except Exception as exc:
        logger.warning("Pipeline state ingestion failed: %s", exc)

    # ── Build query and retrieve ────────────────────────────────────
    try:
        from aetherml.rag.retrieval.retriever import (
            build_retrieval_query,
            retrieve_context,
        )

        query = build_retrieval_query(
            target_column=getattr(state, "target_column", None),
            task_type=getattr(state, "task_type", None),
            best_model=(
                getattr(state, "best_pipeline", {}).get("model_type")
                if isinstance(getattr(state, "best_pipeline", None), dict)
                else None
            ),
            metrics=(
                getattr(state, "evaluation_report", {}).get("metrics")
                if isinstance(getattr(state, "evaluation_report", None), dict)
                else None
            ),
        )
        result["query"] = query

        chunks = retrieve_context(
            client=client,
            embedding_wrapper=embedding_wrapper,
            query=query,
            max_results=max_retrieved_chunks,
            similarity_threshold=similarity_threshold,
        )
        result["chunks"] = chunks
        result["status"] = "success" if chunks else "empty"

    except Exception as exc:
        logger.warning("RAG retrieval failed: %s", exc)
        result["status"] = f"failed: {exc}"

    logger.info(
        "RAG context: %d chunks retrieved, status=%s.",
        len(result["chunks"]),
        result["status"],
    )
    return result
