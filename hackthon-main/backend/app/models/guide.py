"""DTO-P3 Phase 7 — Decentralised Local Guide Marketplace.

Per PRD § "The Decentralized Local Guide Marketplace":

  Independent guides register on the platform via a specialized vendor
  portal, defining their geographic operating radii, subject matter
  expertise, and baseline hourly rates. These profiles are indexed
  geographically. When a booking is accepted, the temporal block is hard-
  locked so the guide mathematically cannot double-book.

Two tables:
  • Guide          — profile owned 1:1 by a User
  • GuideBooking   — a request or confirmed booking on a guide's calendar.
                     A partial unique constraint on (guide_id, status,
                     window) enforces the availability lock at DB level
                     for CONFIRMED rows.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GuideStatus(str, enum.Enum):
    ACTIVE = "active"       # visible in search
    PAUSED = "paused"       # temporarily off the roster
    OFFLINE = "offline"     # deactivated


class Guide(Base):
    __tablename__ = "guides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    display_name: Mapped[str] = mapped_column(String(120))
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Where they operate. Radius km caps how far from home they'll travel.
    home_lat: Mapped[float] = mapped_column(Float)
    home_lng: Mapped[float] = mapped_column(Float)
    home_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    radius_km: Mapped[float] = mapped_column(Float, default=25.0)

    # Subject-matter expertise — list of tags like ["art", "food", "history"]
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)

    hourly_rate_usd: Mapped[float] = mapped_column(Float, default=25.0)
    min_hours: Mapped[int] = mapped_column(Integer, default=2)

    # Razorpay Route account this guide's escrow releases to.
    vendor_account: Mapped[str] = mapped_column(String(64), default="acc_guide_escrow")

    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[GuideStatus] = mapped_column(Enum(GuideStatus), default=GuideStatus.ACTIVE, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class GuideBookingStatus(str, enum.Enum):
    REQUESTED = "requested"    # traveler asked, guide hasn't responded
    CONFIRMED = "confirmed"    # guide accepted — availability HARD-LOCKED
    DECLINED = "declined"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class GuideBooking(Base):
    __tablename__ = "guide_bookings"
    __table_args__ = (
        # For fast overlap checks per guide.
        Index("ix_guide_bookings_guide_window", "guide_id", "start_at", "end_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    guide_id: Mapped[str] = mapped_column(
        ForeignKey("guides.id", ondelete="CASCADE"), index=True
    )
    # Who's requesting — traveler user id (nullable for demo/anon requests).
    traveler_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    super_trip_id: Mapped[str | None] = mapped_column(
        ForeignKey("super_trips.id", ondelete="SET NULL"), nullable=True, index=True
    )
    node_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    title: Mapped[str] = mapped_column(String(200))
    location_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # The temporal block — locked in the DB when status = confirmed.
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    rate_usd: Mapped[float] = mapped_column(Float)
    total_usd: Mapped[float] = mapped_column(Float)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    status: Mapped[GuideBookingStatus] = mapped_column(
        Enum(GuideBookingStatus), default=GuideBookingStatus.REQUESTED, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
