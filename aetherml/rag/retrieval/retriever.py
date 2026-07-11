"""RAG retriever — similarity search over the knowledge base.

Queries the Qdrant vector store for context relevant to the current
pipeline state.  Retrieved chunks are returned with scores and can
be filtered by similarity threshold.

Design:
    - Stateless: all inputs come from the caller.
    - Graceful degradation: returns empty list on any failure.
    - Deduplicates results by document ID.
    - Enforces a maximum number of results.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def retrieve_context(
    client: Any,
    embedding_wrapper: Any,
    query: str,
    max_results: int = 5,
    similarity_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """Retrieve knowledge chunks relevant to the query.

    Args:
        client: ``QdrantClient`` instance.
        embedding_wrapper: ``EmbeddingWrapper`` instance.
        query: Query text to search for.
        max_results: Maximum number of chunks to return.
        similarity_threshold: Minimum cosine similarity score.

    Returns:
        List of dicts with ``text``, ``source``, ``score`` keys.
        Empty list on any failure.

    """
    if not query or not query.strip():
        return []

    query_embedding = embedding_wrapper.embed_single(query)
    if query_embedding is None:
        logger.warning("Failed to generate query embedding.")
        return []

    raw_results = client.search(
        query_vector=query_embedding,
        limit=max_results * 2,
    )

    seen_ids: set[str] = set()
    results: list[dict[str, Any]] = []

    for hit in raw_results:
        doc_id = hit.get("id", "")
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)

        score = hit.get("score", 0.0)
        if score < similarity_threshold:
            continue

        payload = hit.get("payload", {})
        text = payload.get("text", "")
        if not text:
            continue

        results.append(
            {
                "text": text,
                "source": payload.get("source", "unknown"),
                "score": score,
            }
        )

        if len(results) >= max_results:
            break

    logger.info(
        "Retrieved %d chunks (threshold=%.2f, query_len=%d).",
        len(results),
        similarity_threshold,
        len(query),
    )
    return results


def build_retrieval_query(
    target_column: str | None = None,
    task_type: str | None = None,
    best_model: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> str:
    """Build a query string from pipeline state for retrieval.

    Constructs a natural-language query that captures the key aspects
    of the current pipeline for effective similarity search.

    Args:
        target_column: Detected target column name.
        task_type: Detected task type.
        best_model: Best model type found.
        metrics: Evaluation metrics dict.

    Returns:
        A query string suitable for embedding.

    """
    parts: list[str] = []

    if task_type:
        parts.append(f"{task_type} task")
    if target_column:
        parts.append(f"predicting {target_column}")
    if best_model:
        parts.append(f"using {best_model}")
    if metrics:
        metric_names = list(metrics.keys())[:3]
        parts.append(f"evaluated with {', '.join(metric_names)}")

    return " ".join(parts) if parts else "machine learning pipeline"
