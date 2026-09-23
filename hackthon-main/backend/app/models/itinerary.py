import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Itinerary(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    destination_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(10), nullable=True)   # YYYY-MM-DD
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    owner = relationship("User", back_populates="itineraries")
    slots = relationship(
        "ItinerarySlot",
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItinerarySlot.start_at",
    )


class ItinerarySlot(Base):
    """A fixed booking / anchor on an itinerary — flight, hotel check-in, a
    scheduled tour. Gaps between slots are what the gap-filler suggests
    experiences for."""

    __tablename__ = "itinerary_slots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    itinerary_id: Mapped[str] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40), default="booking")  # booking|activity|transit
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    experience_id: Mapped[str | None] = mapped_column(
        ForeignKey("experiences.id", ondelete="SET NULL"), nullable=True
    )
    buffer_before_mins: Mapped[int] = mapped_column(Integer, default=0)
    buffer_after_mins: Mapped[int] = mapped_column(Integer, default=0)

    itinerary = relationship("Itinerary", back_populates="slots")
