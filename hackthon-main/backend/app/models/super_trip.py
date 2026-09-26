"""DTO-P3 SuperTrip persistence.

Stores the full agent-planned DAG as a JSON blob so the Executor/Supervisor
can hydrate it on demand and the Operator Command Center can iterate over
active trips. Keeps the graph shape faithful to the DTO-P3 wire schema
(`app.schemas.super_trip.SuperTrip`) instead of normalising into
ItineraryNode/Edge rows — those are for the older P5 flow.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SuperTripStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"    # planned but user hasn't approved
    APPROVED = "approved"                 # user clicked Review & Approve
    ACTIVE = "active"                     # trip in progress
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SuperTripRecord(Base):
    """One row per planned trip. Whole DAG lives inside `payload_json`."""

    __tablename__ = "super_trips"

    # Application-facing id (matches the DAG's super_trip_id, e.g. ST-PARIS-9F).
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Owning traveler — nullable to allow anon planning demos.
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    # DTO-P3 traveler_id string kept in sync with the DAG (USR-<user_id>).
    traveler_id: Mapped[str] = mapped_column(String(64), index=True)

    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[SuperTripStatus] = mapped_column(
        Enum(SuperTripStatus), default=SuperTripStatus.PENDING_REVIEW, index=True
    )
    total_cost_usd: Mapped[float] = mapped_column(default=0.0)
    max_budget_usd: Mapped[float] = mapped_column(default=0.0)
    node_count: Mapped[int] = mapped_column(default=0)

    # Full SuperTrip JSON per `app.schemas.super_trip.SuperTrip`.
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Original prompt + agent trace for auditability / replay.
    source_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_trace: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Auto-generate id from the DAG's super_trip_id if the caller omits it.
    def __init__(self, **kwargs):
        if "id" not in kwargs and "payload_json" in kwargs:
            kwargs["id"] = kwargs["payload_json"].get("super_trip_id") or _uuid()
        super().__init__(**kwargs)
