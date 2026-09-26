"""DTO-P3 Phase 6 — Razorpay Route split-payment endpoints.

Endpoints:
  POST   /api/super-trips/{id}/checkout              create a payment order + transfers (pending)
  POST   /api/super-trips/{id}/checkout/capture      simulate successful capture → transfers routed
  GET    /api/super-trips/{id}/payment               get current payment state
  POST   /api/super-trips/{id}/refund                {node_ids: [...]} — refund cancelled nodes

Auth: trip owner or operator.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.payment import PaymentStatus, SuperTripPayment
from app.models.super_trip import SuperTripRecord, SuperTripStatus
from app.models.user import User, UserRole
from app.services import payment_mock
from app.services.events import event_bus

log = logging.getLogger("routers.payments")
router = APIRouter(tags=["payments"])


# ---- schemas -------------------------------------------------------------


class TransferOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    transfer_id: str
    account: str
    amount_usd: float
    percent_of_total: float
    purpose: str
    node_ids: list[str]
    status: str
    on_hold: bool = False
    routed_at: str | None = None


class RefundOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    refund_id: str
    payment_id: str
    node_id: str
    vendor_account: str | None = None
    amount_usd: float
    reason: str
    status: str
    created_at: str


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    super_trip_id: str
    status: PaymentStatus
    total_usd: float
    refunded_usd: float
    razorpay_order_id: str
    razorpay_payment_id: str | None
    transfers: list[TransferOut] = Field(default_factory=list)
    refunds: list[RefundOut] = Field(default_factory=list)
    created_at: datetime
    captured_at: datetime | None
    updated_at: datetime


class RefundRequest(BaseModel):
    node_ids: list[str] = Field(min_length=1, max_length=50)
    reason: str = Field(default="cancellation")


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


def _serialise(row: SuperTripPayment) -> PaymentOut:
    return PaymentOut(
        id=row.id,
        super_trip_id=row.super_trip_id,
        status=row.status,
        total_usd=row.total_usd,
        refunded_usd=row.refunded_usd,
        razorpay_order_id=row.razorpay_order_id,
        razorpay_payment_id=row.razorpay_payment_id,
        transfers=[TransferOut(**t) for t in (row.transfers_json or [])],
        refunds=[RefundOut(**r) for r in (row.refunds_json or [])],
        created_at=row.created_at,
        captured_at=row.captured_at,
        updated_at=row.updated_at,
    )


def _propagate_payment_status_to_trip(trip_row: SuperTripRecord, transfers: list[dict]) -> None:
    """Reflect transfer state back into the SuperTrip's node.financials.payment_status."""
    trip = dict(trip_row.payload_json or {})
    nodes = trip.get("nodes") or []
    by_transfer = {}
    for t in transfers:
        for nid in t.get("node_ids", []):
            by_transfer[nid] = t
    for n in nodes:
        t = by_transfer.get(n.get("node_id"))
        if not t:
            continue
        fin = n.setdefault("financials", {})
        if t["status"] == "routed":
            fin["payment_status"] = "routed"
        elif t["status"] == "on_hold":
            fin["payment_status"] = "escrowed"
        elif t["status"] == "pending":
            fin["payment_status"] = "unpaid"
        fin["razorpay_transfer_id"] = t["transfer_id"]
    trip_row.payload_json = trip


# ---- endpoints -----------------------------------------------------------


