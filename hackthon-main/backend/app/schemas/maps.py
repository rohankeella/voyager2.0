from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TravelMode = Literal["walking", "driving", "transit"]


class GeoPoint(BaseModel):
    lat: float
    lng: float


class DistanceRequest(BaseModel):
    origin: GeoPoint
    destination: GeoPoint
    mode: TravelMode = "driving"


class DistanceResponse(BaseModel):
    distance_km: float
    duration_mins: int
    mode: TravelMode
    provider: Literal["haversine", "google"]


class LocationPingIn(BaseModel):
    lat: float
    lng: float
    speed_kmh: float | None = None
    heading: float | None = None
    recorded_at: datetime | None = None


class LocationPingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lat: float
    lng: float
    speed_kmh: float | None
    heading: float | None
    recorded_at: datetime


class DriftAlert(BaseModel):
    slot_id: str
    slot_title: str
    scheduled_start_at: datetime
    projected_arrival_at: datetime
    delay_mins: int
    threshold_mins: int = 10
    severity: Literal["warning", "critical"]
    message: str


class LocationPingResponse(BaseModel):
    ping: LocationPingOut
    next_anchor_slot_id: str | None
    projected_arrival_at: datetime | None
    alert: DriftAlert | None
