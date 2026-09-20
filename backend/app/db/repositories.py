"""Persistence layer — thread-safe CRUD over the SQLAlchemy models.

Every function opens its own short-lived session so that HTTP handlers
(asyncio event loop) and run worker threads can call them safely.
All SQLite writes are serialised by the global write lock.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db.database import SessionLocal, get_write_lock
from backend.app.db.models import Artifact, Dataset, ModelResult, PipelineStage, Run, RunEvent

ILLEGAL_EVENT_MARKER = "_ILLEGAL_EVENT_"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime | None) -> str | None:
    """Serialize a datetime to ISO-8601 with a trailing Z (UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _ownership_clause(column: Any, user_id: str | None, shared_column: Any = None) -> Any | None:
    """Ownership predicate for user-scoped queries.

    ``None`` user_id (internal/trusted callers) disables filtering.

    - AUTH_MODE=disabled: rows owned by *user_id* OR unowned (NULL) rows —
      pre-existing dev data stays visible under the local-dev identity.
    - AUTH_MODE=supabase: strictly owned rows, plus shared system rows only
      when the caller opts in via *shared_column* (bundled samples).
    """
    if user_id is None:
        return None
    me = column == user_id
    if not get_settings().auth_enabled:
        return or_(me, column.is_(None))
    if shared_column is not None:
        return or_(me, and_(column.is_(None), shared_column.is_(True)))
    return me


@contextlib.contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager yielding a new session, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ─────────────────────────── Datasets ───────────────────────────


def create_dataset(row: dict[str, Any]) -> Dataset:
    with get_write_lock(), session_scope() as session:
        obj = Dataset(**{k: v for k, v in row.items() if k in Dataset.__table__.columns})
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj


def get_dataset(dataset_id: str, user_id: str | None = None) -> Dataset | None:
    with session_scope() as session:
        stmt = select(Dataset).where(Dataset.id == dataset_id)
        owner = _ownership_clause(Dataset.user_id, user_id, Dataset.sample)
        if owner is not None:
            stmt = stmt.where(owner)
        return session.scalar(stmt)


def list_datasets(
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    format: str | None = None,  # noqa: A002
    user_id: str | None = None,
) -> tuple[list[Dataset], int]:
    with session_scope() as session:
        stmt = select(Dataset)
        count_stmt = select(func.count()).select_from(Dataset)
        owner = _ownership_clause(Dataset.user_id, user_id, Dataset.sample)
        if owner is not None:
            stmt = stmt.where(owner)
            count_stmt = count_stmt.where(owner)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(Dataset.name.like(like))
            count_stmt = count_stmt.where(Dataset.name.like(like))
        if format:
            stmt = stmt.where(Dataset.format == format)
            count_stmt = count_stmt.where(Dataset.format == format)
        total = int(session.scalar(count_stmt) or 0)
        stmt = stmt.order_by(Dataset.registered_at.desc(), Dataset.id.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(session.scalars(stmt).all()), total


def update_dataset(dataset_id: str, **fields: Any) -> None:
    with get_write_lock(), session_scope() as session:
        obj = session.get(Dataset, dataset_id)
        if obj is None:
            return
        for key, value in fields.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        session.commit()


def touch_dataset_last_used(dataset_id: str, run_id: str) -> None:
    update_dataset(dataset_id, last_used_run_id=run_id)


# ───────────────────────────── Runs ─────────────────────────────


def create_run(row: dict[str, Any]) -> Run:
    with get_write_lock(), session_scope() as session:
        obj = Run(**{k: v for k, v in row.items() if k in Run.__table__.columns})
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj


def get_run(run_id: str, user_id: str | None = None) -> Run | None:
    with session_scope() as session:
        stmt = select(Run).where(Run.id == run_id)
        owner = _ownership_clause(Run.user_id, user_id)
        if owner is not None:
            stmt = stmt.where(owner)
        return session.scalar(stmt)


def update_run(run_id: str, **fields: Any) -> None:
    with get_write_lock(), session_scope() as session:
        obj = session.get(Run, run_id)
        if obj is None:
            return
        for key, value in fields.items():
            if hasattr(obj, key) and key not in {"id", "created_at"}:
                setattr(obj, key, value)
        obj.updated_at = _utcnow()
        session.commit()


def list_runs(
    *,
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    dataset_id: str | None = None,
    search: str | None = None,
    task_type: str | None = None,
    sort: str | None = None,
    order: str | None = None,
    user_id: str | None = None,
) -> tuple[list[Run], int]:
    with session_scope() as session:
        stmt = select(Run)
        count_stmt = select(func.count()).select_from(Run)
        owner = _ownership_clause(Run.user_id, user_id)
        if owner is not None:
            stmt = stmt.where(owner)
            count_stmt = count_stmt.where(owner)
        if status:
            stmt = stmt.where(Run.status == status)
            count_stmt = count_stmt.where(Run.status == status)
        if dataset_id:
            stmt = stmt.where(Run.dataset_id == dataset_id)
            count_stmt = count_stmt.where(Run.dataset_id == dataset_id)
        if task_type:
            stmt = stmt.where(Run.task_type == task_type)
            count_stmt = count_stmt.where(Run.task_type == task_type)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(Run.dataset_name.like(like) | Run.id.like(like))
            count_stmt = count_stmt.where(Run.dataset_name.like(like) | Run.id.like(like))
        total = int(session.scalar(count_stmt) or 0)
        stmt = stmt.order_by(*_run_order_by(sort, order))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(session.scalars(stmt).all()), total


# Allow-listed sort columns (client value → ORM column). Anything else falls
# back to createdAt desc so a bad query string can never break the endpoint.
_RUN_SORT_COLUMNS = {
    "createdAt": Run.created_at,
    "created_at": Run.created_at,
    "updatedAt": Run.updated_at,
    "updated_at": Run.updated_at,
    "bestScore": Run.best_score,
    "best_score": Run.best_score,
    "durationMs": Run.total_duration_ms,
    "duration_ms": Run.total_duration_ms,
    "datasetName": Run.dataset_name,
    "dataset_name": Run.dataset_name,
}


def _run_order_by(sort: str | None, order: str | None):  # noqa: ANN202
    column = _RUN_SORT_COLUMNS.get(sort or "") if sort else None
    descending = (order or "desc").lower() != "asc"
    if column is None:
        return (Run.created_at.desc(), Run.id.desc())
    ordered = column.desc() if descending else column.asc()
    return (ordered, Run.id.desc())


def list_recent_runs(limit: int = 8, user_id: str | None = None) -> list[Run]:
    with session_scope() as session:
        stmt = select(Run).order_by(Run.created_at.desc(), Run.id.desc()).limit(limit)
        owner = _ownership_clause(Run.user_id, user_id)
        if owner is not None:
            stmt = stmt.where(owner)
        return list(session.scalars(stmt).all())


def list_runs_by_status(statuses: Sequence[str]) -> list[Run]:
    """Runs currently in any of *statuses* (used by startup reconciliation)."""
    if not statuses:
        return []
    with session_scope() as session:
        stmt = select(Run).where(Run.status.in_(list(statuses)))
        return list(session.scalars(stmt).all())


def delete_run(run_id: str) -> None:
    with get_write_lock(), session_scope() as session:
        for model in (Artifact, RunEvent, PipelineStage, ModelResult):
            session.query(model).filter(model.run_id == run_id).delete()  # type: ignore[attr-defined]
        session.query(Run).filter(Run.id == run_id).delete()  # type: ignore[attr-defined]
        session.commit()


# ─────────────────────────── Events ────────────────────────────


def create_event(
    run_id: str,
    *,
    event_type: str,
    stage: str | None = None,
    status: str | None = None,
    summary: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> RunEvent:
    with get_write_lock(), session_scope() as session:
        last_seq = session.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id))
        seq = int(last_seq or 0) + 1
        obj = RunEvent(
            run_id=run_id,
            seq=seq,
            type=event_type,
            stage=stage,
            status=status,
            summary=_jsonable(summary),
            payload=_jsonable(payload),
        )
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj


def list_events(run_id: str, after: int | None = None, limit: int = 10000) -> list[RunEvent]:
    with session_scope() as session:
        stmt = select(RunEvent).where(RunEvent.run_id == run_id)
        if after is not None:
            stmt = stmt.where(RunEvent.seq > after)
        stmt = stmt.order_by(RunEvent.seq.asc()).limit(limit)
        return list(session.scalars(stmt).all())


# ──────────────────────── Pipeline stages ──────────────────────


def create_stage(run_id: str, stage: str, position: int) -> PipelineStage:
    """Upsert a pipeline stage row — idempotent across re-runs/restores."""
    with get_write_lock(), session_scope() as session:
        existing = session.scalars(
            select(PipelineStage).where(
                PipelineStage.run_id == run_id,
                PipelineStage.stage == stage,
            )
        ).first()
        if existing is not None:
            existing.position = position
            existing.status = "queued"
            existing.queued_at = existing.queued_at or _utcnow()
            existing.started_at = None
            existing.completed_at = None
            existing.duration_ms = None
            existing.summary = None
            existing.error = None
            existing.logs = []
            obj = existing
        else:
            obj = PipelineStage(
                run_id=run_id, stage=stage, position=position, status="queued", queued_at=_utcnow()
            )
            session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj


def get_stages(run_id: str) -> list[PipelineStage]:
    with session_scope() as session:
        stmt = (
            select(PipelineStage)
            .where(PipelineStage.run_id == run_id)
            .order_by(PipelineStage.position.asc(), PipelineStage.id.asc())
        )
        return list(session.scalars(stmt).all())


def update_stage(
    run_id: str,
    stage: str,
    *,
    status: str,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    duration_ms: int | None = None,
    summary: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> None:
    with get_write_lock(), session_scope() as session:
        obj = session.scalar(
            select(PipelineStage).where(
                PipelineStage.run_id == run_id, PipelineStage.stage == stage
            )
        )
        if obj is None:
            obj = PipelineStage(run_id=run_id, stage=stage, position=0, status=status)
            session.add(obj)
        obj.status = status
        if started_at is not None:
            obj.started_at = started_at
        if completed_at is not None:
            obj.completed_at = completed_at
        if duration_ms is not None:
            obj.duration_ms = duration_ms
        if summary is not None:
            obj.summary = _jsonable(summary)
        if error is not None:
            obj.error = _jsonable(error)
        session.commit()


def upsert_stage_summary(run_id: str, stage: str, summary: dict[str, Any]) -> None:
    with get_write_lock(), session_scope() as session:
        obj = session.scalar(
            select(PipelineStage).where(
                PipelineStage.run_id == run_id, PipelineStage.stage == stage
            )
        )
        if obj is None:
            return
        base = _jsonable(obj.summary if isinstance(obj.summary, dict) else {})
        obj.summary = base | _jsonable(summary)
        session.commit()


# ────────────────────────── Artifacts ──────────────────────────


def index_artifacts(run_id: str, items: Sequence[dict[str, Any]]) -> int:
    with get_write_lock(), session_scope() as session:
        session.query(Artifact).filter(Artifact.run_id == run_id).delete()  # type: ignore[attr-defined]
        count = 0
        for item in items:
            name = str(item["name"])
            artifact_id = f"{run_id}/{name}"
            existing = session.get(Artifact, artifact_id)
            if existing is None:
                existing = Artifact(id=artifact_id, run_id=run_id)
                session.add(existing)
            existing.name = name
            existing.kind = str(item.get("kind") or "pipeline")
            existing.format = str(item.get("format") or "json")
            existing.size_bytes = int(item.get("size_bytes") or 0)
            existing.status = str(item.get("status") or "available")
            existing.reason = item.get("reason")
            existing.description = item.get("description")
            existing.url = item.get("url")
            count += 1
        session.commit()
        return count


def list_artifacts(run_id: str) -> list[Artifact]:
    with session_scope() as session:
        stmt = select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.name.asc())
        return list(session.scalars(stmt).all())


def get_artifact(run_id: str, name: str) -> Artifact | None:
    with session_scope() as session:
        return session.get(Artifact, f"{run_id}/{name}")


def count_artifacts(run_id: str | None = None, user_id: str | None = None) -> int:
    with session_scope() as session:
        stmt = select(func.count()).select_from(Artifact).join(Run, Artifact.run_id == Run.id)
        if run_id:
            stmt = stmt.where(Artifact.run_id == run_id)
        owner = _ownership_clause(Run.user_id, user_id)
        if owner is not None:
            stmt = stmt.where(owner)
        return int(session.scalar(stmt) or 0)


def invalidate_artifacts(run_id: str, reason: str) -> int:
    """Mark every indexed artifact for *run_id* unavailable with a reason.

    Used on restore so a re-queued run never shows the previous attempt's
    artifacts as if they were current; the manifest then renders honestly
    until the new run re-indexes its own outputs.
    """
    with get_write_lock(), session_scope() as session:
        rows = session.scalars(select(Artifact).where(Artifact.run_id == run_id)).all()
        for row in rows:
            row.status = "unavailable"
            row.reason = reason
        session.commit()
        return len(rows)


# ──────────────────────── Model results ────────────────────────


def replace_model_results(run_id: str, rows: Sequence[dict[str, Any]]) -> int:
    with get_write_lock(), session_scope() as session:
        session.query(ModelResult).filter(ModelResult.run_id == run_id).delete()  # type: ignore[attr-defined]
        for row in rows:
            session.add(ModelResult(run_id=run_id, **row))
        session.commit()
        return len(rows)


def list_model_results(run_id: str) -> list[ModelResult]:
    with session_scope() as session:
        stmt = (
            select(ModelResult).where(ModelResult.run_id == run_id).order_by(ModelResult.rank.asc())
        )
        return list(session.scalars(stmt).all())


def count_model_results(user_id: str | None = None) -> int:
    with session_scope() as session:
        stmt = select(func.count()).select_from(ModelResult).join(Run, ModelResult.run_id == Run.id)
        owner = _ownership_clause(Run.user_id, user_id)
        if owner is not None:
            stmt = stmt.where(owner)
        return int(session.scalar(stmt) or 0)


# ─────────────────────────── Statistics ────────────────────────


def run_stats(user_id: str | None = None) -> dict[str, Any]:
    with session_scope() as session:
        owner = _ownership_clause(Run.user_id, user_id)
        run_filter = [owner] if owner is not None else []

        def count_with(*clauses: Any) -> int:
            stmt = select(func.count()).select_from(Run)
            for clause in run_filter:
                stmt = stmt.where(clause)
            for clause in clauses:
                stmt = stmt.where(clause)
            return int(session.scalar(stmt) or 0)

        total_runs = count_with()
        active = count_with(Run.status == Run.STATUS_RUNNING)
        completed = count_with(Run.status == Run.STATUS_COMPLETED)
        failed = count_with(Run.status == Run.STATUS_FAILED)
        queued = count_with(Run.status == Run.STATUS_QUEUED)
        cancelled = count_with(Run.status == Run.STATUS_CANCELLED)

        dataset_stmt = select(func.count()).select_from(Dataset)
        dataset_owner = _ownership_clause(Dataset.user_id, user_id, Dataset.sample)
        if dataset_owner is not None:
            dataset_stmt = dataset_stmt.where(dataset_owner)
        total_datasets = int(session.scalar(dataset_stmt) or 0)

        avg_stmt = select(func.avg(Run.best_score)).where(Run.best_score.isnot(None))
        avg_dur_stmt = select(func.avg(Run.total_duration_ms)).where(
            Run.total_duration_ms.isnot(None), Run.status == Run.STATUS_COMPLETED
        )
        engine_stmt = (
            select(Run.engine, func.count()).where(Run.engine.isnot(None)).group_by(Run.engine)
        )
        task_stmt = (
            select(Run.task_type, func.count())
            .where(Run.task_type.isnot(None))
            .group_by(Run.task_type)
        )
        for clause in run_filter:
            avg_stmt = avg_stmt.where(clause)
            avg_dur_stmt = avg_dur_stmt.where(clause)
            engine_stmt = engine_stmt.where(clause)
            task_stmt = task_stmt.where(clause)
        avg_score = session.scalar(avg_stmt)
        avg_duration = session.scalar(avg_dur_stmt)
        engine_rows = session.execute(engine_stmt).all()
        task_rows = session.execute(task_stmt).all()
        return {
            "total_runs": total_runs,
            "active_runs": active,
            "queued_runs": queued,
            "completed_runs": completed,
            "failed_runs": failed,
            "cancelled_runs": cancelled,
            "total_datasets": total_datasets,
            "avg_best_score": float(avg_score) if avg_score is not None else None,
            "avg_duration_ms": int(avg_duration) if avg_duration is not None else None,
            "engine_breakdown": {k: int(v) for k, v in engine_rows},
            "task_breakdown": {k: int(v) for k, v in task_rows},
        }


# ─────────────────────────── Helpers ───────────────────────────


def _jsonable(value: Any) -> Any:
    """Best-effort JSON conversion for dict payloads (guards NaN/inf)."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {
            str(k): jsonable_v
            for k, v in value.items()
            if (jsonable_v := _jsonable(v)) is not None or v is None
        }
    return value


def file_size(path: str | os.PathLike[str]) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0
