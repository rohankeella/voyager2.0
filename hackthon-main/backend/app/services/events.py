"""Tiny in-process pub/sub for F-06 dynamic re-recommendation.

Multiple concurrent SSE subscribers each get their own asyncio.Queue.
`publish()` is safe to call from sync code paths (routers) — it schedules
delivery on the running loop for each subscriber.

Not durable, not multi-worker. If we ever scale past a single uvicorn worker
this needs to move to Redis pub/sub.
"""

from __future__ import annotations

import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Slow consumer — drop the message rather than block the caller.
                pass


event_bus = EventBus()
