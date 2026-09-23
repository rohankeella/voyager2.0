from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProviderCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    description: str | None = None


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    business_name: str
    contact_email: str | None
    contact_phone: str | None
    description: str | None
    created_at: datetime
