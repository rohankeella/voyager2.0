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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CapacitySourceKind(str, enum.Enum):
    HOUSING = "HOUSING"     # hotels, hostels, homestays
    TRANSIT = "TRANSIT"     # metros, buses, rideshare pickups
    VENUE = "VENUE"         # attractions, restaurants, event halls


class NudgeKind(str, enum.Enum):
    DISCOUNT = "DISCOUNT"
    BADGE = "BADGE"
    PRIORITY_PASS = "PRIORITY_PASS"


class Zone(Base):
    """A geographic zone used for the operator heatmap. Coarser than a lat/lng
    point, finer than a full city — think 'Gion west' or 'Kuta beach strip'.

    We model a zone as a circle (centre + radius). More expressive polygons
    could come later; for hackathon math this keeps the "which zone is this
    in?" lookup to a single haversine.
    """

    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(160))
    center_lat: Mapped[float] = mapped_column(Float)
    center_lng: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float, default=1.0)
    # Aggregate designed capacity across all sources in the zone — used as
    # denominator for density %.
    total_capacity: Mapped[int] = mapped_column(Integer, default=1000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    metrics = relationship("CapacityMetric", back_populates="zone", cascade="all, delete-orphan")
    events = relationship("ZoneEvent", back_populates="zone", cascade="all, delete-orphan")


class CapacityMetric(Base):
    """Time-series data point for a zone from a single source. Must support
    5,000 ingests/sec/zone (NFR) — kept lightweight and indexed on
    (zone_id, recorded_at DESC) for the forecaster's window queries."""

    __tablename__ = "capacity_metrics"
    __table_args__ = (
        Index("ix_metrics_zone_time", "zone_id", "recorded_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), index=True)
    source_kind: Mapped[CapacitySourceKind] = mapped_column(Enum(CapacitySourceKind), index=True)
    source_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    occupancy_count: Mapped[int] = mapped_column(Integer, default=0)
    capacity_max: Mapped[int] = mapped_column(Integer, default=0)
    # Precomputed (occupancy_count / capacity_max) * 100. Storing avoids
    # divide-by-zero + repeated math on read.
    density_pct: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    zone = relationship("Zone", back_populates="metrics")


class ZoneEvent(Base):
    """Scheduled event in a zone (concert end, marathon, festival). Drives
    F-17 (30-min pre-end congestion elevation) and F-18 (staggered
    departures)."""

    __tablename__ = "zone_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expected_attendance: Mapped[int] = mapped_column(Integer, default=500)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    zone = relationship("Zone", back_populates="events")


class Nudge(Base):
    """A pre-defined incentive available to attach to alternate-zone
    recommendations (F-20). Operators register nudges once; the balancer
    picks the best-matching active one at rec-time."""

    __tablename__ = "nudges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[NudgeKind] = mapped_column(Enum(NudgeKind), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(400), nullable=True)
    # If null, valid for any low-density zone. Otherwise, only issued when
    # the alternative recommended zone matches.
    target_zone_id: Mapped[str | None] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"), nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSON, default=dict)  # e.g. {"code":"OFFPEAK10","pct_off":10}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NudgeIssuance(Base):
    """Audit row — records each time a nudge was surfaced to a user for a
    specific alternative zone. Lets us dedupe and measure conversion later."""

    __tablename__ = "nudge_issuances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    nudge_id: Mapped[str] = mapped_column(ForeignKey("nudges.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    alternative_zone_id: Mapped[str] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"), index=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
