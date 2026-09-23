from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.group import GroupMemberRole


class GroupMemberIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    email: EmailStr | None = None
    role: GroupMemberRole = GroupMemberRole.PARTICIPANT
    user_id: str | None = None


class GroupMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    email: str | None
    role: GroupMemberRole
    user_id: str | None
    created_at: datetime


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    trip_destination: str | None = None
    base_currency: str = Field(default="INR", min_length=3, max_length=3)
    itinerary_id: str | None = None
    members: list[GroupMemberIn] = Field(default_factory=list)


class GroupUpdate(BaseModel):
    name: str | None = None
    trip_destination: str | None = None
    base_currency: str | None = None
    itinerary_id: str | None = None


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    trip_destination: str | None
    base_currency: str
    itinerary_id: str | None
    created_by: str
    created_at: datetime
    members: list[GroupMemberOut]
