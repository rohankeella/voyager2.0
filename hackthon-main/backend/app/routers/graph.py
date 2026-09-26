"""P5 endpoints — Itinerary Dependency Graph & Recovery Engine.

Route surface (all under an existing itinerary):

  Structure (F-25)
    POST   /api/itineraries/{id}/nodes
    PATCH  /api/itineraries/{id}/nodes/{node_id}
    DELETE /api/itineraries/{id}/nodes/{node_id}
    POST   /api/itineraries/{id}/edges
    DELETE /api/itineraries/{id}/edges/{edge_id}
    GET    /api/itineraries/{id}/graph

  Risk (F-30)
    GET    /api/itineraries/{id}/risks             — buffer flagging
    POST   /api/itineraries/{id}/risks/apply       — persist AT_RISK status

  Disruption + impact (F-26)
    POST   /api/itineraries/{id}/disruptions       — one or many
    GET    /api/itineraries/{id}/impact            — downstream analysis

  Recovery (F-27, F-31)
    POST   /api/itineraries/{id}/recovery          — generate + persist ranked plans

  Apply fix (F-29)
    POST   /api/itineraries/{id}/recovery/{plan_id}/apply
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.graph import (
    Disruption,
    ItineraryEdge,
    ItineraryNode,
    NodeStatus,
    RecoveryPlan,
)
from app.models.itinerary import Itinerary
from app.models.user import User
from app.schemas.graph import (
    ApplyReportOut,
    BufferRiskOut,
    DisruptionCreate,
    DisruptionOut,
    EdgeCreate,
    EdgeOut,
    GraphOut,
    ImpactReport,
    NodeCreate,
    NodeOut,
    NodeUpdate,
    PlanActionOut,
    RecoveryGenerationResponse,
    RecoveryPlanOut,
    RiskReportOut,
)
from app.services.events import event_bus
from app.services.graph import DependencyGraph
from app.services.recovery import (
    STRATEGY_WEIGHTS,
    generate_recovery_plans,
)
from app.services.rewrite import apply_plan
from app.services.risk import (
    DEFAULT_SAFETY_BUFFER_MINS,
    assess_buffers,
    collect_at_risk_node_ids,
)


router = APIRouter(prefix="/api/itineraries/{itinerary_id}", tags=["graph"])


# --- helpers ----------------------------------------------------------------


def _load_itinerary(db: Session, itinerary_id: str, user: User) -> Itinerary:
    it = db.get(Itinerary, itinerary_id)
    if it is None:
        raise HTTPException(status_code=404, detail="itinerary not found")
    if it.owner_id != user.id:
        raise HTTPException(status_code=403, detail="not your itinerary")
    return it


def _load_graph(db: Session, itinerary_id: str) -> DependencyGraph:
    nodes = list(
        db.execute(select(ItineraryNode).where(ItineraryNode.itinerary_id == itinerary_id))
        .scalars()
        .all()
    )
    edges = list(
        db.execute(select(ItineraryEdge).where(ItineraryEdge.itinerary_id == itinerary_id))
        .scalars()
        .all()
    )
    return DependencyGraph.build(nodes, edges)


# --- nodes (F-25) -----------------------------------------------------------


@router.post("/nodes", response_model=NodeOut, status_code=status.HTTP_201_CREATED)
def add_node(
    itinerary_id: str,
    payload: NodeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NodeOut:
    _load_itinerary(db, itinerary_id, user)
    if payload.end_at <= payload.start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    node = ItineraryNode(itinerary_id=itinerary_id, **payload.model_dump())
    db.add(node)
    db.commit()
    db.refresh(node)
    event_bus.publish({"type": "graph:changed", "action": "node_added", "itinerary_id": itinerary_id})
    return NodeOut.model_validate(node)


@router.patch("/nodes/{node_id}", response_model=NodeOut)
def update_node(
    itinerary_id: str,
    node_id: str,
    payload: NodeUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NodeOut:
    _load_itinerary(db, itinerary_id, user)
    node = db.get(ItineraryNode, node_id)
    if node is None or node.itinerary_id != itinerary_id:
        raise HTTPException(status_code=404, detail="node not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(node, k, v)
    if node.end_at <= node.start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    db.commit()
    db.refresh(node)
    return NodeOut.model_validate(node)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(
    itinerary_id: str,
    node_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _load_itinerary(db, itinerary_id, user)
    node = db.get(ItineraryNode, node_id)
    if node is None or node.itinerary_id != itinerary_id:
        raise HTTPException(status_code=404, detail="node not found")
    db.delete(node)
    db.commit()


# --- edges ------------------------------------------------------------------


@router.post("/edges", response_model=EdgeOut, status_code=status.HTTP_201_CREATED)
def add_edge(
    itinerary_id: str,
    payload: EdgeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EdgeOut:
    _load_itinerary(db, itinerary_id, user)
    from_node = db.get(ItineraryNode, payload.from_node_id)
    to_node = db.get(ItineraryNode, payload.to_node_id)
    if not from_node or not to_node or from_node.itinerary_id != itinerary_id or to_node.itinerary_id != itinerary_id:
        raise HTTPException(status_code=400, detail="both nodes must belong to this itinerary")

    graph = _load_graph(db, itinerary_id)
    if graph.would_create_cycle(payload.from_node_id, payload.to_node_id):
        raise HTTPException(status_code=400, detail="edge would create a cycle")

    edge = ItineraryEdge(itinerary_id=itinerary_id, **payload.model_dump())
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return EdgeOut.model_validate(edge)


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_edge(
    itinerary_id: str,
    edge_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _load_itinerary(db, itinerary_id, user)
    edge = db.get(ItineraryEdge, edge_id)
    if edge is None or edge.itinerary_id != itinerary_id:
        raise HTTPException(status_code=404, detail="edge not found")
    db.delete(edge)
    db.commit()


@router.get("/graph", response_model=GraphOut)
def get_graph(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GraphOut:
    _load_itinerary(db, itinerary_id, user)
    graph = _load_graph(db, itinerary_id)
    return GraphOut(
        itinerary_id=itinerary_id,
        nodes=[NodeOut.model_validate(n) for n in graph.nodes.values()],
        edges=[EdgeOut.model_validate(e) for e in graph.edges],
    )


# --- F-30 risks -------------------------------------------------------------


@router.get("/risks", response_model=RiskReportOut)
def list_risks(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskReportOut:
    _load_itinerary(db, itinerary_id, user)
    graph = _load_graph(db, itinerary_id)
    risks = assess_buffers(graph)
    return RiskReportOut(
        itinerary_id=itinerary_id,
        risks=[BufferRiskOut(**r.__dict__) for r in risks],
        at_risk_node_ids=sorted(collect_at_risk_node_ids(risks)),
    )


@router.post("/risks/apply", response_model=RiskReportOut)
def apply_risk_labels(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskReportOut:
    """Persist AT_RISK status on each affected node — lets the UI badge
    the DAG visually without recomputing on every render."""
    _load_itinerary(db, itinerary_id, user)
    graph = _load_graph(db, itinerary_id)
    risks = assess_buffers(graph)
    at_risk_ids = collect_at_risk_node_ids(risks)

    for node in graph.nodes.values():
        if node.id in at_risk_ids and node.status == NodeStatus.SCHEDULED:
            node.status = NodeStatus.AT_RISK
        elif node.id not in at_risk_ids and node.status == NodeStatus.AT_RISK:
            node.status = NodeStatus.SCHEDULED
    db.commit()
    return RiskReportOut(
        itinerary_id=itinerary_id,
        risks=[BufferRiskOut(**r.__dict__) for r in risks],
        at_risk_node_ids=sorted(at_risk_ids),
    )


# --- disruptions + F-26 impact ---------------------------------------------


@router.post("/disruptions", response_model=list[DisruptionOut], status_code=status.HTTP_201_CREATED)
def declare_disruptions(
    itinerary_id: str,
    payload: List[DisruptionCreate],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DisruptionOut]:
    """Accept one or many disruptions in a single call — F-31 multi-root
    is a natural entry point here."""
    _load_itinerary(db, itinerary_id, user)
    if not payload:
        raise HTTPException(status_code=400, detail="at least one disruption required")

    graph = _load_graph(db, itinerary_id)
    for p in payload:
        if p.node_id not in graph.nodes:
            raise HTTPException(status_code=400, detail=f"unknown node {p.node_id}")

    created: list[Disruption] = []
    for p in payload:
        d = Disruption(itinerary_id=itinerary_id, **p.model_dump())
        db.add(d)
        created.append(d)
        graph.nodes[p.node_id].status = NodeStatus.DISRUPTED

    # F-26: mark every downstream node as IMPACTED so the UI can render the wave.
    for nid in graph.downstream([p.node_id for p in payload]):
        node = graph.nodes[nid]
        if node.status not in (NodeStatus.DISRUPTED, NodeStatus.REPLACED):
            node.status = NodeStatus.IMPACTED

    db.commit()
    for d in created:
        db.refresh(d)
    event_bus.publish({"type": "graph:changed", "action": "disrupted", "itinerary_id": itinerary_id, "count": len(created)})
    return [DisruptionOut.model_validate(d) for d in created]


@router.get("/impact", response_model=ImpactReport)
def get_impact(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImpactReport:
    _load_itinerary(db, itinerary_id, user)
    graph = _load_graph(db, itinerary_id)
    active_disruptions = list(
        db.execute(
            select(Disruption).where(
                Disruption.itinerary_id == itinerary_id,
                Disruption.is_resolved == False,  # noqa: E712
            )
        )
        .scalars()
        .all()
    )
    disrupted_ids = [d.node_id for d in active_disruptions]
    impacted_ids = graph.downstream(disrupted_ids)
    impacted_nodes = [graph.nodes[nid] for nid in impacted_ids if nid in graph.nodes]
    return ImpactReport(
        disrupted_node_ids=disrupted_ids,
        impacted_node_ids=impacted_ids,
        impacted_nodes=[NodeOut.model_validate(n) for n in impacted_nodes],
    )


# --- F-27 + F-31 recovery ---------------------------------------------------


@router.post("/recovery", response_model=RecoveryGenerationResponse)
def generate_recovery(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecoveryGenerationResponse:
    _load_itinerary(db, itinerary_id, user)
    graph = _load_graph(db, itinerary_id)

    active = list(
        db.execute(
            select(Disruption).where(
                Disruption.itinerary_id == itinerary_id,
                Disruption.is_resolved == False,  # noqa: E712
            )
        )
        .scalars()
        .all()
    )
    if not active:
        raise HTTPException(status_code=400, detail="no active disruptions on this itinerary")

    drafts = generate_recovery_plans(graph, active)

    # Persist so `/apply` has a stable id.
    persisted: list[RecoveryPlan] = []
    for d in drafts:
        weights = STRATEGY_WEIGHTS.get(d.strategy, STRATEGY_WEIGHTS["least_impact"])
        row = RecoveryPlan(
            itinerary_id=itinerary_id,
            label=d.label,
            strategy=d.strategy,
            penalty=d.penalty(weights),
            cost_delta=d.cost_delta,
            time_delta_mins=d.time_delta_mins,
            nodes_modified=d.nodes_modified,
            actions=[a.to_dict() for a in d.actions],
            summary=d.summary,
        )
        db.add(row)
        persisted.append(row)
    db.commit()
    for p in persisted:
        db.refresh(p)

    return RecoveryGenerationResponse(
        itinerary_id=itinerary_id,
        disruptions=[DisruptionOut.model_validate(d) for d in active],
        plans=[
            RecoveryPlanOut(
                id=p.id,
                itinerary_id=p.itinerary_id,
                label=p.label,
                strategy=p.strategy,
                penalty=p.penalty,
                cost_delta=p.cost_delta,
                time_delta_mins=p.time_delta_mins,
                nodes_modified=p.nodes_modified,
                actions=[PlanActionOut(**a) for a in (p.actions or [])],
                summary=p.summary,
                is_applied=p.is_applied,
                applied_at=p.applied_at,
                created_at=p.created_at,
            )
            for p in persisted
        ],
    )


# --- F-29 apply fix ---------------------------------------------------------


@router.post("/recovery/{plan_id}/apply", response_model=ApplyReportOut)
def apply_recovery_plan(
    itinerary_id: str,
    plan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplyReportOut:
    _load_itinerary(db, itinerary_id, user)
    plan = db.get(RecoveryPlan, plan_id)
    if plan is None or plan.itinerary_id != itinerary_id:
        raise HTTPException(status_code=404, detail="plan not found")
    if plan.is_applied:
        raise HTTPException(status_code=409, detail="plan already applied")

    graph = _load_graph(db, itinerary_id)
    active_disruptions = list(
        db.execute(
            select(Disruption).where(
                Disruption.itinerary_id == itinerary_id,
                Disruption.is_resolved == False,  # noqa: E712
            )
        )
        .scalars()
        .all()
    )

    report = apply_plan(
        db=db,
        plan=plan,
        nodes_by_id=graph.nodes,
        edges=graph.edges,
        disruptions=active_disruptions,
    )
    db.commit()

    # Rebuild the fresh graph so the response matches the new state exactly.
    fresh = _load_graph(db, itinerary_id)
    event_bus.publish({"type": "graph:changed", "action": "recovery_applied", "itinerary_id": itinerary_id, "plan_id": plan.id})
    return ApplyReportOut(
        plan_id=report.plan_id,
        label=report.label,
        strategy=report.strategy,
        nodes_shifted=report.nodes_shifted,
        nodes_modified=report.nodes_modified,
        nodes_cancelled=report.nodes_cancelled,
        nodes_dropped=report.nodes_dropped,
        edges_removed=report.edges_removed,
        residual_conflicts=report.residual_conflicts,
        graph=GraphOut(
            itinerary_id=itinerary_id,
            nodes=[NodeOut.model_validate(n) for n in fresh.nodes.values()],
            edges=[EdgeOut.model_validate(e) for e in fresh.edges],
        ),
    )
