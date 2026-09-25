"""DTO-P3 Phase 6 — Split-payment persistence (Razorpay Route mock).

One `SuperTripPayment` row per SuperTrip that has been checked out. Holds
the Razorpay-shaped order/payment/transfer object IDs (all mocked with
`_MOCK_` prefix so nobody confuses them with real Razorpay resources) and
the settled amount per vendor account.

The mock schema mirrors what Razorpay Route actually returns in production
so a future swap to the real API only requires touching `payment_mock.py`.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"           # order created, awaiting capture
    CAPTURED = "captured"         # funds captured + transfers routed
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SuperTripPayment(Base):
    __tablename__ = "super_trip_payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    super_trip_id: Mapped[str] = mapped_column(
        ForeignKey("super_trips.id", ondelete="CASCADE"), index=True, unique=True
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True
    )

    # Amount fields — all USD to match the DTO-P3 schema.
    total_usd: Mapped[float] = mapped_column(Float, default=0.0)
    refunded_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Razorpay-shaped IDs (all mocked)
    razorpay_order_id: Mapped[str] = mapped_column(String(64))
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # List of transfer objects — see services/payment_mock.py for shape.
    transfers_json: Mapped[list] = mapped_column(JSON, default=list)
    # List of refund objects (per-node cancellations)
    refunds_json: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
