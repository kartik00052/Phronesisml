"""Database URL resolution for no-auth prototype deployments."""

from __future__ import annotations

import pytest

from backend.app.config import Settings

SUPABASE_URL = (
    "postgresql://postgres.project:secret@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
)


def test_disabled_auth_ignores_stale_supabase_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "disabled")
    monkeypatch.setenv("DATABASE_URL", SUPABASE_URL)

    settings = Settings()

    assert settings.database_url.startswith("sqlite:///")


def test_supabase_auth_keeps_supabase_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.setenv("DATABASE_URL", SUPABASE_URL)

    settings = Settings()

    assert settings.database_url == SUPABASE_URL


def test_disabled_auth_keeps_non_supabase_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "disabled")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/phronesisml")

    settings = Settings()

    assert settings.database_url == "postgresql://localhost:5432/phronesisml"


def test_missing_database_url_defaults_to_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AUTH_MODE", "disabled")

    settings = Settings()

    assert settings.database_url.startswith("sqlite:///")
