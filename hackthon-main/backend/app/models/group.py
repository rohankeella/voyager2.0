import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GroupMemberRole(str, enum.Enum):
    ORGANIZER = "organizer"
    PARTICIPANT = "participant"


class Group(Base):
    """A trip group — the outer container for the P2 ledger. A group has one
    organizer, N members, and any number of expenses and peer reimbursements
    logged against it."""

    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(160))
    trip_destination: Mapped[str | None] = mapped_column(String(160), nullable=True)
    base_currency: Mapped[str] = mapped_column(String(3), default="INR")
    itinerary_id: Mapped[str | None] = mapped_column(
        ForeignKey("itineraries.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    members = relationship(
        "GroupMember", back_populates="group", cascade="all, delete-orphan"
    )
    expenses = relationship(
        "Expense", back_populates="group", cascade="all, delete-orphan"
    )
    reimbursements = relationship(
        "PeerReimbursement", back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(Base):
    """Membership row. A member is either a real Voyager user (`user_id` set)
    or a placeholder guest that only exists inside the ledger (`user_id` null,
    `display_name` required)."""

    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[GroupMemberRole] = mapped_column(
        Enum(GroupMemberRole), default=GroupMemberRole.PARTICIPANT, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    group = relationship("Group", back_populates="members")
