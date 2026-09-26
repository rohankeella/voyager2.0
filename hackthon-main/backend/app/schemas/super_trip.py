"""DTO-P3 SuperTrip DAG wire format.

Strict JSON schema per the PRD §"System Data Schemas and Execution Constraints".
This is what agents (Planner/Executor/Supervisor) emit and what the frontend
3D globe / timeline / operator Gantt consume. The existing SQLAlchemy models
(ItineraryNode/ItineraryEdge/Disruption/RecoveryPlan) stay unchanged — this
module is the serialisation contract that sits on top.

Example:

    {
      "super_trip_id": "ST-9982-XYZ",
      "traveler_id": "USR-1029",
      "status": "active",
      "global_constraints": {
        "max_budget_usd": 5000,
        "start_date": "2027-05-10T08:00:00Z",
        "end_date":   "2027-05-20T22:00:00Z"
      },
      "nodes": [
        {
          "node_id": "N-01-FLIGHT",
          "type": "amadeus_flight_order",
          "status": "confirmed",
          "execution_data": {...},
          "depends_on": [],
          "financials": {...}
        }
      ]
    }
"""

from __future__ import annotations

import enum
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---- enums ----------------------------------------------------------------


class NodeType(str, enum.Enum):
    """Every node type must map to a tool the Executor Agent can invoke."""

    AMADEUS_FLIGHT_OFFER = "amadeus_flight_offer"      # search-only, unpriced
    AMADEUS_FLIGHT_ORDER = "amadeus_flight_order"      # confirmed reservation
    AMADEUS_HOTEL_OFFER = "amadeus_hotel_offer"
    AMADEUS_HOTEL_BOOKING = "amadeus_hotel_booking"
    OTP_GROUND_TRANSFER = "otp_ground_transfer"         # ground transit leg
    ACTIVITY = "activity"                                # generic activity (museum, tour)
    GUIDE_SESSION = "guide_session"                     # local-guide booking
    MEAL = "meal"                                        # restaurant / culinary
    CUSTOM = "custom"


class NodeStatus(str, enum.Enum):
    PENDING = "pending"           # created but nothing booked yet
    CONFIRMED = "confirmed"       # Executor got a real vendor confirmation
    ACTIVE = "active"             # in-progress (traveler is doing this now)
    AT_RISK = "at_risk"           # downstream of a disruption, timeline shifted
    COMPLETED = "completed"
    DISRUPTED = "disrupted"       # Disruption Agent flagged this
    CANCELLED = "cancelled"
    REPLACED = "replaced"         # superseded by a recovery pivot


class TripStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"     # awaits HITL user approval
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    ESCROWED = "escrowed"
    ROUTED = "routed"           # funds disbursed to vendor via split payment
    REFUNDED = "refunded"
    FAILED = "failed"


# ---- sub-models -----------------------------------------------------------


class GlobalConstraints(BaseModel):
    """User-defined bounds the trip must stay within — surfaced to Supervisor."""

    max_budget_usd: float = Field(gt=0)
    start_date: datetime
    end_date: datetime
    home_location: str | None = None          # e.g. "Bangalore, IN"
    traveler_count: int = Field(default=1, ge=1, le=20)
    preferences: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _end_after_start(self) -> "GlobalConstraints":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class NodeFinancials(BaseModel):
    cost_usd: float = Field(default=0.0, ge=0)
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    vendor_account: str | None = None         # split-payment destination account
    razorpay_transfer_id: str | None = None   # populated after Razorpay Route call


class NodeExecutionData(BaseModel):
    """Free-form execution payload — shape depends on `NodeType`.

    Common fields (present on most types):
      • start_time / end_time — ISO-8601 timestamps
      • location_label — human-readable place
      • lat / lng — coordinates for map rendering
      • route_geometry — encoded polyline (OTP transfers only)
      • pnr_number — Amadeus confirmed order (flight/hotel)
    """

    model_config = ConfigDict(extra="allow")

    start_time: datetime | None = None
    end_time: datetime | None = None
    location_label: str | None = None
    lat: float | None = None
    lng: float | None = None
    route_geometry: str | None = None
    pnr_number: str | None = None


class TripNode(BaseModel):
    """A single vertex in the SuperTrip DAG."""

    node_id: str = Field(pattern=r"^N-\d{2,3}-[A-Z_]+$", description="e.g. N-01-FLIGHT")
    type: NodeType
    status: NodeStatus = NodeStatus.PENDING
    execution_data: NodeExecutionData
    depends_on: list[str] = Field(default_factory=list, description="node_ids this node depends on")
    financials: NodeFinancials = Field(default_factory=NodeFinancials)

    # optional HITL / display hints
    title: str | None = None
    description: str | None = None
    requires_approval: bool = False

    @field_validator("depends_on")
    @classmethod
    def _no_self_dep(cls, v: list[str], info: Any) -> list[str]:
        node_id = info.data.get("node_id") if hasattr(info, "data") else None
        if node_id and node_id in v:
            raise ValueError(f"{node_id} cannot depend on itself")
        return v


