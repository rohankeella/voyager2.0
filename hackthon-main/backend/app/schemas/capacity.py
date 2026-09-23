from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.capacity import CapacitySourceKind, NudgeKind


# ---- zones ----------------------------------------------------------------


class ZoneCreate(BaseModel):
    city: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    center_lat: float
    center_lng: float
    radius_km: float = Field(default=1.0, gt=0)
    total_capacity: int = Field(default=1000, ge=0)


class ZoneUpdate(BaseModel):
    city: str | None = None
    name: str | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    radius_km: float | None = None
    total_capacity: int | None = None


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    city: str
    name: str
    center_lat: float
    center_lng: float
    radius_km: float
    total_capacity: int
    created_at: datetime


# ---- capacity metric ingestion --------------------------------------------


class CapacityMetricIn(BaseModel):
    zone_id: str
    source_kind: CapacitySourceKind
    source_label: str | None = None
    occupancy_count: int = Field(ge=0)
    capacity_max: int = Field(ge=0)
    recorded_at: datetime | None = None


class CapacityMetricBatch(BaseModel):
    metrics: list[CapacityMetricIn] = Field(min_length=1)


class CapacityMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    zone_id: str
    source_kind: CapacitySourceKind
    source_label: str | None
    occupancy_count: int
    capacity_max: int
    density_pct: float
    recorded_at: datetime


# ---- forecasting outputs --------------------------------------------------


class ZoneDensityOut(BaseModel):
    zone_id: str
    zone_name: str
    city: str
    density_pct: float
    occupancy_count: int
    capacity_max: int
    recorded_at: datetime | None
    sources: dict[str, float]


class SaturationForecastOut(BaseModel):
    zone_id: str
    zone_name: str
    current_density_pct: float
    projected_density_pct_60m: float
    slope_pct_per_min: float
    minutes_to_saturation: float | None
    status: str
    event_pressure_applied: bool


class BalancerRecommendationOut(BaseModel):
    from_zone_id: str
    from_zone_name: str
    from_density_pct: float
    to_zone_id: str
    to_zone_name: str
    to_density_pct: float
    distance_km: float
    attached_nudge: "NudgeOut | None" = None


# ---- events + staggering ---------------------------------------------------


class ZoneEventCreate(BaseModel):
    zone_id: str
    name: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    expected_attendance: int = Field(default=500, ge=0)


class ZoneEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    zone_id: str
    name: str
    start_at: datetime
    end_at: datetime
    expected_attendance: int
    created_at: datetime


class DepartureBandOut(BaseModel):
    label: str
    start_at: datetime
    end_at: datetime
    assigned_headcount: int


class StaggeringRequest(BaseModel):
    event_id: str
    max_per_band: int = Field(default=200, gt=0)
    band_minutes: int = Field(default=15, gt=0)


class StaggeringPlan(BaseModel):
    event_id: str
    event_name: str
    event_end_at: datetime
    total_attendees: int
    bands: list[DepartureBandOut]


# ---- nudges ---------------------------------------------------------------


class NudgeCreate(BaseModel):
    kind: NudgeKind
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    target_zone_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class NudgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: NudgeKind
    title: str
    description: str | None
    target_zone_id: str | None
    payload: dict[str, Any]
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


# ---- dual-role views (F-14, F-19) -----------------------------------------


class OperatorDashboardView(BaseModel):
    """Organizer scope: heatmap + forecasts + alerts + balancer suggestions."""

    now: datetime
    zone_densities: list[ZoneDensityOut]
    forecasts: list[SaturationForecastOut]
    balancer_recommendations: list[BalancerRecommendationOut]
    active_events: list[ZoneEventOut]


class AttendeeCapacityView(BaseModel):
    """Attendee scope for a given zone: current status + one crowd-avoidance
    recommendation + any nudge attached (F-19 + F-20)."""

    zone_id: str
    zone_name: str
    density_pct: float
    status: str  # STABLE | RISING | APPROACHING_SATURATION | SATURATED
    forecast: SaturationForecastOut
    suggested_alternative: BalancerRecommendationOut | None
    tip: str


BalancerRecommendationOut.model_rebuild()
