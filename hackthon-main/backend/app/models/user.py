import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    TRAVELER = "traveler"
    PROVIDER = "provider"
    OPERATOR = "operator"
    ADMIN = "admin"


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.TRAVELER, index=True)

    # Onboarding preference vector — kept as JSON so it maps 1:1 to the
    # OnboardingData shape the frontend already builds in
    # src/types/onboarding.ts.
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    provider = relationship("Provider", back_populates="user", uselist=False)
    itineraries = relationship("Itinerary", back_populates="owner", cascade="all, delete-orphan")
