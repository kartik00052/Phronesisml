"""In-memory job store for asynchronous pipeline execution.

Provides a simple, thread-safe (asyncio-safe) job store that tracks
the lifecycle of background tasks.  Jobs are stored in a dictionary
and are lost on server restart — this is intentional for v1 and
avoids adding persistence dependencies.

Production deployments should replace this with Redis, PostgreSQL,
or a task queue (Celery, ARQ, etc.).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """A single asynchronous job."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "queued"
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    started_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    _task: asyncio.Task[Any] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Serialise job to a dict (excludes internal fields)."""
        return {
            "job_id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }


class JobStore:
    """In-memory job store with asyncio-safe operations."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create(self) -> Job:
        """Create a new job and register it."""
        job = Job()
        async with self._lock:
            self._jobs[job.id] = job
        logger.info("Job created: %s", job.id)
        return job

    async def get(self, job_id: str) -> Job | None:
        """Retrieve a job by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(self) -> list[Job]:
        """Return all jobs (newest first)."""
        async with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )

    async def update_status(
        self,
        job_id: str,
        status: str,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status and optional result/error."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            now = datetime.now(UTC).isoformat()
            if status == "running" and job.started_at is None:
                job.started_at = now
            if status in ("completed", "failed"):
                job.completed_at = now
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error

    async def start_job(
        self,
        job_id: str,
        coro: Coroutine[Any, Any, dict[str, Any]],
    ) -> None:
        """Mark job as running and schedule the coroutine as a background task."""
        await self.update_status(job_id, "running")

        async def _wrapper() -> None:
            try:
                result = await coro
                await self.update_status(job_id, "completed", result=result)
            except Exception as exc:
                logger.exception("Job %s failed", job_id)
                await self.update_status(job_id, "failed", error=str(exc))

        task = asyncio.create_task(_wrapper())
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job._task = task


# Module-level singleton
job_store = JobStore()
