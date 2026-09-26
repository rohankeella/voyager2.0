"""DTO-P3 Phase 7 — Local Guide Marketplace endpoints.

  Traveler-facing:
    GET  /api/guides                       search (geo + tags + time window)
    POST /api/guides/{id}/bookings         request a session (creates REQUESTED row)

  Guide-facing:
    POST /api/guides                       register / update my guide profile
    GET  /api/guides/me                    my profile
    GET  /api/guides/me/bookings           incoming requests + confirmed sessions
    POST /api/guides/me/bookings/{id}/accept   flip to CONFIRMED (locks slot)
    POST /api/guides/me/bookings/{id}/decline  flip to DECLINED

Availability lock: `accept_booking` runs an overlap query in a single txn
and refuses if any CONFIRMED booking on the same guide intersects the
requested window. This is the "cryptographic availability lock" from the
PRD — cryptographic in spirit (deterministic + atomic), not literal keys.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.guide import (
    Guide,
    GuideBooking,
    GuideBookingStatus,
    GuideStatus,
)
from app.models.user import User

log = logging.getLogger("routers.guides")
router = APIRouter(prefix="/api/guides", tags=["guides"])


# ---- schemas -------------------------------------------------------------


class GuideProfileIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    headline: str | None = Field(default=None, max_length=200)
    bio: str | None = None
    home_lat: float = Field(ge=-90, le=90)
    home_lng: float = Field(ge=-180, le=180)
    home_city: str | None = Field(default=None, max_length=120)
    country_code: str | None = Field(default=None, max_length=4)
    radius_km: float = Field(default=25.0, gt=0, le=500)
    tags: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    hourly_rate_usd: float = Field(default=25.0, gt=0)
    min_hours: int = Field(default=2, ge=1, le=24)
    status: GuideStatus = GuideStatus.ACTIVE


class GuideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    display_name: str
    headline: str | None
    bio: str | None
    home_lat: float
    home_lng: float
    home_city: str | None
    country_code: str | None
    radius_km: float
    tags: list[str]
    languages: list[str]
    hourly_rate_usd: float
    min_hours: int
    vendor_account: str
    rating: float | None
    review_count: int
    verified: bool
    status: GuideStatus


class GuideSearchHit(GuideOut):
    distance_km: float | None = None
    matched_tags: list[str] = Field(default_factory=list)
    conflicts: bool = False   # true if `available_from`+`available_to` overlap a confirmed booking


class BookingRequestIn(BaseModel):
    start_at: datetime
    end_at: datetime
    title: str = Field(min_length=2, max_length=200)
    location_label: str | None = Field(default=None, max_length=200)
    location_lat: float | None = Field(default=None, ge=-90, le=90)
    location_lng: float | None = Field(default=None, ge=-180, le=180)
    super_trip_id: str | None = None
    node_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    note: str | None = None


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    guide_id: str
    traveler_user_id: str | None
    super_trip_id: str | None
    node_id: str | None
    title: str
    location_label: str | None
    location_lat: float | None
    location_lng: float | None
    start_at: datetime
    end_at: datetime
    rate_usd: float
    total_usd: float
    tags: list[str]
    status: GuideBookingStatus
    note: str | None
    created_at: datetime
    updated_at: datetime
    responded_at: datetime | None


# ---- helpers -------------------------------------------------------------


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _hours_between(start: datetime, end: datetime) -> float:
    return max(0.0, (end - start).total_seconds() / 3600.0)


def _guide_for_user(db: Session, user: User) -> Guide | None:
    return db.query(Guide).filter(Guide.user_id == user.id).first()


def _overlap_exists(db: Session, guide_id: str, start: datetime, end: datetime, exclude_id: str | None = None) -> bool:
    q = db.query(GuideBooking).filter(
        GuideBooking.guide_id == guide_id,
        GuideBooking.status == GuideBookingStatus.CONFIRMED,
        # Overlap = NOT (end <= start OR start >= end)
        GuideBooking.start_at < end,
        GuideBooking.end_at > start,
    )
    if exclude_id:
        q = q.filter(GuideBooking.id != exclude_id)
    return db.query(q.exists()).scalar() or False


# ---- registration / profile ---------------------------------------------


@router.post("", response_model=GuideOut, status_code=status.HTTP_201_CREATED)
def upsert_guide(
    body: GuideProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GuideOut:
    guide = _guide_for_user(db, user)
    if guide:
        # In-place update
        for k, v in body.model_dump().items():
            setattr(guide, k, v)
    else:
        guide = Guide(user_id=user.id, **body.model_dump())
        db.add(guide)
    db.commit()
    db.refresh(guide)
    return GuideOut.model_validate(guide)


@router.get("/me", response_model=GuideOut)
def get_my_guide(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GuideOut:
    guide = _guide_for_user(db, user)
    if not guide:
        raise HTTPException(status_code=404, detail="no guide profile — register first via POST /api/guides")
    return GuideOut.model_validate(guide)


# ---- search --------------------------------------------------------------


@router.get("", response_model=list[GuideSearchHit])
def search_guides(
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    tags: str | None = Query(None, description="comma-separated tag filter"),
    max_distance_km: float | None = Query(None, gt=0, le=500),
    available_from: datetime | None = Query(None, alias="from"),
    available_to: datetime | None = Query(None, alias="to"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[GuideSearchHit]:
    """Search by geo (lat/lng + max_distance_km), tag intersection, and
    optional time window that filters out guides already booked then.
    Result rank: (matched tag count desc, distance asc, rating desc).
    """
    q = db.query(Guide).filter(Guide.status == GuideStatus.ACTIVE)
    rows = q.all()

    tag_set = [t.strip().lower() for t in (tags or "").split(",") if t.strip()]

    hits: list[GuideSearchHit] = []
    for g in rows:
        # Geo filter
        dist_km: float | None = None
        if lat is not None and lng is not None:
            dist_km = _haversine_km(lat, lng, g.home_lat, g.home_lng)
            cap = max_distance_km if max_distance_km is not None else g.radius_km
            if dist_km > cap:
                continue

        # Tag filter (soft — a matched_tags of [] still passes if no tags queried)
        matched = [t for t in (g.tags or []) if t.lower() in tag_set] if tag_set else []
        if tag_set and not matched:
            continue

        # Time window — mark conflicts (don't hide; UI can still show them faded).
        conflicts = False
        if available_from and available_to:
            conflicts = _overlap_exists(db, g.id, available_from, available_to)

        hit = GuideSearchHit(
            **{
                **GuideOut.model_validate(g).model_dump(),
                "distance_km": round(dist_km, 1) if dist_km is not None else None,
                "matched_tags": matched,
                "conflicts": conflicts,
            }
        )
        hits.append(hit)

    hits.sort(key=lambda h: (-len(h.matched_tags), h.distance_km or 1e9, -(h.rating or 0)))
    return hits[:limit]


# ---- traveler → booking request -----------------------------------------


@router.post("/{guide_id}/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def request_booking(
    guide_id: str,
    body: BookingRequestIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookingOut:
    guide = db.get(Guide, guide_id)
    if not guide:
        raise HTTPException(status_code=404, detail="guide not found")
    if guide.status != GuideStatus.ACTIVE:
        raise HTTPException(status_code=409, detail=f"guide is {guide.status.value}")
    if body.end_at <= body.start_at:
        raise HTTPException(status_code=422, detail="end_at must be after start_at")

    hours = _hours_between(body.start_at, body.end_at)
    if hours < guide.min_hours:
        raise HTTPException(
            status_code=422,
            detail=f"minimum session is {guide.min_hours}h for this guide (requested {hours:.1f}h)",
        )

    total = round(hours * guide.hourly_rate_usd, 2)

    booking = GuideBooking(
        guide_id=guide.id,
        traveler_user_id=user.id,
        super_trip_id=body.super_trip_id,
        node_id=body.node_id,
        title=body.title,
        location_label=body.location_label,
        location_lat=body.location_lat,
        location_lng=body.location_lng,
        start_at=body.start_at,
        end_at=body.end_at,
        rate_usd=guide.hourly_rate_usd,
        total_usd=total,
        tags=body.tags,
        note=body.note,
        status=GuideBookingStatus.REQUESTED,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    log.info("Guide booking requested: %s guide=%s traveler=%s", booking.id, guide.id, user.id)
    return BookingOut.model_validate(booking)


# ---- guide dashboard -----------------------------------------------------


@router.get("/me/bookings", response_model=list[BookingOut])
def my_bookings(
    status_filter: GuideBookingStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BookingOut]:
    guide = _guide_for_user(db, user)
    if not guide:
        raise HTTPException(status_code=404, detail="no guide profile")
    q = db.query(GuideBooking).filter(GuideBooking.guide_id == guide.id)
    if status_filter is not None:
        q = q.filter(GuideBooking.status == status_filter)
    rows = q.order_by(GuideBooking.start_at.asc()).all()
    return [BookingOut.model_validate(r) for r in rows]


@router.post("/me/bookings/{booking_id}/accept", response_model=BookingOut)
def accept_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookingOut:
    guide = _guide_for_user(db, user)
    if not guide:
        raise HTTPException(status_code=404, detail="no guide profile")
    booking = db.get(GuideBooking, booking_id)
    if not booking or booking.guide_id != guide.id:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking.status != GuideBookingStatus.REQUESTED:
        raise HTTPException(status_code=409, detail=f"cannot accept from {booking.status.value}")

    # Cryptographic availability lock — reject if any confirmed booking overlaps.
    if _overlap_exists(db, guide.id, booking.start_at, booking.end_at, exclude_id=booking.id):
        raise HTTPException(
            status_code=409,
            detail="overlapping confirmed booking — availability lock refused this slot",
        )

    booking.status = GuideBookingStatus.CONFIRMED
    booking.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    log.info("Guide booking confirmed: %s", booking.id)
    return BookingOut.model_validate(booking)


@router.post("/me/bookings/{booking_id}/decline", response_model=BookingOut)
def decline_booking(
    booking_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookingOut:
    guide = _guide_for_user(db, user)
    if not guide:
        raise HTTPException(status_code=404, detail="no guide profile")
    booking = db.get(GuideBooking, booking_id)
    if not booking or booking.guide_id != guide.id:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking.status != GuideBookingStatus.REQUESTED:
        raise HTTPException(status_code=409, detail=f"cannot decline from {booking.status.value}")
    booking.status = GuideBookingStatus.DECLINED
    booking.responded_at = datetime.now(timezone.utc)
    reason = body.get("reason") if isinstance(body, dict) else None
    if reason:
        booking.note = f"[decline reason] {reason}"
    db.commit()
    db.refresh(booking)
    return BookingOut.model_validate(booking)
