"""WebSocket endpoint — live run events (``/api/v1/ws/runs/{run_id}``).

Connects to the thread-safe :class:`backend.app.ws.hub.Hub`, replays the
persisted event history (``events.replay_events``) from the client's last
sequence, then streams live events as they are emitted by the run worker.

The connection is authenticated *before* accept:

- ``AUTH_MODE=supabase`` requires a valid Supabase access token (via the
  ``access_token``/``token`` query parameter or an ``Authorization`` header),
  and the run must belong to the authenticated user — otherwise the socket is
  closed with ``4401`` (unauthenticated) or ``4404`` (not found / not owned).
- ``AUTH_MODE=disabled`` uses the fixed local-dev identity (dev/test).

The message wire format is unchanged.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.auth.deps import get_websocket_user
from backend.app.auth.verifier import AuthError
from backend.app.db import repositories
from backend.app.services.events import event_to_dict
from backend.app.ws.hub import HUB

router = APIRouter()

_HEARTBEAT_INTERVAL = 30.0


@router.websocket("/ws/runs/{run_id}")
async def run_events_ws(websocket: WebSocket, run_id: str) -> None:
    try:
        user = get_websocket_user(websocket)
    except AuthError:
        await websocket.close(code=4401)
        return
    if repositories.get_run(run_id, user_id=user.user_id) is None:
        # Close codes: 4404 mirrors the HTTP 404 semantics — the run either
        # does not exist or belongs to someone else, and neither is surfaced.
        await websocket.close(code=4404)
        return
    await websocket.accept()
    queue = HUB.subscribe(run_id)
    try:
        await _replay(websocket, run_id)
        loop = asyncio.get_running_loop()
        heartbeat = loop.create_task(_heartbeat(websocket))
        try:
            while True:
                payload = await queue.get()
                if payload is None:
                    break
                await websocket.send_text(json.dumps(payload, default=str))
        finally:
            heartbeat.cancel()
    except WebSocketDisconnect:
        pass
    finally:
        HUB.unsubscribe(run_id, queue)


async def _replay(websocket: WebSocket, run_id: str) -> None:
    """Re-send persisted events since the client's claimed last sequence."""
    last_seq = int(websocket.query_params.get("last_seq", "0") or 0)
    for record in repositories.list_events(run_id, after=last_seq):
        await websocket.send_text(json.dumps(event_to_dict(record), default=str))
    await websocket.send_text(json.dumps({"type": "replay.done", "run_id": run_id}))


async def _heartbeat(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(_HEARTBEAT_INTERVAL)
        try:
            await websocket.send_text(json.dumps({"type": "ping"}))
        except Exception:  # noqa: BLE001  (connection dropped)
            return
