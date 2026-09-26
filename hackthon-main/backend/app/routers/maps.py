"""F-03: Real-time maps + live route tracking.

Two responsibilities:
  1. Distance / travel-time lookup between two points. Uses Google Distance
     Matrix if GOOGLE_MAPS_API_KEY is set, otherwise the Haversine fallback.
  2. Location pings from an active traveler. Each ping compares projected
     arrival against the next itinerary anchor and returns a `DriftAlert`
     when the delta exceeds the 10-minute threshold from the PRD acceptance
     criteria for F-03.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.itinerary import Itinerary, ItinerarySlot
from app.models.location import UserLocationPing
from app.models.user import User
from app.schemas.maps import (
    DistanceRequest,
    DistanceResponse,
    DriftAlert,
    LocationPingIn,
    LocationPingOut,
    LocationPingResponse,
)
from app.services.events import event_bus
from app.services.logistics import estimated_travel_mins, haversine_km


router = APIRouter(prefix="/api/maps", tags=["maps"])
settings = get_settings()


async def _google_distance(req: DistanceRequest, api_key: str) -> DistanceResponse | None:
    params = {
        "origins": f"{req.origin.lat},{req.origin.lng}",
        "destinations": f"{req.destination.lat},{req.destination.lng}",
        "mode": req.mode,
        "key": api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get("https://maps.googleapis.com/maps/api/distancematrix/json", params=params)
            r.raise_for_status()
            data = r.json()
            el = data["rows"][0]["elements"][0]
            if el.get("status") != "OK":
                return None
            return DistanceResponse(
                distance_km=el["distance"]["value"] / 1000,
                duration_mins=int(round(el["duration"]["value"] / 60)),
                mode=req.mode,
                provider="google",
            )
    except (httpx.HTTPError, KeyError, IndexError):
        return None


@router.post("/distance", response_model=DistanceResponse)
async def distance(req: DistanceRequest) -> DistanceResponse:
    if settings.google_maps_api_key:
        result = await _google_distance(req, settings.google_maps_api_key)
        if result is not None:
            return result

    km = haversine_km(req.origin.lat, req.origin.lng, req.destination.lat, req.destination.lng)
    mins = estimated_travel_mins(
        req.origin.lat, req.origin.lng, req.destination.lat, req.destination.lng, req.mode
    )
    return DistanceResponse(distance_km=round(km, 2), duration_mins=mins, mode=req.mode, provider="haversine")


def _next_anchor(slots: list[ItinerarySlot], now: datetime) -> Optional[ItinerarySlot]:
    upcoming = [s for s in slots if s.start_at > now and s.lat is not None and s.lng is not None]
    upcoming.sort(key=lambda s: s.start_at)
    return upcoming[0] if upcoming else None


@router.post("/ping", response_model=LocationPingResponse)
def post_ping(
    payload: LocationPingIn,
    itinerary_id: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LocationPingResponse:
    now = payload.recorded_at or datetime.now(timezone.utc)
    ping = UserLocationPing(
        user_id=user.id,
        lat=payload.lat,
        lng=payload.lng,
        speed_kmh=payload.speed_kmh,
        heading=payload.heading,
        recorded_at=now,
    )
    db.add(ping)
    db.commit()
    db.refresh(ping)

    alert: DriftAlert | None = None
    next_slot_id: str | None = None
    projected_arrival: datetime | None = None

    if itinerary_id:
        itinerary = db.execute(
            select(Itinerary).options(selectinload(Itinerary.slots)).where(Itinerary.id == itinerary_id)
        ).scalar_one_or_none()
        if itinerary and itinerary.owner_id == user.id:
            nxt = _next_anchor(list(itinerary.slots), now)
            if nxt is not None:
                next_slot_id = nxt.id
                transit = estimated_travel_mins(payload.lat, payload.lng, nxt.lat, nxt.lng, "driving")
                projected_arrival = now + timedelta(minutes=transit)
                delay = int((projected_arrival - nxt.start_at).total_seconds() // 60)
                if delay > 10:
                    alert = DriftAlert(
                        slot_id=nxt.id,
                        slot_title=nxt.title,
                        scheduled_start_at=nxt.start_at,
                        projected_arrival_at=projected_arrival,
                        delay_mins=delay,
                        severity="critical" if delay > 30 else "warning",
                        message=(
                            f"At current pace you'll arrive at '{nxt.title}' {delay} min late "
                            f"({projected_arrival:%H:%M} vs scheduled {nxt.start_at:%H:%M})."
                        ),
                    )
                    event_bus.publish({
                        "type": "location:drift",
                        "user_id": user.id,
                        "itinerary_id": itinerary.id,
                        "slot_id": nxt.id,
                        "delay_mins": delay,
                    })

    return LocationPingResponse(
        ping=LocationPingOut.model_validate(ping),
        next_anchor_slot_id=next_slot_id,
        projected_arrival_at=projected_arrival,
        alert=alert,
    )


@router.get("/ping/latest", response_model=LocationPingOut | None)
def latest_ping(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LocationPingOut | None:
    row = db.execute(
        select(UserLocationPing)
        .where(UserLocationPing.user_id == user.id)
        .order_by(UserLocationPing.recorded_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return LocationPingOut.model_validate(row) if row else None
