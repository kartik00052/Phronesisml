"""Knowledge base store — document ingestion and management.

Manages documents in the Qdrant vector store.  Provides functions for
ingesting pipeline outputs, updating existing documents, and querying
the knowledge base.

Design:
    - Stateless functions that accept a ``QdrantClient`` and
      ``EmbeddingWrapper`` — no global state.
    - Documents are chunked before embedding to stay within model
      context limits.
    - Each document has a ``source`` field for traceability.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Maximum characters per chunk before splitting
_MAX_CHUNK_CHARS = 512


def _chunk_text(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """Split text into chunks of at most *max_chars* characters.

    Splits on paragraph boundaries first, then sentence boundaries,
    then hard-breaks at max_chars for text with no natural breaks.
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                sentences = para.replace(". ", ".\n").split("\n")
                current = ""
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(sent) > max_chars:
                        if current:
                            chunks.append(current)
                            current = ""
                        for i in range(0, len(sent), max_chars):
                            chunks.append(sent[i : i + max_chars])
                    elif len(current) + len(sent) + 1 <= max_chars:
                        current = f"{current} {sent}" if current else sent
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks or []


def _make_doc_id(source: str, chunk_index: int, content: str) -> str:
    """Generate a deterministic document ID from source + content hash."""
    h = hashlib.sha256(f"{source}:{chunk_index}:{content[:100]}".encode()).hexdigest()
    return f"doc_{h[:16]}"


def ingest_text(
    client: Any,
    embedding_wrapper: Any,
    text: str,
    source: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> int:
    """Ingest a text document into the knowledge base.

    Args:
        client: ``QdrantClient`` instance.
        embedding_wrapper: ``EmbeddingWrapper`` instance.
        text: Text content to ingest.
        source: Origin of the document (e.g., "pipeline_output").
        metadata: Additional metadata to attach to each chunk.

    Returns:
        Number of chunks successfully ingested.

    """
    chunks = _chunk_text(text)
    if not chunks:
        return 0

    embeddings = embedding_wrapper.embed(chunks)
    if embeddings is None:
        logger.warning("Failed to generate embeddings for source=%s", source)
        return 0

    payload_meta = metadata or {}
    ids = []
    payloads = []
    for i, chunk in enumerate(chunks):
        doc_id = _make_doc_id(source, i, chunk)
        ids.append(doc_id)
        payloads.append(
            {
                "text": chunk,
                "source": source,
                "chunk_index": i,
                "total_chunks": len(chunks),
                **payload_meta,
            }
        )

    success = client.upsert(ids=ids, vectors=embeddings, payloads=payloads)
    if success:
        logger.info(
            "Ingested %d chunks from source=%s",
            len(chunks),
            source,
        )
        return len(chunks)
    return 0


def ingest_pipeline_state(
    client: Any,
    embedding_wrapper: Any,
    state: Any,
) -> int:
    """Ingest key pipeline state fields as searchable knowledge.

    Extracts human-readable summaries from the pipeline state and
    ingests them for future retrieval.

    Args:
        client: ``QdrantClient`` instance.
        embedding_wrapper: ``EmbeddingWrapper`` instance.
        state: ``WorkflowState`` (or compatible) with pipeline outputs.

    Returns:
        Total chunks ingested.

    """
    total = 0

    target = getattr(state, "target_column", None)
    task_type = getattr(state, "task_type", None)
    if target and task_type:
        text = f"Target column: {target}. Task type: {task_type}."
        total += ingest_text(
            client,
            embedding_wrapper,
            text,
            source="pipeline_target",
            metadata={"stage": "target_detection"},
        )

    eval_report = getattr(state, "evaluation_report", None)
    if isinstance(eval_report, dict) and eval_report.get("metrics"):
        metrics = eval_report["metrics"]
        metrics_str = ", ".join(f"{k}: {v}" for k, v in metrics.items())
        text = f"Model evaluation metrics: {metrics_str}."
        caveat = eval_report.get("ambiguity_caveat")
        if caveat:
            text += f" Caveat: {caveat}"
        total += ingest_text(
            client,
            embedding_wrapper,
            text,
            source="pipeline_evaluation",
            metadata={"stage": "evaluation"},
        )

    best = getattr(state, "best_pipeline", None)
    if isinstance(best, dict):
        model_type = best.get("model_type")
        score = best.get("score") or best.get("mean_cv_score")
        if model_type:
            text = f"Best model: {model_type}."
            if score is not None:
                text += f" Score: {score}."
            total += ingest_text(
                client,
                embedding_wrapper,
                text,
                source="pipeline_model_selection",
                metadata={"stage": "model_selection"},
            )

    explanation = getattr(state, "explanation_report", None)
    if isinstance(explanation, dict) and explanation.get("feature_importance"):
        importance = explanation["feature_importance"]
        top = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
        top_str = ", ".join(f"{k}: {v:.4f}" for k, v in top)
        text = f"Top feature importances: {top_str}."
        total += ingest_text(
            client,
            embedding_wrapper,
            text,
            source="pipeline_explainability",
            metadata={"stage": "explainability"},
        )

    logger.info("Ingested %d total chunks from pipeline state.", total)
    return total
