"""DTO-P3 Phase 5 — SuperTrip disruption ingestion + recovery.

Endpoints:
  POST   /api/super-trips/{id}/disruptions          create a disruption event
                                                    (also runs cascade + generates plans)
  GET    /api/super-trips/{id}/disruptions          list all disruptions on a trip
  POST   /api/super-trips/{id}/disruptions/{d_id}/apply/{plan_id}
                                                    apply a recovery plan → rewrites DAG
  DELETE /api/super-trips/{id}/disruptions/{d_id}   dismiss / mark as ignored

Also:
  POST   /api/webhooks/flight-status                webhook hook (demo-mode ingester)

Auth: either the trip owner or an operator can trigger + apply. Anon requests
are rejected.
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.disruption import (
    SuperDisruption,
    SuperDisruptionKind,
    SuperDisruptionStatus,
)
from app.models.super_trip import SuperTripRecord
from app.models.user import User, UserRole
from app.schemas.super_trip import SuperTrip
from app.services.cascade import apply_cancellation, apply_delay
from app.services.events import event_bus
from app.services.recovery_super_trip import generate_recovery_plans

log = logging.getLogger("routers.disruptions")
router = APIRouter(tags=["disruptions"])


# ---- schemas -------------------------------------------------------------


class DisruptionCreate(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    kind: SuperDisruptionKind = SuperDisruptionKind.DELAY
    delta_mins: int = Field(default=0, ge=-720, le=1440)
    note: str | None = None
    source: str = Field(default="manual", max_length=32)


class RecoveryAction(BaseModel):
    action: str
    node_id: str
    detail: str
    monetary_penalty: float = 0.0


class RecoveryPlan(BaseModel):
    plan_id: str
    label: str
    summary: str
    actions: list[RecoveryAction]
    cost_delta_usd: float
    time_delta_mins: int
    nodes_modified: int
    nodes_cancelled: int
    nodes_kept: int


class DisruptionOut(BaseModel):
    id: str
    super_trip_id: str
    node_id: str
    kind: SuperDisruptionKind
    status: SuperDisruptionStatus
    delta_mins: int
    note: str | None
    source: str
    applied_plan_id: str | None
    plans: list[RecoveryPlan]
    created_at: datetime
    resolved_at: datetime | None


# ---- helpers -------------------------------------------------------------


def _authorize(trip: SuperTripRecord, user: User) -> None:
    if user.role in (UserRole.OPERATOR, UserRole.ADMIN):
        return
    if trip.user_id == user.id:
        return
    raise HTTPException(status_code=403, detail="not your trip")


def _load_trip(db: Session, super_trip_id: str) -> SuperTripRecord:
    trip = db.get(SuperTripRecord, super_trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="super trip not found")
    return trip


def _serialise_disruption(row: SuperDisruption) -> DisruptionOut:
    plans = [RecoveryPlan(**{k: p[k] for k in RecoveryPlan.model_fields.keys() if k in p}) for p in (row.plans_json or [])]
    return DisruptionOut(
        id=row.id,
        super_trip_id=row.super_trip_id,
        node_id=row.node_id,
        kind=row.kind,
        status=row.status,
        delta_mins=row.delta_mins,
        note=row.note,
        source=row.source,
        applied_plan_id=row.applied_plan_id,
        plans=plans,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


# ---- endpoints -----------------------------------------------------------


@router.post(
    "/api/super-trips/{super_trip_id}/disruptions",
    response_model=DisruptionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_disruption(
    super_trip_id: str,
    body: DisruptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DisruptionOut:
    trip_row = _load_trip(db, super_trip_id)
    _authorize(trip_row, user)

    payload = dict(trip_row.payload_json or {})
    nodes = payload.get("nodes") or []
    if not any(n.get("node_id") == body.node_id for n in nodes):
        raise HTTPException(status_code=422, detail=f"node {body.node_id} not on this trip")

    # 1. Cascade
    if body.kind == SuperDisruptionKind.CANCELLATION:
        cascade = apply_cancellation(payload, body.node_id)
    else:
        cascade = apply_delay(payload, body.node_id, body.delta_mins)

    # 2. Recovery plans
    plans = generate_recovery_plans(payload, cascade)

    # 3. Persist disruption row + updated trip snapshot
    row = SuperDisruption(
        super_trip_id=super_trip_id,
        node_id=body.node_id,
        kind=body.kind,
        status=SuperDisruptionStatus.OPEN,
        delta_mins=body.delta_mins,
        note=body.note,
        source=body.source,
        plans_json=[
            {
                "plan_id": p["plan_id"],
                "label": p["label"],
                "summary": p["summary"],
                "actions": p["actions"],
                "cost_delta_usd": p["cost_delta_usd"],
                "time_delta_mins": p["time_delta_mins"],
                "nodes_modified": p["nodes_modified"],
                "nodes_cancelled": p["nodes_cancelled"],
                "nodes_kept": p["nodes_kept"],
            }
            for p in plans
        ],
        pre_snapshot=copy.deepcopy(trip_row.payload_json),
    )
    db.add(row)

    # 4. Update the trip's live DAG with the cascade-shifted timestamps so the
    # Gantt immediately reflects the disruption. Recovery plans stay in the
    # `disruption` row until an operator applies one.
    trip_row.payload_json = cascade["trip_after"]
    db.commit()
    db.refresh(row)

    log.info("Disruption created: %s on trip %s (%s %s min)", row.id, super_trip_id, body.kind.value, body.delta_mins)
    event_bus.publish({
        "type": "disruption.created",
        "trip_id": super_trip_id,
        "disruption_id": row.id,
        "kind": body.kind.value,
    })

    return _serialise_disruption(row)


@router.get(
    "/api/super-trips/{super_trip_id}/disruptions",
    response_model=list[DisruptionOut],
)
def list_disruptions(
    super_trip_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DisruptionOut]:
    trip_row = _load_trip(db, super_trip_id)
    _authorize(trip_row, user)
    rows = (
        db.query(SuperDisruption)
        .filter(SuperDisruption.super_trip_id == super_trip_id)
        .order_by(SuperDisruption.created_at.desc())
        .all()
    )
    return [_serialise_disruption(r) for r in rows]


@router.post(
    "/api/super-trips/{super_trip_id}/disruptions/{disruption_id}/apply/{plan_id}",
    response_model=DisruptionOut,
)
def apply_recovery(
    super_trip_id: str,
    disruption_id: str,
    plan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DisruptionOut:
    trip_row = _load_trip(db, super_trip_id)
    _authorize(trip_row, user)
    row = db.get(SuperDisruption, disruption_id)
    if not row or row.super_trip_id != super_trip_id:
        raise HTTPException(status_code=404, detail="disruption not found")
    if row.status != SuperDisruptionStatus.OPEN:
        raise HTTPException(status_code=409, detail=f"disruption is {row.status.value}, cannot apply")

    # Rebuild the plan from persisted json
    plan = next((p for p in (row.plans_json or []) if p.get("plan_id") == plan_id), None)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"plan {plan_id} not in this disruption")

    # Rerun the cascade to get a fresh `trip_after` (pre_snapshot is the DAG
    # at the moment the disruption was created — plan actions may reference
    # cancellations that we apply against that snapshot).
    from app.services.cascade import apply_cancellation as _cancel, apply_delay as _delay
    if row.kind == SuperDisruptionKind.CANCELLATION:
        cascade = _cancel(row.pre_snapshot or trip_row.payload_json, row.node_id)
    else:
        cascade = _delay(row.pre_snapshot or trip_row.payload_json, row.node_id, row.delta_mins)

    # Regenerate plans (deterministic) so we can pick the same one.
    plans = generate_recovery_plans(row.pre_snapshot or trip_row.payload_json, cascade)
    match = next((p for p in plans if p["plan_id"] == plan_id), None)
    if match is None:
        raise HTTPException(status_code=500, detail="failed to reproduce plan")

    trip_after = match["trip_after"]
    # Bump status metadata so travelers know the DAG has changed.
    trip_after["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Validate the resulting SuperTrip against the strict schema before saving.
    try:
        SuperTrip.model_validate(trip_after)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"recovery produced invalid DAG: {e}")

    trip_row.payload_json = trip_after
    trip_row.total_cost_usd = float(
        sum((n.get("financials") or {}).get("cost_usd") or 0 for n in (trip_after.get("nodes") or []))
    )
    row.applied_plan_id = plan_id
    row.status = SuperDisruptionStatus.MITIGATED
    row.resolved_at = datetime.now(timezone.utc)

    # Auto-refund any nodes the plan cancelled (Phase 6 hook). Only kicks in if
    # a payment has already been captured — otherwise there's nothing to refund.
    from app.models.payment import PaymentStatus as PayStatus, SuperTripPayment
    from app.services import payment_mock

    pre_nodes = {n.get("node_id"): n for n in (row.pre_snapshot or {}).get("nodes") or []}
    post_nodes = {n.get("node_id"): n for n in trip_after.get("nodes") or []}
    newly_cancelled = [
        nid for nid, post in post_nodes.items()
        if str(post.get("status")) == "cancelled"
        and str((pre_nodes.get(nid) or {}).get("status")) != "cancelled"
    ]

    if newly_cancelled:
        pay = (
            db.query(SuperTripPayment)
            .filter(SuperTripPayment.super_trip_id == super_trip_id)
            .first()
        )
        if pay and pay.status in (PayStatus.CAPTURED, PayStatus.PARTIALLY_REFUNDED):
            refunds_new = list(pay.refunds_json or [])
            total_refund = 0.0
            for nid in newly_cancelled:
                if any(r.get("node_id") == nid for r in refunds_new):
                    continue
                node = pre_nodes.get(nid) or post_nodes.get(nid)
                refund = payment_mock.build_refund_for_node(
                    pay.razorpay_payment_id or pay.razorpay_order_id, node
                )
                if refund:
                    refunds_new.append(refund)
                    total_refund += refund["amount_usd"]
            if total_refund > 0:
                pay.refunds_json = refunds_new
                pay.refunded_usd = round(pay.refunded_usd + total_refund, 2)
                if pay.refunded_usd >= pay.total_usd - 0.01:
                    pay.status = PayStatus.REFUNDED
                else:
                    pay.status = PayStatus.PARTIALLY_REFUNDED
                event_bus.publish({
                    "type": "payment.refunded",
                    "trip_id": super_trip_id,
                    "payment_id": pay.id,
                    "amount_usd": total_refund,
                    "reason": "auto_from_recovery",
                })

    db.commit()
    db.refresh(row)

    log.info("Recovery applied: disruption=%s plan=%s trip=%s", row.id, plan_id, super_trip_id)
    event_bus.publish({
        "type": "recovery.applied",
        "trip_id": super_trip_id,
        "disruption_id": row.id,
        "plan_id": plan_id,
    })
    return _serialise_disruption(row)


@router.delete(
    "/api/super-trips/{super_trip_id}/disruptions/{disruption_id}",
    response_model=DisruptionOut,
)
def dismiss_disruption(
    super_trip_id: str,
    disruption_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DisruptionOut:
    trip_row = _load_trip(db, super_trip_id)
    _authorize(trip_row, user)
    row = db.get(SuperDisruption, disruption_id)
    if not row or row.super_trip_id != super_trip_id:
        raise HTTPException(status_code=404, detail="disruption not found")
    if row.status == SuperDisruptionStatus.MITIGATED:
        raise HTTPException(status_code=409, detail="already mitigated")
    row.status = SuperDisruptionStatus.IGNORED
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _serialise_disruption(row)