@router.post(
    "/api/super-trips/{super_trip_id}/checkout",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_checkout(
    super_trip_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    trip_row = _load_trip(db, super_trip_id)
    _authorize(trip_row, user)

    # Only approved / active trips can be paid.
    if trip_row.status not in (SuperTripStatus.APPROVED, SuperTripStatus.ACTIVE):
        raise HTTPException(
            status_code=409,
            detail=f"trip must be approved before checkout (current: {trip_row.status.value})",
        )

    existing = db.get(SuperTripPayment, str(super_trip_id))  # try id lookup — but pk is uuid.
    existing = db.query(SuperTripPayment).filter(SuperTripPayment.super_trip_id == super_trip_id).first()

    if existing and existing.status in (PaymentStatus.CAPTURED, PaymentStatus.PARTIALLY_REFUNDED):
        raise HTTPException(status_code=409, detail=f"payment already {existing.status.value}")

    transfers, total = payment_mock.build_transfers(trip_row.payload_json or {})
    order_id = payment_mock.create_order(super_trip_id, total)

    if existing:
        existing.transfers_json = transfers
        existing.total_usd = total
        existing.razorpay_order_id = order_id
        existing.status = PaymentStatus.PENDING
        row = existing
    else:
        row = SuperTripPayment(
            super_trip_id=super_trip_id,
            status=PaymentStatus.PENDING,
            total_usd=total,
            razorpay_order_id=order_id,
            transfers_json=transfers,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    log.info("Checkout created: %s (total=$%.2f, %s transfers)", row.id, total, len(transfers))
    return _serialise(row)


@router.post("/api/super-trips/{super_trip_id}/checkout/capture", response_model=PaymentOut)
def capture_checkout(
    super_trip_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    trip_row = _load_trip(db, super_trip_id)
    _authorize(trip_row, user)
    row = db.query(SuperTripPayment).filter(SuperTripPayment.super_trip_id == super_trip_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="no checkout on this trip")
    if row.status != PaymentStatus.PENDING:
        raise HTTPException(status_code=409, detail=f"payment is {row.status.value}, cannot capture")

    payment_id = payment_mock.capture_payment(row.razorpay_order_id)
    routed = payment_mock.route_transfers(row.transfers_json or [])
    row.razorpay_payment_id = payment_id
    row.transfers_json = routed
    row.status = PaymentStatus.CAPTURED
    row.captured_at = datetime.now(timezone.utc)

    # Propagate payment_status into node.financials so /copilot & Gantt reflect it.
    _propagate_payment_status_to_trip(trip_row, routed)
    trip_row.status = SuperTripStatus.ACTIVE

    db.commit()
    db.refresh(row)

    event_bus.publish({"type": "payment.captured", "trip_id": super_trip_id, "payment_id": row.id})
    log.info("Payment captured: %s trip=%s", row.id, super_trip_id)
    return _serialise(row)


@router.get("/api/super-trips/{super_trip_id}/payment", response_model=PaymentOut)
def get_payment(
    super_trip_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    trip_row = _load_trip(db, super_trip_id)
    _authorize(trip_row, user)
    row = db.query(SuperTripPayment).filter(SuperTripPayment.super_trip_id == super_trip_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="no payment on this trip")
    return _serialise(row)


@router.post("/api/super-trips/{super_trip_id}/refund", response_model=PaymentOut)
def refund_nodes(
    super_trip_id: str,
    body: RefundRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    trip_row = _load_trip(db, super_trip_id)
    _authorize(trip_row, user)
    row = db.query(SuperTripPayment).filter(SuperTripPayment.super_trip_id == super_trip_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="no payment to refund")
    if row.status not in (PaymentStatus.CAPTURED, PaymentStatus.PARTIALLY_REFUNDED):
        raise HTTPException(
            status_code=409,
            detail=f"payment must be captured before refund (current: {row.status.value})",
        )

    nodes = (trip_row.payload_json or {}).get("nodes") or []
    by_id = {n.get("node_id"): n for n in nodes}
    refunds_new: list[dict[str, Any]] = list(row.refunds_json or [])
    total_refund = 0.0
    for nid in body.node_ids:
        node = by_id.get(nid)
        if not node:
            continue
        # Prevent double-refunding the same node
        if any(r.get("node_id") == nid for r in refunds_new):
            continue
        refund = payment_mock.build_refund_for_node(row.razorpay_payment_id or row.razorpay_order_id, node)
        if refund:
            refunds_new.append(refund)
            total_refund += refund["amount_usd"]

    row.refunds_json = refunds_new
    row.refunded_usd = round(row.refunded_usd + total_refund, 2)
    if row.refunded_usd >= row.total_usd - 0.01:
        row.status = PaymentStatus.REFUNDED
    elif row.refunded_usd > 0:
        row.status = PaymentStatus.PARTIALLY_REFUNDED

    db.commit()
    db.refresh(row)
    event_bus.publish({
        "type": "payment.refunded",
        "trip_id": super_trip_id,
        "payment_id": row.id,
        "amount_usd": total_refund,
    })
    log.info("Refund processed: trip=%s amount=$%.2f", super_trip_id, total_refund)
    return _serialise(row)
