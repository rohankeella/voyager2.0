from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItinerarySlotIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    kind: str = "booking"
    start_at: datetime
    end_at: datetime
    lat: float | None = None
    lng: float | None = None
    location_label: str | None = None
    experience_id: str | None = None
    buffer_before_mins: int = 0
    buffer_after_mins: int = 0


class ItinerarySlotOut(ItinerarySlotIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class ItineraryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    destination_city: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    slots: list[ItinerarySlotIn] = Field(default_factory=list)


class ItineraryUpdate(BaseModel):
    title: str | None = None
    destination_city: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ItineraryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    title: str
    destination_city: str | None
    start_date: str | None
    end_date: str | None
    created_at: datetime
    slots: list[ItinerarySlotOut]