class SuperTrip(BaseModel):
    """The full DAG wire format — what agents produce & consumers render."""

    super_trip_id: str = Field(pattern=r"^ST-[A-Z0-9\-]+$")
    traveler_id: str = Field(pattern=r"^USR-[A-Za-z0-9\-]+$")
    status: TripStatus = TripStatus.DRAFT
    global_constraints: GlobalConstraints
    nodes: list[TripNode]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # ---- validators ------------------------------------------------------

    @model_validator(mode="after")
    def _validate_dag(self) -> "SuperTrip":
        ids = {n.node_id for n in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("duplicate node_id detected")

        # every depends_on target must resolve
        for n in self.nodes:
            for dep in n.depends_on:
                if dep not in ids:
                    raise ValueError(f"node {n.node_id} depends on unknown {dep}")

        # no cycles — DFS cycle detection
        adj: dict[str, list[str]] = {n.node_id: list(n.depends_on) for n in self.nodes}
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {nid: WHITE for nid in adj}

        def dfs(u: str) -> None:
            color[u] = GRAY
            for v in adj[u]:
                if color[v] == GRAY:
                    raise ValueError(f"cycle detected involving {u} -> {v}")
                if color[v] == WHITE:
                    dfs(v)
            color[u] = BLACK

        for nid in adj:
            if color[nid] == WHITE:
                dfs(nid)
        return self

    # ---- utilities the agents use ---------------------------------------

    def topological_order(self) -> list[str]:
        """Kahn's algorithm — returns node_ids in dependency-safe order.

        Node A comes before node B if B.depends_on contains A.
        """
        indeg: dict[str, int] = {n.node_id: 0 for n in self.nodes}
        rev: dict[str, list[str]] = {n.node_id: [] for n in self.nodes}
        for n in self.nodes:
            for dep in n.depends_on:
                indeg[n.node_id] += 1
                rev[dep].append(n.node_id)

        queue = [nid for nid, d in indeg.items() if d == 0]
        order: list[str] = []
        while queue:
            u = queue.pop(0)
            order.append(u)
            for v in rev[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    queue.append(v)
        if len(order) != len(self.nodes):
            raise ValueError("topological_order failed — DAG invariant broken")
        return order

    def descendants(self, node_id: str) -> set[str]:
        """All nodes that (transitively) depend on `node_id`. Used by the
        Disruption Agent to compute a delay's blast radius."""
        rev: dict[str, list[str]] = {n.node_id: [] for n in self.nodes}
        for n in self.nodes:
            for dep in n.depends_on:
                rev[dep].append(n.node_id)

        seen: set[str] = set()
        stack = list(rev.get(node_id, []))
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(rev.get(n, []))
        return seen

    def total_cost_usd(self) -> float:
        return sum(n.financials.cost_usd for n in self.nodes)

    def within_budget(self) -> bool:
        return self.total_cost_usd() <= self.global_constraints.max_budget_usd


# ---- id helpers -----------------------------------------------------------


_NODE_KIND_ABBR = {
    NodeType.AMADEUS_FLIGHT_OFFER: "FLIGHT",
    NodeType.AMADEUS_FLIGHT_ORDER: "FLIGHT",
    NodeType.AMADEUS_HOTEL_OFFER: "HOTEL",
    NodeType.AMADEUS_HOTEL_BOOKING: "HOTEL",
    NodeType.OTP_GROUND_TRANSFER: "TRANSIT",
    NodeType.ACTIVITY: "ACTIVITY",
    NodeType.GUIDE_SESSION: "GUIDE",
    NodeType.MEAL: "MEAL",
    NodeType.CUSTOM: "CUSTOM",
}


def make_node_id(index: int, node_type: NodeType) -> str:
    """Deterministic node_id per PRD example (N-01-FLIGHT, N-02-TRANSIT)."""
    return f"N-{index:02d}-{_NODE_KIND_ABBR[node_type]}"


def make_super_trip_id(seed: str | None = None) -> str:
    """`ST-<8char>-<4char>` — stable enough for the demo. Real prod would use
    a monotonic ID generator."""
    import secrets

    if seed:
        clean = re.sub(r"[^A-Z0-9]", "", seed.upper())[:8] or "TRIP"
        return f"ST-{clean}-{secrets.token_hex(2).upper()}"
    return f"ST-{secrets.token_hex(4).upper()}-{secrets.token_hex(2).upper()}"
