"""Database engine, session factory, and model base.

SQLite is the canonical backing store for run metadata, events, stage
state, artifacts, and model results.  Large payloads (dataset files,
model binaries, reports) live on disk under the storage directories;
only references are stored here.

Concurrency notes:
- ``check_same_thread=False`` lets worker threads (one per run) share
  the engine safely.
- WAL journaling enables concurrent readers + a single writer.
- A global write lock serialises SQLite writes from any thread.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.app.config import get_settings

Base = declarative_base()

# Serialises all SQLite writes (single-process backend; correctness over speed).
_write_lock = threading.Lock()


def _engine_factory() -> Engine:
    settings = get_settings()
    url = settings.database_url
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        db_path = url.replace("sqlite:///", "", 1)
        if db_path.startswith("./"):
            db_path = str(settings.root_dir / db_path[2:])
        parent = Path(db_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(
        url,
        connect_args=connect_args or None,
        pool_pre_ping=True,
        future=True,
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: object, _: object) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return engine


engine = _engine_factory()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_write_lock() -> threading.Lock:
    """Return the process-wide SQLite write lock."""
    return _write_lock


def init_db() -> None:
    """Create tables if they do not yet exist (dev/bootstrapping)."""
    # Import models so they register on Base.metadata before create_all.
    from backend.app.db import models as _models  # noqa: F401

    with _write_lock:
        Base.metadata.create_all(bind=engine)
        _ensure_column(engine, "datasets", "sample")
    ensure_storage_dirs()


def _ensure_column(db_engine: Engine, table: str, column: str) -> None:
    """Additive, idempotent column backfill for pre-existing SQLite tables.

    ``create_all`` never alters existing tables, so a previously created
    database would otherwise miss newly added columns. Only additive
    ``ALTER TABLE ... ADD COLUMN`` statements are ever issued.
    """
    if not (db_engine.dialect.name == "sqlite" and hasattr(db_engine, "connect")):
        return
    with db_engine.connect() as conn:
        cols = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
        if column not in cols:
            sql = f"ALTER TABLE {table} ADD COLUMN {column} BOOLEAN NOT NULL DEFAULT 0"
            conn.exec_driver_sql(sql)
            conn.commit()


def ensure_storage_dirs() -> None:
    """Ensure all configured storage directories exist."""
    settings = get_settings()
    for path in (
        settings.data_storage_dir,
        settings.run_storage_dir,
        settings.artifact_storage_dir,
        settings.report_storage_dir,
        settings.root_dir / "data",
    ):
        path.mkdir(parents=True, exist_ok=True)


def sqlite_file_path() -> str | None:
    """Return the absolute SQLite file path when a SQLite database is used."""
    url = get_settings().database_url
    if not url.startswith("sqlite:"):
        return None
    bare = url.replace("sqlite:///", "", 1)
    if bare.startswith("./"):
        return str(get_settings().root_dir / bare[2:])
    return os.path.abspath(bare)
