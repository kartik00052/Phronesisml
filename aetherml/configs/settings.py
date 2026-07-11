"""Minimal configuration for AetherML.

Uses Pydantic ``BaseSettings`` so that values can be overridden via
environment variables or constructor arguments.  This is the minimal
configuration needed to make the Upload → ETL vertical slice runnable.
Full configuration infrastructure is deferred to a later pass.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
            "Memory threshold (bytes) above which Spark is preferred "
            "over in-process engines."
        ),
    )
    max_file_size_bytes: int = Field(
        default=2 * 1024 * 1024 * 1024,  # 2 GB
        description=(
            "Maximum file size (bytes) allowed for upload. "
            "Files exceeding this limit are rejected before loading."
        ),
    )


class LLMConfig(BaseModel):
    """LLM configuration for narrative generation.

    All fields are optional — the LLM integration is entirely opt-in.
    When ``use_narrative`` is False (the default), no LLM calls are made
    and the pipeline runs fully deterministically.
    """

    use_narrative: bool = Field(
        default=False,
        description=(
            "Enable LLM-generated narrative summaries in the report. "
            "When False (default), no LLM calls are made."
        ),
    )
    api_key: str | None = Field(
        default=None,
        description=(
            "API key for the LLM provider. Read from "
            "AETHERML_LLM_API_KEY env var if not set."
        ),
    )
    model_id: str = Field(
        default="gemma-2-9b",
        description="Model identifier for the LLM backend.",
    )
    timeout_seconds: float = Field(
        default=30.0,
        description="Maximum seconds to wait for an LLM API response.",
    )
    max_retries: int = Field(
        default=2,
        description="Maximum number of retries on transient LLM API failures.",
    )
    max_sample_rows: int = Field(
        default=5,
        description="Maximum number of data rows to include in prompts.",
    )
    max_columns: int = Field(
        default=20,
        description="Maximum number of column names to include in prompts.",
    )


class QdrantConfig(BaseModel):
    """Qdrant vector store configuration.

    All fields default to local-mode settings.  Credentials are read
    from environment variables when not explicitly set.
    """

    url: str = Field(
        default="http://localhost:6333",
        description=(
            "Qdrant server URL. Read from AETHERML_QDRANT_URL env var if not set."
        ),
    )
    api_key: str | None = Field(
        default=None,
        description=(
            "API key for Qdrant Cloud. Read from AETHERML_QDRANT_API_KEY env var."
        ),
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
            "Enable RAG context retrieval for LLM narrative generation. "
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


class AetherMLConfig(BaseModel):
    """Top-level SDK configuration."""

    engine: EngineConfig = Field(default_factory=EngineConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)

    model_config = {"extra": "ignore"}
