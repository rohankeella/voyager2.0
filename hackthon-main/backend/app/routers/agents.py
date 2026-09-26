"""DTO-P3 agent orchestration endpoints.

Exposes the LangGraph Planner→Executor→Supervisor pipeline behind a single
HTTP surface so the frontend co-pilot can hand off natural-language goals.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.orchestrator import plan_trip
from app.config import get_settings
from app.database import get_db
from app.deps import oauth2_scheme
from app.models.super_trip import SuperTripRecord, SuperTripStatus
from app.models.user import User
from app.schemas.super_trip import SuperTrip
from app.security import decode_token

log = logging.getLogger("routers.agents")
router = APIRouter(prefix="/api/agents", tags=["agents"])


class PlanTripRequest(BaseModel):
    user_goal: str = Field(min_length=6, max_length=2000)
    traveler_id: str | None = None
    constraints_hint: dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = Field(default=3, ge=1, le=5)
    persist: bool = Field(
        default=True,
        description="If auth token present, save the DAG so /dashboard can list it later.",
    )


class PlanTripResponse(BaseModel):
    trip: dict[str, Any] | None
    hitl_required: bool
    hitl_reason: str | None
    errors: list[str]
    warnings: list[str]
    iterations: int
    trace: list[dict[str, Any]]
    persisted_id: str | None = None
    persisted_status: str | None = None


@router.get("/status")
def agent_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "gemini_configured": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model if settings.gemini_api_key else None,
        "amadeus_configured": bool(settings.amadeus_client_id and settings.amadeus_client_secret),
        "note": (
            "Set GEMINI_API_KEY in backend/.env to enable the Planner Agent. "
            "Amadeus is optional — falls back to deterministic mock data."
            if not settings.gemini_api_key
            else "Ready. Multi-agent orchestration active."
        ),
    }


def _resolve_user(token: str | None, db: Session) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    return db.get(User, sub)


@router.post("/plan-trip", response_model=PlanTripResponse)
async def plan_trip_endpoint(
    payload: PlanTripRequest,
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
) -> PlanTripResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "Planner Agent needs a Gemini API key. Add GEMINI_API_KEY to "
                "backend/.env (free at https://aistudio.google.com/apikey) and restart."
            ),
        )

    user = _resolve_user(token, db)
    traveler = (payload.traveler_id or "").strip()
    if not traveler:
        traveler = f"USR-{user.id}" if user else "USR-anon"
    elif not traveler.startswith("USR-"):
        traveler = f"USR-{traveler}"

    # LangGraph invoke is sync — offload so we don't block the event loop.
    try:
        result = await run_in_threadpool(
            plan_trip,
            payload.user_goal,
            traveler_id=traveler,
            constraints_hint=payload.constraints_hint,
            max_iterations=payload.max_iterations,
        )
    except RuntimeError as e:
        log.exception("Agent stack failed")
        raise HTTPException(status_code=500, detail=str(e))

    # Auto-persist for signed-in travelers so /copilot has something to
    # approve and /dashboard can list it. Anon requests are ephemeral.
    persisted_id: str | None = None
    persisted_status: str | None = None
    if payload.persist and user and result.get("trip"):
        try:
            trip = SuperTrip.model_validate(result["trip"])
            existing = db.get(SuperTripRecord, trip.super_trip_id)
            if existing:
                existing.payload_json = trip.model_dump(mode="json")
                existing.title = f"{trip.global_constraints.home_location or 'Trip'} · {trip.super_trip_id}"[:200]
                existing.total_cost_usd = trip.total_cost_usd()
                existing.max_budget_usd = trip.global_constraints.max_budget_usd
                existing.node_count = len(trip.nodes)
                existing.source_prompt = payload.user_goal
                existing.agent_trace = result.get("trace") or []
                existing.user_id = user.id
                existing.traveler_id = traveler
                record = existing
            else:
                record = SuperTripRecord(
                    payload_json=trip.model_dump(mode="json"),
                    title=f"{trip.global_constraints.home_location or 'Trip'} · {trip.super_trip_id}"[:200],
                    total_cost_usd=trip.total_cost_usd(),
                    max_budget_usd=trip.global_constraints.max_budget_usd,
                    node_count=len(trip.nodes),
                    status=SuperTripStatus.PENDING_REVIEW,
                    source_prompt=payload.user_goal,
                    agent_trace=result.get("trace") or [],
                    traveler_id=traveler,
                    user_id=user.id,
                )
                db.add(record)
            db.commit()
            persisted_id = record.id
            persisted_status = record.status.value
        except Exception:
            log.exception("Auto-persist failed (non-fatal)")

    return PlanTripResponse(**result, persisted_id=persisted_id, persisted_status=persisted_status)
