"""F-06: Dynamic Re-Recommendation stream.

Frontend opens `GET /api/realtime/stream` as an EventSource. Whenever the
catalog, an itinerary, or a live location drift changes, this endpoint
pushes a JSON event so the discover feed / gap-filler can silently
recalculate.
"""

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services.events import event_bus


router = APIRouter(prefix="/api/realtime", tags=["realtime"])


async def _event_generator(request: Request):
    queue = event_bus.subscribe()
    try:
        # Send an initial "hello" so the client's onopen fires promptly.
        hello = {"type": "hello", "ts": datetime.now(timezone.utc).isoformat()}
        yield f"data: {json.dumps(hello)}\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25.0)
                yield f"data: {json.dumps(event, default=str)}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat keeps proxies from cutting the stream.
                yield ": keepalive\n\n"
    finally:
        event_bus.unsubscribe(queue)


@router.get("/stream")
async def stream(request: Request):
    return StreamingResponse(
        _event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
