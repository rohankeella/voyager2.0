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
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ExperienceCategory(str, enum.Enum):
    FOOD = "FOOD"
    WORKSHOP = "WORKSHOP"
    FESTIVAL = "FESTIVAL"
    OUTDOOR = "OUTDOOR"
    NIGHTLIFE = "NIGHTLIFE"
    CULTURE = "CULTURE"


class Experience(Base):
    """Unified data catalog row (F-02).

    A single schema serves food places, workshops, pop-ups, festivals, outdoor
    activities, nightlife spots — anything a traveler might slot into their
    itinerary. Category-specific fields ride in `attributes` (JSON) instead of
    branching the schema.
    """

    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_id: Mapped[str | None] = mapped_column(
        ForeignKey("providers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(200), index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    category: Mapped[ExperienceCategory] = mapped_column(Enum(ExperienceCategory), index=True)

    base_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    duration_mins: Mapped[int] = mapped_column(Integer, default=60)

    lat: Mapped[float] = mapped_column(Float, index=True)
    lng: Mapped[float] = mapped_column(Float, index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(400), nullable=True)

    capacity_max: Mapped[int] = mapped_column(Integer, default=100)
    seats_available: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Free-form category-specific fields (accessibility flags, dietary tags,
    # dress code, etc.)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)

    # Denormalized match tags — kept aligned with the frontend Activity enum so
    # the matcher can intersect interests without a join table for MVP.
    interest_tags: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    provider = relationship("Provider", back_populates="experiences")
    hours = relationship(
        "OperatingHour", back_populates="experience", cascade="all, delete-orphan"
    )


class OperatingHour(Base):
    __tablename__ = "operating_hours"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experience_id: Mapped[str] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    # 0=Mon ... 6=Sun to match Python's datetime.weekday()
    day_of_week: Mapped[int] = mapped_column(Integer, index=True)
    open_time: Mapped[str] = mapped_column(String(5))   # "HH:MM"
    close_time: Mapped[str] = mapped_column(String(5))  # "HH:MM"

    experience = relationship("Experience", back_populates="hours")
