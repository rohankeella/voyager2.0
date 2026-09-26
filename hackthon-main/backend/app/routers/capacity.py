"""P3 endpoints — Capacity & Crowd Command Center.

Route surface:

  Zones (operator)
    POST   /api/zones
    GET    /api/zones
    PATCH  /api/zones/{id}
    DELETE /api/zones/{id}

  Capacity ingestion (operator or trusted device)
    POST   /api/capacity/metrics             single point
    POST   /api/capacity/metrics/batch       up to N in one call

  Events (operator, for F-17 + F-18)
    POST   /api/zones/{id}/events
    GET    /api/zones/{id}/events

  Nudges (operator)
    POST   /api/nudges
    GET    /api/nudges

  Analytics
    GET    /api/capacity/densities           latest density per zone
    GET    /api/capacity/forecasts           F-15 saturation projections (+ F-17 event pressure)
    GET    /api/capacity/balancer            F-16 zone alternatives (with F-20 nudges)
    POST   /api/events/{id}/stagger          F-18 departure bands

  Dual-role views (F-14, F-19)
    GET    /api/operator/dashboard           full picture, operator only
    GET    /api/capacity/for-attendee?zone_id=X   scoped view for any traveler
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_operator
from app.models.capacity import (
    CapacityMetric,
    Nudge,
    NudgeIssuance,
    Zone,
    ZoneEvent,
)
from app.models.user import User
from app.schemas.capacity import (
    AttendeeCapacityView,
    BalancerRecommendationOut,
    CapacityMetricBatch,
    CapacityMetricIn,
    CapacityMetricOut,
    DepartureBandOut,
    NudgeCreate,
    NudgeOut,
    OperatorDashboardView,
    SaturationForecastOut,
    StaggeringPlan,
    StaggeringRequest,
    ZoneCreate,
    ZoneDensityOut,
    ZoneEventCreate,
    ZoneEventOut,
    ZoneOut,
    ZoneUpdate,
)
from app.services.events import event_bus
from app.services.forecasting import (
    BALANCER_TRIGGER_PCT,
    SATURATION_THRESHOLD_PCT,
    apply_event_pressure,
    latest_density_by_zone,
    nearby_low_density_zones,
    project_saturation,
)
from app.services.nudges import pick_nudge_for_zone
from app.services.staggering import generate_staggered_departures


router = APIRouter(prefix="/api", tags=["capacity"])


# ---- helpers --------------------------------------------------------------


def _all_zones(db: Session) -> list[Zone]:
    return list(db.execute(select(Zone)).scalars().all())


def _all_recent_metrics(db: Session, lookback_mins: int = 120) -> list[CapacityMetric]:
    # For the operator dashboard we scan the last 2 hours across all zones —
    # simpler than per-zone queries and still cheap on SQLite for the demo.
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_mins)
    return list(
        db.execute(
            select(CapacityMetric).where(CapacityMetric.recorded_at >= cutoff)
        )
        .scalars()
        .all()
    )


def _all_active_events(db: Session) -> list[ZoneEvent]:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=2)
    return list(
        db.execute(
            select(ZoneEvent).where(ZoneEvent.end_at >= now - timedelta(minutes=30), ZoneEvent.start_at <= horizon)
        )
        .scalars()
        .all()
    )


def _active_nudges(db: Session) -> list[Nudge]:
    return list(db.execute(select(Nudge).where(Nudge.is_active == True)).scalars().all())  # noqa: E712


def _compute_density(occupancy: int, capacity: int) -> float:
    if capacity <= 0:
        return 0.0
    return round((occupancy / capacity) * 100.0, 4)


# ---- zones ----------------------------------------------------------------


@router.post("/zones", response_model=ZoneOut, status_code=status.HTTP_201_CREATED)
def create_zone(payload: ZoneCreate, _op: User = Depends(require_operator), db: Session = Depends(get_db)) -> ZoneOut:
    zone = Zone(**payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    event_bus.publish({"type": "capacity:changed", "action": "zone_created", "zone_id": zone.id})
    return ZoneOut.model_validate(zone)


@router.get("/zones", response_model=list[ZoneOut])
def list_zones(db: Session = Depends(get_db), city: Optional[str] = Query(default=None)) -> list[ZoneOut]:
    stmt = select(Zone)
    if city:
        stmt = stmt.where(Zone.city.ilike(f"%{city}%"))
    rows = db.execute(stmt.order_by(Zone.city, Zone.name)).scalars().all()
    return [ZoneOut.model_validate(z) for z in rows]


@router.patch("/zones/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: str, payload: ZoneUpdate, _op: User = Depends(require_operator), db: Session = Depends(get_db)) -> ZoneOut:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="zone not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(zone, k, v)
    db.commit()
    db.refresh(zone)
    return ZoneOut.model_validate(zone)


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(zone_id: str, _op: User = Depends(require_operator), db: Session = Depends(get_db)) -> None:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="zone not found")
    db.delete(zone)
    db.commit()


# ---- capacity ingestion ---------------------------------------------------


def _store_metric(db: Session, m: CapacityMetricIn) -> CapacityMetric:
    zone = db.get(Zone, m.zone_id)
    if not zone:
        raise HTTPException(status_code=400, detail=f"unknown zone {m.zone_id}")
    row = CapacityMetric(
        zone_id=m.zone_id,
        source_kind=m.source_kind,
        source_label=m.source_label,
        occupancy_count=m.occupancy_count,
        capacity_max=m.capacity_max,
        density_pct=_compute_density(m.occupancy_count, m.capacity_max),
        recorded_at=m.recorded_at or datetime.now(timezone.utc),
    )
    db.add(row)
    return row


@router.post("/capacity/metrics", response_model=CapacityMetricOut, status_code=status.HTTP_201_CREATED)
def post_metric(payload: CapacityMetricIn, _op: User = Depends(require_operator), db: Session = Depends(get_db)) -> CapacityMetricOut:
    row = _store_metric(db, payload)
    db.commit()
    db.refresh(row)
    event_bus.publish({"type": "capacity:changed", "action": "metric_posted", "zone_id": row.zone_id, "density_pct": row.density_pct})
    return CapacityMetricOut.model_validate(row)


@router.post("/capacity/metrics/batch", response_model=list[CapacityMetricOut], status_code=status.HTTP_201_CREATED)
def post_metrics_batch(payload: CapacityMetricBatch, _op: User = Depends(require_operator), db: Session = Depends(get_db)) -> list[CapacityMetricOut]:
    rows = [_store_metric(db, m) for m in payload.metrics]
    db.commit()
    for r in rows:
        db.refresh(r)
    # Single fan-out event so the SSE stream doesn't spam a per-metric burst.
    event_bus.publish({"type": "capacity:changed", "action": "metrics_batched", "count": len(rows)})
    return [CapacityMetricOut.model_validate(r) for r in rows]


# ---- events ---------------------------------------------------------------


@router.post("/zones/{zone_id}/events", response_model=ZoneEventOut, status_code=status.HTTP_201_CREATED)
def create_event(zone_id: str, payload: ZoneEventCreate, _op: User = Depends(require_operator), db: Session = Depends(get_db)) -> ZoneEventOut:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="zone not found")
    if payload.zone_id != zone_id:
        raise HTTPException(status_code=400, detail="zone_id mismatch")
    if payload.end_at <= payload.start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    ev = ZoneEvent(**payload.model_dump())
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ZoneEventOut.model_validate(ev)


@router.get("/zones/{zone_id}/events", response_model=list[ZoneEventOut])
def list_zone_events(zone_id: str, db: Session = Depends(get_db)) -> list[ZoneEventOut]:
    rows = db.execute(select(ZoneEvent).where(ZoneEvent.zone_id == zone_id).order_by(ZoneEvent.start_at)).scalars().all()
    return [ZoneEventOut.model_validate(r) for r in rows]


# ---- nudges ---------------------------------------------------------------


@router.post("/nudges", response_model=NudgeOut, status_code=status.HTTP_201_CREATED)
def create_nudge(payload: NudgeCreate, _op: User = Depends(require_operator), db: Session = Depends(get_db)) -> NudgeOut:
    if payload.target_zone_id and not db.get(Zone, payload.target_zone_id):
        raise HTTPException(status_code=400, detail="target zone not found")
    n = Nudge(**payload.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return NudgeOut.model_validate(n)


@router.get("/nudges", response_model=list[NudgeOut])
def list_nudges(db: Session = Depends(get_db), active_only: bool = Query(default=True)) -> list[NudgeOut]:
    stmt = select(Nudge)
    if active_only:
        stmt = stmt.where(Nudge.is_active == True)  # noqa: E712
    rows = db.execute(stmt.order_by(Nudge.created_at.desc())).scalars().all()
    return [NudgeOut.model_validate(r) for r in rows]


# ---- analytics ------------------------------------------------------------


@router.get("/capacity/densities", response_model=list[ZoneDensityOut])
def densities(db: Session = Depends(get_db)) -> list[ZoneDensityOut]:
    zones = _all_zones(db)
    metrics = _all_recent_metrics(db)
    result = latest_density_by_zone(zones, metrics)
    return [ZoneDensityOut(**d.__dict__) for d in result]


@router.get("/capacity/forecasts", response_model=list[SaturationForecastOut])
def forecasts(db: Session = Depends(get_db)) -> list[SaturationForecastOut]:
    zones = _all_zones(db)
    metrics = _all_recent_metrics(db)
    events = _all_active_events(db)
    projections = project_saturation(zones, metrics)
    projections = apply_event_pressure(projections, events)
    return [SaturationForecastOut(**f.__dict__) for f in projections]


def _build_balancer(db: Session, user: User | None = None) -> list[BalancerRecommendationOut]:
    zones = _all_zones(db)
    metrics = _all_recent_metrics(db)
    densities_ = latest_density_by_zone(zones, metrics)
    recs = nearby_low_density_zones(densities_, zones)
    nudges = _active_nudges(db)

    out: list[BalancerRecommendationOut] = []
    for r in recs:
        nudge = pick_nudge_for_zone(nudges, r.to_zone_id)
        # Log issuance so we can measure conversion later.
        if nudge is not None and user is not None:
            db.add(
                NudgeIssuance(
                    nudge_id=nudge.id,
                    user_id=user.id,
                    alternative_zone_id=r.to_zone_id,
                )
            )
        out.append(
            BalancerRecommendationOut(
                **{k: v for k, v in r.__dict__.items()},
                attached_nudge=NudgeOut.model_validate(nudge) if nudge is not None else None,
            )
        )
    if user is not None:
        db.commit()
    return out


@router.get("/capacity/balancer", response_model=list[BalancerRecommendationOut])
def balancer(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[BalancerRecommendationOut]:
    return _build_balancer(db, user)


@router.post("/events/{event_id}/stagger", response_model=StaggeringPlan)
def stagger(event_id: str, payload: StaggeringRequest, _op: User = Depends(require_operator), db: Session = Depends(get_db)) -> StaggeringPlan:
    if payload.event_id != event_id:
        raise HTTPException(status_code=400, detail="event_id mismatch")
    ev = db.get(ZoneEvent, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="event not found")
    bands = generate_staggered_departures(
        event_end_at=ev.end_at,
        total_attendees=ev.expected_attendance,
        max_per_band=payload.max_per_band,
        band_minutes=payload.band_minutes,
    )
    return StaggeringPlan(
        event_id=ev.id,
        event_name=ev.name,
        event_end_at=ev.end_at,
        total_attendees=ev.expected_attendance,
        bands=[DepartureBandOut(**b.__dict__) for b in bands],
    )


# ---- dual-role views ------------------------------------------------------


@router.get("/operator/dashboard", response_model=OperatorDashboardView)
def operator_dashboard(_op: User = Depends(require_operator), db: Session = Depends(get_db)) -> OperatorDashboardView:
    zones = _all_zones(db)
    metrics = _all_recent_metrics(db)
    events = _all_active_events(db)

    densities_ = latest_density_by_zone(zones, metrics)
    projections = apply_event_pressure(project_saturation(zones, metrics), events)
    balancer_recs = _build_balancer(db, _op)

    return OperatorDashboardView(
        now=datetime.now(timezone.utc),
        zone_densities=[ZoneDensityOut(**d.__dict__) for d in densities_],
        forecasts=[SaturationForecastOut(**f.__dict__) for f in projections],
        balancer_recommendations=balancer_recs,
        active_events=[ZoneEventOut.model_validate(e) for e in events],
    )


@router.get("/capacity/for-attendee", response_model=AttendeeCapacityView)
def attendee_view(
    zone_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttendeeCapacityView:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="zone not found")

    zones = _all_zones(db)
    metrics = _all_recent_metrics(db)
    events = _all_active_events(db)

    densities_ = latest_density_by_zone(zones, metrics)
    projections = apply_event_pressure(project_saturation(zones, metrics), events)
    my_density = next((d for d in densities_ if d.zone_id == zone_id), None)
    my_forecast = next((f for f in projections if f.zone_id == zone_id), None)
    if my_density is None or my_forecast is None:
        raise HTTPException(status_code=404, detail="no metrics yet for this zone")

    # Only surface the balancer alt when the zone is actually congested — the
    # attendee UX shouldn't route people away from an empty zone.
    suggested: BalancerRecommendationOut | None = None
    if my_density.density_pct >= BALANCER_TRIGGER_PCT:
        recs = nearby_low_density_zones([d for d in densities_], zones)
        me_rec = next((r for r in recs if r.from_zone_id == zone_id), None)
        if me_rec is not None:
            nudges = _active_nudges(db)
            nudge = pick_nudge_for_zone(nudges, me_rec.to_zone_id)
            if nudge is not None:
                db.add(NudgeIssuance(nudge_id=nudge.id, user_id=user.id, alternative_zone_id=me_rec.to_zone_id))
                db.commit()
            suggested = BalancerRecommendationOut(
                **{k: v for k, v in me_rec.__dict__.items()},
                attached_nudge=NudgeOut.model_validate(nudge) if nudge is not None else None,
            )

    if my_density.density_pct >= SATURATION_THRESHOLD_PCT:
        tip = f"{zone.name} is saturated — consider heading to a nearby zone."
    elif my_forecast.status == "APPROACHING_SATURATION":
        tip = f"{zone.name} will fill up in ~{my_forecast.minutes_to_saturation or 60:.0f} min. Consider moving now."
    elif my_forecast.status == "RISING":
        tip = f"{zone.name} is filling up but still comfortable."
    else:
        tip = f"{zone.name} is quiet — good time to visit."

    return AttendeeCapacityView(
        zone_id=zone.id,
        zone_name=zone.name,
        density_pct=my_density.density_pct,
        status=my_forecast.status,
        forecast=SaturationForecastOut(**my_forecast.__dict__),
        suggested_alternative=suggested,
        tip=tip,
    )
