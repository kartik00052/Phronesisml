"""Run event emission — persist to SQLite first, then broadcast on WS.

Canonical event types (single source of truth):
``run.created``, ``run.started``, ``pipeline.stage``, ``pipeline.warning``,
``pipeline.error``, ``artifact.created``, ``model.completed``,
``run.completed``, ``run.failed``, ``run.cancelled``.

Every event is durable (written to ``run_events``) so a WebSocket client
that reconnects can replay history from its last ``seq``.
"""

from __future__ import annotations

from typing import Any

from backend.app.db import repositories
from backend.app.db.repositories import iso
from backend.app.ws.hub import HUB, Hub

__all__ = ["emit_event", "REPLAY_EVENT", "event_to_dict"]


def event_to_dict(rec: Any) -> dict[str, Any]:
    """Convert a persisted ``RunEvent`` into its wire payload."""
    return {
        "run_id": rec.run_id,
        "seq": rec.seq,
        "type": rec.type,
        "stage": rec.stage,
        "status": rec.status,
        "summary": rec.summary,
        "payload": rec.payload,
        "ts": iso(rec.created_at),
    }


REPLAY_EVENT = {"type": "replay.done"}


def emit_event(
    run_id: str,
    *,
    event_type: str,
    stage: str | None = None,
    status: str | None = None,
    summary: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    hub: Hub | None = None,
) -> dict[str, Any]:
    """Persist and broadcast a single event."""
    rec = repositories.create_event(
        run_id,
        event_type=event_type,
        stage=stage,
        status=status,
        summary=summary,
        payload=payload,
    )
    evt = event_to_dict(rec)
    (hub or HUB).publish(run_id, evt)
    return evt
