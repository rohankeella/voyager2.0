"""DTO-P3 SuperTrip CRUD.

Persists agent-planned DAGs so the dashboard, /copilot inspector, and
operator Gantt (Phase 4) can iterate over them. All endpoints require JWT
except GET-by-id, which allows anon reads if the trip has no owner (shared
demo links).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, oauth2_scheme
from app.models.super_trip import SuperTripRecord, SuperTripStatus
from app.models.user import User
from app.schemas.super_trip import SuperTrip
from app.schemas.super_trip_record import (
    SuperTripCreate,
    SuperTripDetail,
    SuperTripSummary,
)
from app.security import decode_token

log = logging.getLogger("routers.super_trips")
router = APIRouter(prefix="/api/super-trips", tags=["super-trips"])


def _optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Auth is nice-to-have on /copilot demos — resolve if present, else None."""
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


def _validate_super_trip(payload: dict) -> SuperTrip:
    try:
        return SuperTrip.model_validate(payload)
    except ValidationError as e:
        detail = "; ".join(
            f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()[:5]
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _derive_title(trip: SuperTrip, override: str | None = None) -> str:
    if override:
        return override[:200]
    home = trip.global_constraints.home_location or "Trip"
    days = (trip.global_constraints.end_date - trip.global_constraints.start_date).days
    return f"{home} · {days}-day plan · {trip.super_trip_id}"[:200]


@router.post("", response_model=SuperTripDetail, status_code=status.HTTP_201_CREATED)
def create_super_trip(
    body: SuperTripCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(_optional_user),
) -> SuperTripDetail:
    trip = _validate_super_trip(body.payload)

    # If a record with this id already exists, treat as replace-in-place
    # (typical for /copilot: user re-plans same trip in one session).
    existing = db.get(SuperTripRecord, trip.super_trip_id)
    if existing:
        existing.payload_json = trip.model_dump(mode="json")
        existing.title = _derive_title(trip, body.title)
        existing.total_cost_usd = trip.total_cost_usd()
        existing.max_budget_usd = trip.global_constraints.max_budget_usd
        existing.node_count = len(trip.nodes)
        existing.source_prompt = body.source_prompt or existing.source_prompt
        existing.agent_trace = body.agent_trace or existing.agent_trace
        if user and existing.user_id != user.id:
            existing.user_id = user.id
            existing.traveler_id = f"USR-{user.id}"
        db.commit()
        db.refresh(existing)
        return SuperTripDetail.model_validate(existing)

    record = SuperTripRecord(
        payload_json=trip.model_dump(mode="json"),
        title=_derive_title(trip, body.title),
        total_cost_usd=trip.total_cost_usd(),
        max_budget_usd=trip.global_constraints.max_budget_usd,
        node_count=len(trip.nodes),
        status=SuperTripStatus.PENDING_REVIEW,
        source_prompt=body.source_prompt,
        agent_trace=body.agent_trace or [],
        traveler_id=(f"USR-{user.id}" if user else trip.traveler_id),
        user_id=user.id if user else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    log.info("SuperTrip persisted: %s (%s nodes, $%.2f)", record.id, record.node_count, record.total_cost_usd)
    return SuperTripDetail.model_validate(record)


@router.get("", response_model=list[SuperTripSummary])
def list_super_trips(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SuperTripSummary]:
    rows = (
        db.query(SuperTripRecord)
        .filter(SuperTripRecord.user_id == user.id)
        .order_by(SuperTripRecord.created_at.desc())
        .all()
    )
    return [SuperTripSummary.model_validate(r) for r in rows]


@router.get("/{super_trip_id}", response_model=SuperTripDetail)
def get_super_trip(
    super_trip_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(_optional_user),
) -> SuperTripDetail:
    record = db.get(SuperTripRecord, super_trip_id)
    if not record:
        raise HTTPException(status_code=404, detail="super trip not found")
    if record.user_id and (not user or user.id != record.user_id):
        raise HTTPException(status_code=403, detail="not your trip")
    return SuperTripDetail.model_validate(record)


@router.post("/{super_trip_id}/approve", response_model=SuperTripDetail)
def approve_super_trip(
    super_trip_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SuperTripDetail:
    record = db.get(SuperTripRecord, super_trip_id)
    if not record:
        raise HTTPException(status_code=404, detail="super trip not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your trip")
    if record.status not in (SuperTripStatus.DRAFT, SuperTripStatus.PENDING_REVIEW):
        raise HTTPException(status_code=409, detail=f"cannot approve from status={record.status.value}")

    record.status = SuperTripStatus.APPROVED
    record.approved_at = datetime.now(timezone.utc)

    # Also flip the embedded DAG status so downstream consumers stay in sync.
    payload = dict(record.payload_json or {})
    payload["status"] = "active"
    record.payload_json = payload

    db.commit()
    db.refresh(record)
    log.info("SuperTrip approved: %s by user %s", record.id, user.id)
    return SuperTripDetail.model_validate(record)


@router.delete("/{super_trip_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_super_trip(
    super_trip_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    record = db.get(SuperTripRecord, super_trip_id)
    if not record:
        raise HTTPException(status_code=404, detail="super trip not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your trip")
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
