"""Minimal configuration for AetherML.

Uses Pydantic ``BaseSettings`` so that values can be overridden via
environment variables or constructor arguments.  This is the minimal
configuration needed to make the Upload → ETL vertical slice runnable.
Full configuration infrastructure is deferred to a later pass.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "AetherMLConfig",
    "DataConfig",
    "EngineConfig",
    "FeatureSelectionConfig",
    "QdrantConfig",
    "RAGConfig",
]


class EngineConfig(BaseModel):
    """Engine selection preferences."""

    preferred: str | None = Field(
        default=None,
        description="Force a specific engine ('pandas', 'polars', 'spark'). None = auto-select.",
    )
    spark_master: str = Field(
        default="local[*]",
        description="Spark master URL (only used when Spark is selected).",
    )


class DataConfig(BaseModel):
    """Data loading defaults."""

    default_format: str = Field(
        default="auto",
        description=(
            "Default file format when not inferred from extension "
            "('auto', 'csv', 'parquet', 'json')."
        ),
    )
    max_memory_bytes: int = Field(
        default=500 * 1024 * 1024,  # 500 MB
        description=(
            "Memory threshold (bytes) above which Spark is preferred over in-process engines."
        ),
    )
    max_file_size_bytes: int = Field(
        default=2 * 1024 * 1024 * 1024,  # 2 GB
        description=(
            "Maximum file size (bytes) allowed for upload. "
            "Files exceeding this limit are rejected before loading."
        ),
    )


class QdrantConfig(BaseModel):
    """Qdrant vector store configuration.

    All fields default to local-mode settings.  Credentials are read
    from environment variables when not explicitly set.
    """

    url: str = Field(
        default="http://localhost:6333",
        description=("Qdrant server URL. Read from AETHERML_QDRANT_URL env var if not set."),
    )
    api_key: str | None = Field(
        default=None,
        description=("API key for Qdrant Cloud. Read from AETHERML_QDRANT_API_KEY env var."),
    )
    collection_name: str = Field(
        default="aetherml_knowledge",
        description="Name of the Qdrant collection to use.",
    )
    timeout_seconds: float = Field(
        default=5.0,
        description="Maximum seconds to wait for a Qdrant operation.",
    )


class RAGConfig(BaseModel):
    """RAG (Retrieval-Augmented Generation) configuration."""

    enabled: bool = Field(
        default=False,
        description=(
            "Enable RAG context retrieval for enhanced reporting. "
            "When False (default), no retrieval is performed."
        ),
    )
    max_retrieved_chunks: int = Field(
        default=5,
        description="Maximum number of knowledge chunks to retrieve per query.",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers model for embedding generation.",
    )
    similarity_threshold: float = Field(
        default=0.3,
        description="Minimum cosine similarity to include a retrieved chunk.",
    )


class FeatureSelectionConfig(BaseModel):
    """Feature selection thresholds for Feature Engineering.

    These control the variance-threshold and correlation-based feature
    selection in ``_select_features()``.  Adjusting these allows tuning
    for datasets where the defaults are too aggressive or too lenient.
    """

    variance_threshold: float = Field(
        default=0.01,
        description=(
            "Features with variance below this are dropped. Lower values retain more features."
        ),
    )
    correlation_threshold: float = Field(
        default=0.05,
        description=(
            "Features with absolute correlation to the target below "
            "this are dropped (supervised selection).  Lower values "
            "retain more features."
        ),
    )
    min_features: int = Field(
        default=1,
        description=(
            "Minimum number of features to retain.  Prevents feature "
            "selection from dropping ALL features on small datasets."
        ),
    )


class AetherMLConfig(BaseModel):
    """Top-level SDK configuration."""

    engine: EngineConfig = Field(default_factory=EngineConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    feature_selection: FeatureSelectionConfig = Field(default_factory=FeatureSelectionConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)

    model_config = {"extra": "ignore"}
