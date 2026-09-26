import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NodeKind(str, enum.Enum):
    FLIGHT = "FLIGHT"
    TRAIN = "TRAIN"
    TRANSFER = "TRANSFER"
    HOTEL = "HOTEL"
    ACTIVITY = "ACTIVITY"
    MEAL = "MEAL"
    GENERIC = "GENERIC"


class NodeStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    AT_RISK = "AT_RISK"          # F-30: buffer below safety threshold
    IMPACTED = "IMPACTED"        # F-26: downstream of a disrupted node
    DISRUPTED = "DISRUPTED"      # explicitly broken (delay/cancel/weather)
    REPLACED = "REPLACED"        # superseded by a recovery plan node


class EdgeKind(str, enum.Enum):
    """How strict is this dependency?

    REQUIRES  — target cannot happen without source (hard dependency).
    SEQUENCED — target should follow source (soft; a delay just shifts it).
    OPTIONAL  — nice-to-have (e.g. a suggested activity in a gap).
    """

    REQUIRES = "REQUIRES"
    SEQUENCED = "SEQUENCED"
    OPTIONAL = "OPTIONAL"


class DisruptionKind(str, enum.Enum):
    DELAY = "DELAY"
    CANCELLATION = "CANCELLATION"
    WEATHER = "WEATHER"
    OVERBOOKED = "OVERBOOKED"
    OTHER = "OTHER"


class RefundClass(str, enum.Enum):
    FULLY_REFUNDABLE = "FULLY_REFUNDABLE"
    PARTIALLY_REFUNDABLE = "PARTIALLY_REFUNDABLE"
    NON_REFUNDABLE = "NON_REFUNDABLE"


class ItineraryNode(Base):
    """F-25 · A single booking anchor in the itinerary DAG.

    Coexists with the P1-era `ItinerarySlot` (which stays a flat list).
    Graph consumers should read from `ItineraryNode` + `ItineraryEdge`.
    """

    __tablename__ = "itinerary_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    itinerary_id: Mapped[str] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[NodeKind] = mapped_column(Enum(NodeKind), index=True)
    title: Mapped[str] = mapped_column(String(200))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    refund_class: Mapped[RefundClass] = mapped_column(
        Enum(RefundClass), default=RefundClass.NON_REFUNDABLE
    )
    change_fee: Mapped[float] = mapped_column(Float, default=0.0)
    provider_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[NodeStatus] = mapped_column(Enum(NodeStatus), default=NodeStatus.SCHEDULED)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ItineraryEdge(Base):
    """F-25 · Directed dependency edge between two `ItineraryNode` rows.

    `min_buffer_mins` is the minimum gap between source.end_at and
    target.start_at; the F-30 risk checker flags edges falling below the
    30-minute default safety threshold.
    """

    __tablename__ = "itinerary_edges"
    __table_args__ = (
        UniqueConstraint("from_node_id", "to_node_id", name="uq_edge_endpoints"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    itinerary_id: Mapped[str] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), index=True
    )
    from_node_id: Mapped[str] = mapped_column(
        ForeignKey("itinerary_nodes.id", ondelete="CASCADE"), index=True
    )
    to_node_id: Mapped[str] = mapped_column(
        ForeignKey("itinerary_nodes.id", ondelete="CASCADE"), index=True
    )
    edge_kind: Mapped[EdgeKind] = mapped_column(Enum(EdgeKind), default=EdgeKind.REQUIRES)
    min_buffer_mins: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Disruption(Base):
    """A declared break on the graph. One or more of these can be active at
    the same time — F-31 recovery handles multiple concurrently."""

    __tablename__ = "disruptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    itinerary_id: Mapped[str] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[str] = mapped_column(
        ForeignKey("itinerary_nodes.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[DisruptionKind] = mapped_column(Enum(DisruptionKind))
    delta_mins: Mapped[int] = mapped_column(Integer, default=0)   # positive = later than scheduled
    note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RecoveryPlan(Base):
    """A proposal returned by the recovery generator. Persisted so the
    frontend can display multiple options and later confirm ("Apply Fix" —
    F-29) with a stable identifier."""

    __tablename__ = "recovery_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    itinerary_id: Mapped[str] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    strategy: Mapped[str] = mapped_column(String(60))  # e.g. "fastest", "cheapest", "least_impact"
    penalty: Mapped[float] = mapped_column(Float)
    cost_delta: Mapped[float] = mapped_column(Float)
    time_delta_mins: Mapped[int] = mapped_column(Integer)
    nodes_modified: Mapped[int] = mapped_column(Integer)
    # Serialised action list — see services.recovery.PlanAction.
    actions: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(String(600), nullable=True)
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
