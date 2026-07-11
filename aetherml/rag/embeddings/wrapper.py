"""Embedding generation wrapper for RAG.

Wraps ``sentence-transformers`` for generating text embeddings used
by the RAG retriever.  The embedding model is loaded lazily and
cached — first call may take a few seconds to download the model.

Design:
    - Lazy import: ``sentence_transformers`` is imported only when
      ``embed()`` is called, so the SDK works without it installed.
    - Graceful degradation: returns ``None`` on failure.
    - Model is cached on the wrapper instance for reuse.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmbeddingWrapper:
    """Thin wrapper around sentence-transformers for embedding generation.

    Args:
        model_name: Name of the sentence-transformers model.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazily load and cache the sentence-transformers model."""
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            msg = (
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            )
            logger.warning(msg)
            raise ImportError(msg) from exc

        self._model = SentenceTransformer(self._model_name)
        logger.info("Loaded embedding model: %s", self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors, or None on failure.
        """
        if not texts:
            return []

        try:
            model = self._get_model()
            embeddings: Any = model.encode(texts, show_progress_bar=False)
            result: list[list[float]] = embeddings.tolist()
            return result
        except Exception as exc:
            logger.warning("Embedding generation failed: %s", exc)
            return None

    def embed_single(self, text: str) -> list[float] | None:
        """Generate an embedding for a single text.

        Args:
            text: String to embed.

        Returns:
            Embedding vector, or None on failure.
        """
        result = self.embed([text])
        if result and len(result) == 1:
            return result[0]
        return None

    @property
    def dimension(self) -> int:
        """Return the embedding dimension for the configured model."""
        try:
            model = self._get_model()
            dim: int = model.get_sentence_embedding_dimension()
            return dim
        except Exception as exc:
            logger.warning(
                "Could not determine embedding dimension, defaulting to 384: %s",
                exc,
            )
            return 384
