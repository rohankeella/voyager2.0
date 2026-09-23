from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    country: str | None = None
    phone: str | None
    role: UserRole
    preferences: dict[str, Any] | None
    created_at: datetime


class PreferencesUpdate(BaseModel):
    """Mirrors the frontend OnboardingData type — passed straight through as
    JSON so the recommendation engine can score against it."""

    preferences: dict[str, Any]
