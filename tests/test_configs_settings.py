"""Unit tests for AetherML configuration settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aetherml.configs.settings import (
    AetherMLConfig,
    DataConfig,
    EngineConfig,
    QdrantConfig,
    RAGConfig,
)


class TestEngineConfigDefaults:
    def test_default_preferred_is_none(self) -> None:
        cfg = EngineConfig()
        assert cfg.preferred is None

    def test_default_spark_master(self) -> None:
        cfg = EngineConfig()
        assert cfg.spark_master == "local[*]"

    def test_custom_preferred(self) -> None:
        cfg = EngineConfig(preferred="polars")
        assert cfg.preferred == "polars"

    def test_custom_spark_master(self) -> None:
        cfg = EngineConfig(spark_master="spark://host:7077")
        assert (
            cfg.spark_master == "spark://spark://host:7077"
            or cfg.spark_master == "spark://host:7077"
        )


class TestDataConfigDefaults:
    def test_default_format(self) -> None:
        cfg = DataConfig()
        assert cfg.default_format == "auto"

    def test_default_max_memory_bytes(self) -> None:
        cfg = DataConfig()
        assert cfg.max_memory_bytes == 500 * 1024 * 1024

    def test_default_max_file_size_bytes(self) -> None:
        cfg = DataConfig()
        assert cfg.max_file_size_bytes == 2 * 1024 * 1024 * 1024


class TestQdrantConfigDefaults:
    def test_default_url(self) -> None:
        cfg = QdrantConfig()
        assert cfg.url == "http://localhost:6333"

    def test_default_api_key_is_none(self) -> None:
        cfg = QdrantConfig()
        assert cfg.api_key is None

    def test_default_collection_name(self) -> None:
        cfg = QdrantConfig()
        assert cfg.collection_name == "aetherml_knowledge"

    def test_default_timeout(self) -> None:
        cfg = QdrantConfig()
        assert cfg.timeout_seconds == 5.0


class TestRAGConfigDefaults:
    def test_default_enabled(self) -> None:
        cfg = RAGConfig()
        assert cfg.enabled is False

    def test_default_max_retrieved_chunks(self) -> None:
        cfg = RAGConfig()
        assert cfg.max_retrieved_chunks == 5

    def test_default_embedding_model(self) -> None:
        cfg = RAGConfig()
        assert cfg.embedding_model == "all-MiniLM-L6-v2"

    def test_default_similarity_threshold(self) -> None:
        cfg = RAGConfig()
        assert cfg.similarity_threshold == 0.3


class TestAetherMLConfigComposition:
    def test_default_sub_configs(self) -> None:
        cfg = AetherMLConfig()
        assert isinstance(cfg.engine, EngineConfig)
        assert isinstance(cfg.data, DataConfig)
        assert isinstance(cfg.qdrant, QdrantConfig)
        assert isinstance(cfg.rag, RAGConfig)

    def test_nested_defaults(self) -> None:
        cfg = AetherMLConfig()
        assert cfg.engine.preferred is None
        assert cfg.data.default_format == "auto"
        assert cfg.qdrant.url == "http://localhost:6333"
        assert cfg.rag.enabled is False

    def test_custom_sub_config(self) -> None:
        engine = EngineConfig(preferred="polars")
        cfg = AetherMLConfig(engine=engine)
        assert cfg.engine.preferred == "polars"
        # Other sub-configs still default
        assert cfg.data.default_format == "auto"


class TestAetherMLConfigExtraIgnore:
    def test_unknown_fields_dropped(self) -> None:
        cfg = AetherMLConfig(unknown_field="hello", another=42)
        assert not hasattr(cfg, "unknown_field")
        assert not hasattr(cfg, "another")

    def test_valid_fields_preserved(self) -> None:
        cfg = AetherMLConfig(engine=EngineConfig(preferred="spark"))
        assert cfg.engine.preferred == "spark"


class TestAetherMLConfigValidation:
    def test_wrong_type_for_data_raises(self) -> None:
        with pytest.raises(ValidationError):
            AetherMLConfig(data="not a dict")  # type: ignore[arg-type]

    def test_wrong_type_for_engine_raises(self) -> None:
        with pytest.raises(ValidationError):
            AetherMLConfig(engine=123)  # type: ignore[arg-type]


class TestEngineConfigPreferredValidation:
    def test_preferred_accepts_pandas(self) -> None:
        cfg = EngineConfig(preferred="pandas")
        assert cfg.preferred == "pandas"

    def test_preferred_accepts_polars(self) -> None:
        cfg = EngineConfig(preferred="polars")
        assert cfg.preferred == "polars"

    def test_preferred_accepts_spark(self) -> None:
        cfg = EngineConfig(preferred="spark")
        assert cfg.preferred == "spark"

    def test_preferred_accepts_none(self) -> None:
        cfg = EngineConfig(preferred=None)
        assert cfg.preferred is None
