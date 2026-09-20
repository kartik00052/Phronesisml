"""Backend configuration — environment-driven settings.

All paths default relative to the repository root so the backend runs
identically from any working directory (``uvicorn backend.app.main:app``).

Paths & limits follow the target contract:

- ``DATABASE_URL=sqlite:///./data/phronesisml.db``
- ``DATA_STORAGE_DIR=./storage/datasets``
- ``RUN_STORAGE_DIR=./storage/runs``
- ``ARTIFACT_STORAGE_DIR=./storage/artifacts``
- ``REPORT_STORAGE_DIR=./storage/reports``
- ``MAX_UPLOAD_SIZE_MB=2048``
- ``CORS_ORIGINS=http://localhost:5173``
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["ROOT_DIR", "Settings", "normalize_database_url", "get_settings"]


ROOT_DIR = Path(__file__).resolve().parents[2]


def normalize_database_url(url: str) -> str:
    """Route a bare ``postgresql://``/``postgres://`` URL to the psycopg driver.

    SQLAlchemy's default driver for that scheme is ``psycopg2``, which is not
    installed here — the project pins ``psycopg[binary]`` (psycopg 3). Supabase
    exposes ``postgresql://`` connection strings, so without this rewrite the
    engine and Alembic would fail with ``ModuleNotFoundError: psycopg2``.
    URLs that already name a driver (``postgresql+psycopg://``) pass through.
    """
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.split("://", 1)[1]
    return url


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings resolved from environment variables."""

    root_dir: Path = ROOT_DIR
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", f"sqlite:///{ROOT_DIR / 'data' / 'phronesisml.db'}"
        )
    )
    data_storage_dir: Path = field(
        default_factory=lambda: _env_path("DATA_STORAGE_DIR", ROOT_DIR / "storage" / "datasets")
    )
    run_storage_dir: Path = field(
        default_factory=lambda: _env_path("RUN_STORAGE_DIR", ROOT_DIR / "storage" / "runs")
    )
    artifact_storage_dir: Path = field(
        default_factory=lambda: _env_path(
            "ARTIFACT_STORAGE_DIR", ROOT_DIR / "storage" / "artifacts"
        )
    )
    report_storage_dir: Path = field(
        default_factory=lambda: _env_path("REPORT_STORAGE_DIR", ROOT_DIR / "storage" / "reports")
    )
    max_upload_size_mb: int = field(
        default_factory=lambda: int(os.environ.get("MAX_UPLOAD_SIZE_MB", "2048"))
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
            if o.strip()
        )
    )
    request_log: bool = field(default_factory=lambda: os.environ.get("REQUEST_LOG", "1") != "0")
    app_name: str = field(default_factory=lambda: os.environ.get("VITE_APP_NAME", "PhronesisML"))
    seed_sample_datasets: bool = field(
        default_factory=lambda: os.environ.get("SEED_SAMPLE_DATASETS", "1") == "1"
    )
    # ── Authentication ──────────────────────────────────────────────────────
    # "disabled" → no JWT is required; requests run under the fixed
    # "local-dev" identity (single-tenant dev/test). "supabase" → every
    # protected endpoint validates a Supabase access token and enforces
    # per-user ownership of datasets/runs.
    auth_mode: str = field(default_factory=lambda: os.environ.get("AUTH_MODE", "disabled"))
    supabase_url: str = field(default_factory=lambda: os.environ.get("SUPABASE_URL", ""))
    supabase_anon_key: str = field(default_factory=lambda: os.environ.get("SUPABASE_ANON_KEY", ""))
    # Server-side only. Either the legacy HS256 shared secret (most projects)
    # or a JWKS URL for RSA/RS256 verification. Never exposed to the client.
    supabase_jwt_secret: str = field(
        default_factory=lambda: os.environ.get("SUPABASE_JWT_SECRET", "")
    )
    supabase_jwt_issuer: str = field(
        default_factory=lambda: os.environ.get("SUPABASE_JWT_ISSUER", "")
    )
    supabase_jwks_url: str = field(default_factory=lambda: os.environ.get("SUPABASE_JWKS_URL", ""))
    supabase_jwt_audience: str = field(
        default_factory=lambda: os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")
    )
    # ── Database pooling (PostgreSQL) ───────────────────────────────────────
    db_pool_size: int = field(default_factory=lambda: int(os.environ.get("DB_POOL_SIZE", "5")))
    db_max_overflow: int = field(
        default_factory=lambda: int(os.environ.get("DB_MAX_OVERFLOW", "10"))
    )

    @property
    def auth_enabled(self) -> bool:
        return self.auth_mode == "supabase"

    @property
    def resolved_supabase_jwt_issuer(self) -> str | None:
        """Effective issuer — explicit env override, else derived from the project URL."""
        if self.supabase_jwt_issuer:
            return self.supabase_jwt_issuer
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1"
        return None

    @property
    def resolved_supabase_jwks_url(self) -> str | None:
        """Effective JWKS URL — explicit env override, else derived from the project URL."""
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        return None

    @property
    def max_upload_bytes(self) -> int:
        """Maximum accepted upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if raw is None:
        return default
    p = Path(raw)
    return p if p.is_absolute() else ROOT_DIR / p


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()
    return _settings
