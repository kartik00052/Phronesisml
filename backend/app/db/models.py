"""SQLAlchemy ORM models for the PhronesisML web backend.

Model set (minimum per the target contract):
- ``datasets``   — registered datasets + upload-time profile reference
- ``runs``       — run plan of record, status, summary
- ``run_events`` — persisted, ordered event log (reconnect-safe replay)
- ``pipeline_stages`` — per-stage lifecycle state
- ``artifacts``  — index of on-disk run artifacts
- ``model_results``  — indexed model leaderboard entries for a run

Only metadata/state is stored here — file bytes live under storage/.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False, default="csv")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    columns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engine: Mapped[str | None] = mapped_column(String, nullable=True)
    engine_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    validation_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    missing_cells: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicate_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_column: Mapped[str | None] = mapped_column(String, nullable=True)
    task_type: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_path: Mapped[str | None] = mapped_column(String, nullable=True)
    validation_path: Mapped[str | None] = mapped_column(String, nullable=True)
    preview_path: Mapped[str | None] = mapped_column(String, nullable=True)
    sheets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_used_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sample: Mapped[bool] = mapped_column(Boolean, default=False)


class Run(Base):
    __tablename__ = "runs"

    # queued | running | completed | failed | cancelled
    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    dataset_name: Mapped[str | None] = mapped_column(String, nullable=True)
    dataset_path: Mapped[str | None] = mapped_column(String, nullable=True)
    file_format: Mapped[str | None] = mapped_column(String, nullable=True)
    rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    columns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default=STATUS_QUEUED, index=True)
    request: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    engine: Mapped[str | None] = mapped_column(String, nullable=True)
    engine_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    mode: Mapped[str | None] = mapped_column(String, default="balanced")
    task_type: Mapped[str | None] = mapped_column(String, nullable=True)
    target_column: Mapped[str | None] = mapped_column(String, nullable=True)
    best_model_type: Mapped[str | None] = mapped_column(String, nullable=True)
    best_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_metric: Mapped[str | None] = mapped_column(String, nullable=True)
    trial_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hpo_truncated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sampling_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resource_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    transform_log: Mapped[list | None] = mapped_column(JSON, default=list)
    warnings: Mapped[list | None] = mapped_column(JSON, default=list)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stages_requested: Mapped[list | None] = mapped_column(JSON, default=list)
    stages_executed: Mapped[list | None] = mapped_column(JSON, default=list)
    total_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_dir: Mapped[str | None] = mapped_column(String, nullable=True)
    logs: Mapped[list | None] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "seq", name="uq_run_events_seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(40), ForeignKey("runs.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # noqa: A003
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"
    __table_args__ = (UniqueConstraint("run_id", "stage", name="uq_pipeline_stage"),)

    # idle | queued | running | completed | warning | failed | skipped | sampled
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(40), ForeignKey("runs.id"), index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    queued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    logs: Mapped[list | None] = mapped_column(JSON, default=list)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)  # f"{run_id}/{name}"
    run_id: Mapped[str] = mapped_column(String(40), ForeignKey("runs.id"), index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="pipeline")
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="json")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="available")
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)


class ModelResult(Base):
    __tablename__ = "model_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(40), ForeignKey("runs.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    model_type: Mapped[str] = mapped_column(String, nullable=False)
    primary_score: Mapped[float] = mapped_column(Float, default=0.0)
    secondary_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trials_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_elapsed: Mapped[float | None] = mapped_column(Float, nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_training_cost: Mapped[str | None] = mapped_column(String, nullable=True)
    best: Mapped[bool] = mapped_column(Boolean, default=False)
