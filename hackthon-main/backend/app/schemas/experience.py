from datetime import datetime
import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.experience import ExperienceCategory


def _catalog_attributes(value):
    if value is None:
        return value
    for key, maximum in {"rating": 5, "recommendation_score": 100,
                         "popularity_score": None, "original_price": None, "review_count": None}.items():
        number = value.get(key)
        if number is not None and (type(number) not in (int, float) or not math.isfinite(number)
                                   or number < 0 or (maximum is not None and number > maximum)):
            raise ValueError(f"{key} must be a non-negative number" + (f" no greater than {maximum}" if maximum else ""))
    for key in ("free_cancellation", "instant_confirmation", "is_sample"):
        if key in value and type(value[key]) is not bool:
            raise ValueError(f"{key} must be a boolean")
    return value


class OperatingHourIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    open_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    close_time: str = Field(pattern=r"^\d{2}:\d{2}$")


class OperatingHourOut(OperatingHourIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class ExperienceBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: ExperienceCategory
    base_cost: float = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    duration_mins: int = Field(gt=0)
    lat: float
    lng: float
    city: str
    country: str | None = None
    address: str | None = None
    capacity_max: int = Field(default=100, ge=0)
    seats_available: int = Field(default=100, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    interest_tags: list[str] = Field(default_factory=list)


class ExperienceCreate(ExperienceBase):
    _validate_attributes = field_validator("attributes")(_catalog_attributes)
    hours: list[OperatingHourIn] = Field(default_factory=list)


class ExperienceUpdate(BaseModel):
    _validate_attributes = field_validator("attributes")(_catalog_attributes)
    title: str | None = None
    description: str | None = None
    category: ExperienceCategory | None = None
    base_cost: float | None = None
    duration_mins: int | None = None
    lat: float | None = None
    lng: float | None = None
    city: str | None = None
    country: str | None = None
    address: str | None = None
    capacity_max: int | None = None
    seats_available: int | None = None
    attributes: dict[str, Any] | None = None
    interest_tags: list[str] | None = None
    is_active: bool | None = None
    hours: list[OperatingHourIn] | None = None


class ExperienceOut(ExperienceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    provider_id: str | None
    is_active: bool
    hours: list[OperatingHourOut]
    created_at: datetime
    updated_at: datetime
