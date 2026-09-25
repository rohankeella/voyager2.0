"""DTO-P3 Phase 5 — SuperTrip disruption persistence.

One row per active disruption event ingested from a webhook (or triggered
manually from the operator UI for the demo). The row carries the raw event,
the pre-cascade DAG snapshot, the generated recovery plans, and the applied
plan id (if any). Historical rows are kept for audit even after resolution.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SuperDisruptionKind(str, enum.Enum):
    DELAY = "delay"                # positive delta_mins on a scheduled event
    CANCELLATION = "cancellation"  # source node cancelled outright
    WEATHER = "weather"            # weather-driven closure at destination
    OVERBOOKED = "overbooked"
    CAPACITY = "capacity"
    OTHER = "other"


class SuperDisruptionStatus(str, enum.Enum):
    OPEN = "open"                  # detected, plans generated, awaiting decision
    MITIGATED = "mitigated"        # a recovery plan was applied
    RESOLVED = "resolved"          # naturally cleared (e.g. flight went back on time)
    IGNORED = "ignored"            # operator dismissed


class SuperDisruption(Base):
    __tablename__ = "super_disruptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    super_trip_id: Mapped[str] = mapped_column(
        ForeignKey("super_trips.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[str] = mapped_column(String(64), index=True)

    kind: Mapped[SuperDisruptionKind] = mapped_column(Enum(SuperDisruptionKind))
    status: Mapped[SuperDisruptionStatus] = mapped_column(
        Enum(SuperDisruptionStatus), default=SuperDisruptionStatus.OPEN, index=True
    )
    delta_mins: Mapped[int] = mapped_column(Integer, default=0)   # positive = later
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")

    # Snapshots for audit / rollback. `plans_json` is the list of proposed
    # recovery strategies (see services/recovery_super_trip.py). `applied_plan_id`
    # names the strategy the operator accepted.
    plans_json: Mapped[list] = mapped_column(JSON, default=list)
    applied_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # DAG BEFORE cascade for potential rollback.
    pre_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
