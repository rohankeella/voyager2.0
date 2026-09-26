"""Wire schemas for the /api/super-trips CRUD endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.super_trip import SuperTripStatus


class SuperTripCreate(BaseModel):
    """POST /api/super-trips body — accepts a validated SuperTrip payload."""

    payload: dict[str, Any] = Field(description="Full SuperTrip DAG JSON")
    title: str | None = None
    source_prompt: str | None = None
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)


class SuperTripSummary(BaseModel):
    """Compact row for listing (dashboard, operator Gantt)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    traveler_id: str
    title: str
    status: SuperTripStatus
    total_cost_usd: float
    max_budget_usd: float
    node_count: int
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None


class SuperTripDetail(SuperTripSummary):
    """Full record — for /copilot inspector + globe rendering."""

    payload_json: dict[str, Any]
    source_prompt: str | None
    agent_trace: list[dict[str, Any]]
