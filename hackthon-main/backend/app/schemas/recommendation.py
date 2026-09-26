from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.experience import ExperienceOut


class RecommendationQuery(BaseModel):
    """Direct match query — used when the traveler hits Discover with a
    specific location + free window."""

    lat: float
    lng: float
    at: datetime
    window_end: datetime
    interests: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    budget_max: float | None = None
    group_type: str | None = None
    accessibility_flags: list[str] = Field(default_factory=list)
    travel_mode: Literal["walking", "driving", "transit"] = "driving"
    limit: int = Field(default=20, ge=1, le=100)
    city: str | None = None


class ScoreBreakdown(BaseModel):
    interest: float
    logistics: float
    budget: float
    fit: float
    weights: dict[str, float]


class ScoredExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    experience: ExperienceOut
    score: float
    breakdown: ScoreBreakdown
    transit_mins: int
    distance_km: float
    reasons: list[str]


class RecommendationsResponse(BaseModel):
    query_window_mins: int
    candidates_scanned: int
    results: list[ScoredExperienceOut]


class GapFillQuery(BaseModel):
    """F-05: fills the idle intervals in an itinerary."""

    itinerary_id: str
    interests: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    budget_max: float | None = None
    group_type: str | None = None
    accessibility_flags: list[str] = Field(default_factory=list)
    travel_mode: Literal["walking", "driving", "transit"] = "driving"
    min_gap_mins: int = Field(default=45, description="ignore gaps shorter than this")
    per_gap_limit: int = Field(default=5, ge=1, le=20)


class GapWindow(BaseModel):
    start_at: datetime
    end_at: datetime
    duration_mins: int
    anchor_before: str | None = None
    anchor_after: str | None = None
    lat: float | None = None
    lng: float | None = None


class GapSuggestion(BaseModel):
    gap: GapWindow
    suggestions: list[ScoredExperienceOut]


class GapFillResponse(BaseModel):
    itinerary_id: str
    gaps: list[GapSuggestion]
