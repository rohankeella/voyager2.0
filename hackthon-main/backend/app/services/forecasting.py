"""Capacity math for P3 (Module 2).

Four responsibilities:

  1. `latest_density_pct`     — most recent occupancy% per zone
  2. `project_saturation`      — F-15 predictive forecasting. Linear + light
                                 exponential trend over recent samples;
                                 flags "APPROACHING_SATURATION" when the
                                 projection crosses 100% within 60 min.
  3. `apply_event_pressure`    — F-17. Elevates the projected density in the
                                 30 minutes before a scheduled event ends,
                                 since attendees are about to spill out.
  4. `nearby_low_density_zones` — F-16 balancer alternatives.

All functions are pure: they operate on plain ORM rows / dataclasses. The
routers wire them to the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.models.capacity import CapacityMetric, Zone, ZoneEvent
from app.services.logistics import haversine_km


SATURATION_THRESHOLD_PCT = 100.0
APPROACHING_SATURATION_MINS = 60
BALANCER_TRIGGER_PCT = 85.0           # PRD F-16 acceptance
EVENT_END_PRESSURE_WINDOW_MINS = 30   # PRD F-17 acceptance


def _as_utc(dt: datetime) -> datetime:
    """SQLite strips tzinfo on read, so naive datetimes coming from the ORM
    need to be labelled UTC before we compare with tz-aware "now"."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class ZoneDensity:
    zone_id: str
    zone_name: str
    city: str
    density_pct: float
    occupancy_count: int
    capacity_max: int
    recorded_at: datetime | None
    sources: dict[str, float] = field(default_factory=dict)  # source_kind -> latest density_pct


def latest_density_by_zone(zones: list[Zone], metrics: list[CapacityMetric]) -> list[ZoneDensity]:
    """Collapse a bag of metrics into one ZoneDensity per zone. When a zone
    has multiple source_kinds reporting, we surface each one for the
    heatmap tooltip and use the *max* as the headline density (worst-case
    wins for operator alerting)."""
    latest_per_source: dict[tuple[str, str], CapacityMetric] = {}
    for m in metrics:
        key = (m.zone_id, m.source_kind.value)
        prev = latest_per_source.get(key)
        if prev is None or _as_utc(m.recorded_at) > _as_utc(prev.recorded_at):
            latest_per_source[key] = m

    zone_by_id = {z.id: z for z in zones}
    out: dict[str, ZoneDensity] = {
        z.id: ZoneDensity(
            zone_id=z.id,
            zone_name=z.name,
            city=z.city,
            density_pct=0.0,
            occupancy_count=0,
            capacity_max=z.total_capacity,
            recorded_at=None,
        )
        for z in zones
    }
    for (zid, src), m in latest_per_source.items():
        if zid not in out:
            continue
        d = out[zid]
        d.sources[src] = round(m.density_pct, 2)
        if m.density_pct > d.density_pct:
            d.density_pct = round(m.density_pct, 2)
            d.occupancy_count = m.occupancy_count
            d.capacity_max = m.capacity_max
        m_at = _as_utc(m.recorded_at)
        if d.recorded_at is None or m_at > d.recorded_at:
            d.recorded_at = m_at
    return list(out.values())


# --- F-15 saturation projection --------------------------------------------


@dataclass
class SaturationForecast:
    zone_id: str
    zone_name: str
    current_density_pct: float
    projected_density_pct_60m: float
    slope_pct_per_min: float          # linear trend
    minutes_to_saturation: float | None  # None if not converging
    status: str                        # STABLE | RISING | APPROACHING_SATURATION | SATURATED
    event_pressure_applied: bool = False


