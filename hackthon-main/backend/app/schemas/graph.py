from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.graph import (
    DisruptionKind,
    EdgeKind,
    NodeKind,
    NodeStatus,
    RefundClass,
)


# ---- node CRUD ------------------------------------------------------------


class NodeCreate(BaseModel):
    kind: NodeKind
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    location_label: str | None = None
    lat: float | None = None
    lng: float | None = None
    cost: float = 0.0
    currency: str = "INR"
    refund_class: RefundClass = RefundClass.NON_REFUNDABLE
    change_fee: float = 0.0
    provider_ref: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NodeUpdate(BaseModel):
    kind: NodeKind | None = None
    title: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    location_label: str | None = None
    lat: float | None = None
    lng: float | None = None
    cost: float | None = None
    currency: str | None = None
    refund_class: RefundClass | None = None
    change_fee: float | None = None
    provider_ref: str | None = None
    status: NodeStatus | None = None
    metadata_json: dict[str, Any] | None = None


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    itinerary_id: str
    kind: NodeKind
    title: str
    start_at: datetime
    end_at: datetime
    location_label: str | None
    lat: float | None
    lng: float | None
    cost: float
    currency: str
    refund_class: RefundClass
    change_fee: float
    provider_ref: str | None
    status: NodeStatus
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---- edges ---------------------------------------------------------------


class EdgeCreate(BaseModel):
    from_node_id: str
    to_node_id: str
    edge_kind: EdgeKind = EdgeKind.REQUIRES
    min_buffer_mins: int = Field(default=30, ge=0)


class EdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    itinerary_id: str
    from_node_id: str
    to_node_id: str
    edge_kind: EdgeKind
    min_buffer_mins: int
    created_at: datetime


# ---- graph view ----------------------------------------------------------


class GraphOut(BaseModel):
    itinerary_id: str
    nodes: list[NodeOut]
    edges: list[EdgeOut]


# ---- risks (F-30) --------------------------------------------------------


class BufferRiskOut(BaseModel):
    edge_id: str
    from_node_id: str
    from_title: str
    to_node_id: str
    to_title: str
    actual_buffer_mins: int
    required_buffer_mins: int
    severity: str
    message: str


class RiskReportOut(BaseModel):
    itinerary_id: str
    risks: list[BufferRiskOut]
    at_risk_node_ids: list[str]


# ---- disruptions ---------------------------------------------------------


class DisruptionCreate(BaseModel):
    node_id: str
    kind: DisruptionKind
    delta_mins: int = 0
    note: str | None = None


class DisruptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    itinerary_id: str
    node_id: str
    kind: DisruptionKind
    delta_mins: int
    note: str | None
    is_resolved: bool
    created_at: datetime


# ---- impact analysis (F-26) ----------------------------------------------


class ImpactReport(BaseModel):
    disrupted_node_ids: list[str]
    impacted_node_ids: list[str]
    impacted_nodes: list[NodeOut]


# ---- recovery plans (F-27, F-31) -----------------------------------------


class PlanActionOut(BaseModel):
    node_id: str
    kind: str
    detail: str
    delta_mins: int = 0
    monetary_penalty: float = 0.0


class RecoveryPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    itinerary_id: str
    label: str
    strategy: str
    penalty: float
    cost_delta: float
    time_delta_mins: int
    nodes_modified: int
    actions: list[PlanActionOut]
    summary: str | None
    is_applied: bool
    applied_at: datetime | None
    created_at: datetime


class RecoveryGenerationResponse(BaseModel):
    itinerary_id: str
    disruptions: list[DisruptionOut]
    plans: list[RecoveryPlanOut]


# ---- apply-fix report (F-29) ---------------------------------------------


class ApplyReportOut(BaseModel):
    plan_id: str
    label: str
    strategy: str
    nodes_shifted: int
    nodes_modified: int
    nodes_cancelled: int
    nodes_dropped: int
    edges_removed: int
    residual_conflicts: list[str]
    graph: GraphOut
