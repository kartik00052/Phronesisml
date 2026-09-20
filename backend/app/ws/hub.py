"""WebSocket connection hub — thread-safe publish/subscribe.

The hub lets any thread (run worker, HTTP handler) push run events onto
the asyncio event loop, which fans them out to every subscribed
``WebSocket`` connection.  Subscriptions are per-run ``asyncio.Queue``
drained by per-connection sender tasks in :mod:`backend.app.api.v1.ws`.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from collections import defaultdict
from typing import Any

__all__ = ["Hub", "HUB"]


class Hub:
    """A lightweight broadcast hub keyed by ``run_id``."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[Any]]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the hub to the running asyncio loop (call at startup)."""
        with self._lock:
            self._loop = loop

    def subscribe(self, run_id: str) -> asyncio.Queue[Any]:
        """Register a queue for *run_id* and return it."""
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=10_000)
        with self._lock:
            self._subs[run_id].add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[Any]) -> None:
        with self._lock:
            self._subs.get(run_id, set()).discard(queue)

    def publish(self, run_id: str, payload: dict[str, Any]) -> None:
        """Thread-safe publish: schedule dispatch on the event loop."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(self._dispatch, run_id, payload)

    def subscriber_count(self, run_id: str) -> int:
        with self._lock:
            return len(self._subs.get(run_id, set()))

    def _dispatch(self, run_id: str, payload: dict[str, Any]) -> None:
        for queue in list(self._subs.get(run_id, ())):
            with contextlib.suppress(asyncio.QueueFull):  # bounded queue
                queue.put_nowait(payload)


HUB = Hub()
