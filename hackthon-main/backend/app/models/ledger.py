import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SplitStrategy(str, enum.Enum):
    """F-09 supported models. The `share_value` on each participant is
    interpreted according to the strategy:
      EQUAL             — share_value ignored, cost / N
      EXACT_AMOUNT      — share_value = the absolute amount owed
      PERCENTAGE        — share_value = %; must sum to 100
      SHARE_WEIGHTED    — share_value = integer weight; owed = weight / sum(weights) * cost
      ORGANIZER_COVERED — share_value ignored; owed = 0 for everyone (payer eats it)
    """

    EQUAL = "EQUAL"
    EXACT_AMOUNT = "EXACT_AMOUNT"
    PERCENTAGE = "PERCENTAGE"
    SHARE_WEIGHTED = "SHARE_WEIGHTED"
    ORGANIZER_COVERED = "ORGANIZER_COVERED"


class Expense(Base):
    """A single line-item paid to an external vendor (restaurant, tour,
    hotel, etc.). Participation is per-activity (F-08): only the members
    listed in `participants` owe anything, regardless of the wider group
    roster."""

    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)

    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    # Exchange rate against the group's base_currency at time of entry, so
    # historical expenses don't drift when live rates move.
    fx_rate_to_base: Mapped[float] = mapped_column(Float, default=1.0)

    payer_member_id: Mapped[str] = mapped_column(
        ForeignKey("group_members.id", ondelete="RESTRICT"), index=True
    )
    split_strategy: Mapped[SplitStrategy] = mapped_column(
        Enum(SplitStrategy), default=SplitStrategy.EQUAL
    )
    incurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    group = relationship("Group", back_populates="expenses")
    participants = relationship(
        "ExpenseParticipant",
        back_populates="expense",
        cascade="all, delete-orphan",
    )


class ExpenseParticipant(Base):
    """Per-activity participation row (F-08). `computed_amount_base` is the
    canonical liability figure in the group's base currency — set by the
    reactive recalculator (F-10) whenever the parent Expense changes."""

    __tablename__ = "expense_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    expense_id: Mapped[str] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[str] = mapped_column(
        ForeignKey("group_members.id", ondelete="CASCADE"), index=True
    )
    share_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_amount_base: Mapped[float] = mapped_column(Numeric(12, 4), default=0)

    expense = relationship("Expense", back_populates="participants")


class PeerReimbursement(Base):
    """Layer-2 (Asset / Reimbursement) event — money moving between two
    members inside the group, not to any vendor. These reduce the outstanding
    net-balance graph without touching the underlying expense records
    (F-11 audit separation)."""

    __tablename__ = "peer_reimbursements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    from_member_id: Mapped[str] = mapped_column(
        ForeignKey("group_members.id", ondelete="RESTRICT")
    )
    to_member_id: Mapped[str] = mapped_column(
        ForeignKey("group_members.id", ondelete="RESTRICT")
    )
    amount_base: Mapped[float] = mapped_column(Numeric(12, 2))
    note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    group = relationship("Group", back_populates="reimbursements")
