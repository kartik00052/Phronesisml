"""Unit tests for Phronesis configuration settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from phronesisml.configs.settings import (
    DataConfig,
    EngineConfig,
    PhronesisConfig,
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


class TestPhronesisConfigComposition:
    def test_default_sub_configs(self) -> None:
        cfg = PhronesisConfig()
        assert isinstance(cfg.engine, EngineConfig)
        assert isinstance(cfg.data, DataConfig)

    def test_nested_defaults(self) -> None:
        cfg = PhronesisConfig()
        assert cfg.engine.preferred is None
        assert cfg.data.default_format == "auto"

    def test_custom_sub_config(self) -> None:
        engine = EngineConfig(preferred="polars")
        cfg = PhronesisConfig(engine=engine)
        assert cfg.engine.preferred == "polars"
        # Other sub-configs still default
        assert cfg.data.default_format == "auto"


class TestPhronesisConfigExtraIgnore:
    def test_unknown_fields_dropped(self) -> None:
        cfg = PhronesisConfig(unknown_field="hello", another=42)
        assert not hasattr(cfg, "unknown_field")
        assert not hasattr(cfg, "another")

    def test_valid_fields_preserved(self) -> None:
        cfg = PhronesisConfig(engine=EngineConfig(preferred="spark"))
        assert cfg.engine.preferred == "spark"


class TestPhronesisConfigValidation:
    def test_wrong_type_for_data_raises(self) -> None:
        with pytest.raises(ValidationError):
            PhronesisConfig(data="not a dict")  # type: ignore[arg-type]

    def test_wrong_type_for_engine_raises(self) -> None:
        with pytest.raises(ValidationError):
            PhronesisConfig(engine=123)  # type: ignore[arg-type]


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
