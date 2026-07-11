"""Qdrant vector store client — thin adapter with graceful degradation.

This module wraps the ``qdrant-client`` library, providing a minimal
interface for collection management, upsert, and similarity search.
All methods degrade gracefully — connection failures return empty results
rather than raising, so the pipeline can continue without RAG context.

Design:
    - Thin wrapper: no domain logic beyond connection management.
    - Lazy import: ``qdrant_client`` is imported only when methods are
      called, so the SDK works without ``qdrant-client`` installed.
    - Credentials via config or environment variables.
    - All timeouts are configurable via ``QdrantConfig``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class QdrantClient:
    """Thin wrapper around the Qdrant HTTP client.

    Args:
        url: Qdrant server URL.  Falls back to ``AETHERML_QDRANT_URL``
            env var.
        api_key: Optional API key for Qdrant Cloud.  Falls back to
            ``AETHERML_QDRANT_API_KEY`` env var.
        collection_name: Name of the collection to operate on.
        timeout_seconds: Timeout for Qdrant operations.
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str | None = None,
        collection_name: str = "aetherml_knowledge",
        timeout_seconds: float = 5.0,
    ) -> None:
        self._url = url or os.environ.get("AETHERML_QDRANT_URL", "http://localhost:6333")
        self._api_key = api_key or os.environ.get("AETHERML_QDRANT_API_KEY")
        self._collection_name = collection_name
        self._timeout_seconds = timeout_seconds
        self._client: Any = None

    def close(self) -> None:
        """Release the underlying Qdrant connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:
                logger.debug("Qdrant connection close failed: %s", exc)
            self._client = None

    def __enter__(self) -> QdrantClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _get_client(self) -> Any:
        """Lazily initialise and return the underlying Qdrant client."""
        if self._client is not None:
            return self._client

        try:
            from qdrant_client import QdrantClient as _QdrantClient
        except ImportError as exc:
            msg = (
                "qdrant-client is not installed. "
                "Install it with: pip install qdrant-client"
            )
            logger.warning(msg)
            raise ImportError(msg) from exc

        kwargs: dict[str, Any] = {
            "url": self._url,
            "timeout": self._timeout_seconds,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key

        self._client = _QdrantClient(**kwargs)
        return self._client

    def ensure_collection(self, dimension: int = 384) -> bool:
        """Create the collection if it does not exist.

        Args:
            dimension: Vector dimension for the collection.

        Returns:
            True if the collection exists or was created successfully.
        """
        try:
            client = self._get_client()
            from qdrant_client.models import Distance, VectorParams

            collections = client.get_collections().collections
            existing = {c.name for c in collections}

            if self._collection_name not in existing:
                client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(
                        size=dimension,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection: %s", self._collection_name)

            return True

        except ImportError:
            raise
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.warning("Qdrant ensure_collection failed (infra): %s", exc)
            return False
        except Exception as exc:
            logger.warning("Qdrant ensure_collection failed: %s", exc)
            return False

    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> bool:
        """Insert or update points in the collection.

        Args:
            ids: Point IDs (strings).
            vectors: Embedding vectors.
            payloads: Metadata payloads for each point.

        Returns:
            True if upsert succeeded.
        """
        try:
            client = self._get_client()
            from qdrant_client.models import PointStruct

            points = [
                PointStruct(id=i, vector=v, payload=p)
                for i, v, p in zip(ids, vectors, payloads, strict=True)
            ]

            client.upsert(
                collection_name=self._collection_name,
                points=points,
            )
            return True

        except ImportError:
            raise
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.warning("Qdrant upsert failed (infra): %s", exc)
            return False
        except Exception as exc:
            logger.warning("Qdrant upsert failed: %s", exc)
            return False

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors in the collection.

        Args:
            query_vector: The query embedding.
            limit: Maximum number of results.

        Returns:
            List of result dicts with ``id``, ``score``, and ``payload``.
            Returns an empty list on any failure.
        """
        try:
            client = self._get_client()
            results = client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                limit=limit,
            )
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload or {},
                }
                for hit in results
            ]

        except ImportError:
            raise
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.warning("Qdrant search failed (infra): %s", exc)
            return []
        except Exception as exc:
            logger.warning("Qdrant search failed: %s", exc)
            return []

    def delete_collection(self) -> bool:
        """Delete the collection.

        Returns:
            True if deletion succeeded.
        """
        try:
            client = self._get_client()
            client.delete_collection(collection_name=self._collection_name)
            return True

        except ImportError:
            raise
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.warning("Qdrant delete_collection failed (infra): %s", exc)
            return False
        except Exception as exc:
            logger.warning("Qdrant delete_collection failed: %s", exc)
            return False