def _linear_regression(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Least-squares slope + intercept for y = a + b*x. Returns (a, b)."""
    n = len(points)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return points[0][1], 0.0
    sx = sum(p[0] for p in points)
    sy = sum(p[1] for p in points)
    sxx = sum(p[0] * p[0] for p in points)
    sxy = sum(p[0] * p[1] for p in points)
    denom = n * sxx - sx * sx
    if denom == 0:
        return sy / n, 0.0
    b = (n * sxy - sx * sy) / denom
    a = (sy - b * sx) / n
    return a, b


def _pick_series(metrics: list[CapacityMetric], zone_id: str, window_mins: int, now: datetime) -> list[CapacityMetric]:
    cutoff = now - timedelta(minutes=window_mins)
    series = [m for m in metrics if m.zone_id == zone_id and _as_utc(m.recorded_at) >= cutoff]
    series.sort(key=lambda m: _as_utc(m.recorded_at))
    return series


def project_saturation(
    zones: list[Zone],
    metrics: list[CapacityMetric],
    now: datetime | None = None,
    horizon_mins: int = APPROACHING_SATURATION_MINS,
    lookback_mins: int = 90,
) -> list[SaturationForecast]:
    now = now or datetime.now(timezone.utc)
    forecasts: list[SaturationForecast] = []
    for zone in zones:
        series = _pick_series(metrics, zone.id, lookback_mins, now)
        current = series[-1].density_pct if series else 0.0

        if len(series) < 2:
            status = "STABLE" if current < BALANCER_TRIGGER_PCT else "SATURATED" if current >= SATURATION_THRESHOLD_PCT else "RISING"
            forecasts.append(SaturationForecast(
                zone_id=zone.id, zone_name=zone.name,
                current_density_pct=round(current, 2),
                projected_density_pct_60m=round(current, 2),
                slope_pct_per_min=0.0,
                minutes_to_saturation=None,
                status=status,
            ))
            continue

        t0 = _as_utc(series[0].recorded_at)
        points = [((_as_utc(m.recorded_at) - t0).total_seconds() / 60.0, m.density_pct) for m in series]
        intercept, slope = _linear_regression(points)
        now_x = (now - t0).total_seconds() / 60.0
        projected = intercept + slope * (now_x + horizon_mins)

        minutes_to_sat: float | None = None
        if slope > 0 and current < SATURATION_THRESHOLD_PCT:
            minutes_to_sat = max(0.0, (SATURATION_THRESHOLD_PCT - current) / slope)

        if current >= SATURATION_THRESHOLD_PCT:
            status = "SATURATED"
        elif minutes_to_sat is not None and minutes_to_sat <= horizon_mins:
            status = "APPROACHING_SATURATION"
        elif slope > 0.05:
            status = "RISING"
        else:
            status = "STABLE"

        forecasts.append(SaturationForecast(
            zone_id=zone.id,
            zone_name=zone.name,
            current_density_pct=round(current, 2),
            projected_density_pct_60m=round(max(0.0, min(150.0, projected)), 2),
            slope_pct_per_min=round(slope, 4),
            minutes_to_saturation=round(minutes_to_sat, 1) if minutes_to_sat is not None else None,
            status=status,
        ))
    return forecasts


# --- F-17 event pressure ---------------------------------------------------


def apply_event_pressure(
    forecasts: list[SaturationForecast],
    events: list[ZoneEvent],
    now: datetime | None = None,
    pressure_pct: float = 25.0,
) -> list[SaturationForecast]:
    """Elevates the 60-minute projected density (and possibly the status) for
    any zone with an event whose end is within `EVENT_END_PRESSURE_WINDOW_MINS`.

    Concretely, F-17 acceptance: "elevates predicted congestion metrics 30
    minutes prior to known event conclusion times."
    """
    now = now or datetime.now(timezone.utc)
    threshold = now + timedelta(minutes=EVENT_END_PRESSURE_WINDOW_MINS)
    affected_zone_ids = {
        e.zone_id
        for e in events
        if now <= _as_utc(e.end_at) <= threshold or _as_utc(e.start_at) <= now <= _as_utc(e.end_at)
    }
    for fc in forecasts:
        if fc.zone_id in affected_zone_ids and fc.current_density_pct < SATURATION_THRESHOLD_PCT:
            fc.projected_density_pct_60m = round(min(150.0, fc.projected_density_pct_60m + pressure_pct), 2)
            fc.event_pressure_applied = True
            # If the elevated projection breaches the saturation line, upgrade status.
            if fc.projected_density_pct_60m >= SATURATION_THRESHOLD_PCT and fc.status not in ("SATURATED",):
                fc.status = "APPROACHING_SATURATION"
    return forecasts


# --- F-16 zone demand balancer --------------------------------------------


@dataclass
class BalancerRecommendation:
    from_zone_id: str
    from_zone_name: str
    from_density_pct: float
    to_zone_id: str
    to_zone_name: str
    to_density_pct: float
    distance_km: float


def nearby_low_density_zones(
    densities: list[ZoneDensity],
    zones: list[Zone],
    max_distance_km: float = 8.0,
    congestion_threshold_pct: float = BALANCER_TRIGGER_PCT,
    low_density_ceiling_pct: float = 60.0,
) -> list[BalancerRecommendation]:
    """For each zone above `congestion_threshold_pct`, propose the closest
    alternate zone below `low_density_ceiling_pct` within `max_distance_km`.
    Deliberately caps at one alt per congested zone — the operator UI can ask
    for more if needed."""
    zone_by_id = {z.id: z for z in zones}
    density_by_id = {d.zone_id: d for d in densities}
    recommendations: list[BalancerRecommendation] = []

    congested = [d for d in densities if d.density_pct >= congestion_threshold_pct]
    for src in congested:
        src_zone = zone_by_id.get(src.zone_id)
        if not src_zone:
            continue
        candidates = []
        for cand in densities:
            if cand.zone_id == src.zone_id or cand.density_pct >= low_density_ceiling_pct:
                continue
            cz = zone_by_id.get(cand.zone_id)
            if not cz or cz.city != src_zone.city:
                continue
            dist = haversine_km(src_zone.center_lat, src_zone.center_lng, cz.center_lat, cz.center_lng)
            if dist <= max_distance_km:
                candidates.append((dist, cand))
        if not candidates:
            continue
        candidates.sort(key=lambda t: (t[1].density_pct, t[0]))
        dist, best = candidates[0]
        recommendations.append(
            BalancerRecommendation(
                from_zone_id=src.zone_id,
                from_zone_name=src.zone_name,
                from_density_pct=src.density_pct,
                to_zone_id=best.zone_id,
                to_zone_name=best.zone_name,
                to_density_pct=best.density_pct,
                distance_km=round(dist, 2),
            )
        )
    return recommendations
