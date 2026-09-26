"""DTO-P3 Phase 8 — OpenTripPlanner GraphQL client.

Per PRD § "OpenTripPlanner (OTP) GraphQL Integration":

  The Executor Agent constructs GraphQL queries targeting the `route` object
  (gtfsId, longName) and the `legGeometry` object. The resulting encoded
  polyline is passed directly to the frontend CesiumJS/Mapbox renderer to
  draw the transit polylines on the globe.

Default endpoint: Digitransit's free public GTFS-GraphQL API for Finland
(https://digitransit.fi/en/developers/architecture/x-apis/1-routing-api/).
Set OTP_GRAPHQL_URL in backend/.env to point at your own OTP instance for
routes outside Finland.

If the endpoint is not configured or the request fails, callers should fall
back to a straight-line polyline (services/tools.estimate_ground_transfer
already handles this).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings

log = logging.getLogger("services.otp")


# Digitransit's plan query — returns geometry as an encoded polyline plus
# per-leg stop-time details (per PRD's Stoptime schema requirement).
_PLAN_QUERY = """
query PlanRoute(
  $fromLat: Float!, $fromLon: Float!,
  $toLat:   Float!, $toLon:   Float!,
  $date: String, $time: String,
  $modes: [TransportMode!]
) {
  plan(
    from: {lat: $fromLat, lon: $fromLon},
    to:   {lat: $toLat,   lon: $toLon},
    date: $date, time: $time,
    transportModes: $modes,
    numItineraries: 1
  ) {
    itineraries {
      duration
      startTime
      endTime
      walkDistance
      legs {
        mode
        duration
        distance
        startTime
        endTime
        from {
          name
          lat
          lon
          stop { gtfsId name platformCode }
        }
        to {
          name
          lat
          lon
          stop { gtfsId name }
        }
        route {
          gtfsId
          shortName
          longName
          type
          color
        }
        legGeometry {
          points
          length
        }
        realTime
      }
    }
  }
}
"""


def _bbox_contains(lat: float, lng: float, bbox: tuple[float, float, float, float]) -> bool:
    """bbox = (min_lat, min_lng, max_lat, max_lng)."""
    return bbox[0] <= lat <= bbox[2] and bbox[1] <= lng <= bbox[3]


# Digitransit coverage (rough): Finland mainland + Åland.
# lat 59.5..70.5, lng 19..32.
FINLAND_BBOX = (59.5, 19.0, 70.5, 32.0)


def within_default_coverage(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> bool:
    """Return True if BOTH endpoints are within the default OTP coverage
    (Finland when using Digitransit). Callers use this to decide whether to
    attempt OTP or go straight to the Haversine fallback.
    """
    return _bbox_contains(from_lat, from_lng, FINLAND_BBOX) and _bbox_contains(
        to_lat, to_lng, FINLAND_BBOX
    )


async def plan_route(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
    *,
    depart_at: datetime | None = None,
    modes: list[str] | None = None,
) -> dict[str, Any] | None:
    """Query the configured OTP endpoint. Returns the first itinerary
    (dict with legs + polylines) or None on any failure.

    Callers should fall back to a Haversine/straight-line estimate when
    this returns None.
    """
    settings = get_settings()
    url = settings.otp_graphql_url
    if not url:
        return None

    dt = depart_at or datetime.now(timezone.utc)
    variables: dict[str, Any] = {
        "fromLat": from_lat,
        "fromLon": from_lng,
        "toLat": to_lat,
        "toLon": to_lng,
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
        "modes": modes or ["TRANSIT", "WALK"],
    }
    headers = {
        "Content-Type": "application/json",
        # Digitransit requires this. Custom OTPs ignore it.
        "digitransit-subscription-key": settings.otp_subscription_key or "",
        "ET-Client-Name": settings.otp_client_name,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, headers=headers, json={"query": _PLAN_QUERY, "variables": variables})
    except httpx.HTTPError as e:
        log.warning("OTP request failed: %s", e)
        return None

    if r.status_code != 200:
        log.warning("OTP HTTP %s: %s", r.status_code, r.text[:200])
        return None

    payload = r.json()
    if "errors" in payload:
        log.warning("OTP errors: %s", payload["errors"][:1])
        return None

    itins = ((payload.get("data") or {}).get("plan") or {}).get("itineraries") or []
    if not itins:
        return None
    return itins[0]


def summarize_itinerary(itin: dict[str, Any]) -> dict[str, Any]:
    """Collapse an OTP itinerary into an ExecutionData-shaped dict.

    Concatenates every leg's encoded polyline into a comma-separated list of
    (mode|geometry) pairs so the frontend can render each leg with the right
    line style (walking dashed, rail solid, etc.).
    """
    legs = itin.get("legs") or []
    if not legs:
        return {}

    total_seconds = int(itin.get("duration") or 0)
    total_km = round(sum((l.get("distance") or 0) for l in legs) / 1000.0, 2)

    # Compose route_geometry as "mode1:polyline1|mode2:polyline2|..."
    parts: list[str] = []
    for leg in legs:
        mode = str(leg.get("mode") or "WALK")
        poly = (leg.get("legGeometry") or {}).get("points") or ""
        if poly:
            parts.append(f"{mode}:{poly}")
    route_geometry = "|".join(parts) or None

    # Take the first stop's gtfsId as a hint of transit "identity".
    first_transit_leg = next((l for l in legs if str(l.get("mode")) not in {"WALK", "BICYCLE"}), None)
    gtfs_id = None
    route_name = None
    if first_transit_leg:
        route_info = first_transit_leg.get("route") or {}
        gtfs_id = route_info.get("gtfsId")
        route_name = route_info.get("longName") or route_info.get("shortName")

    return {
        "duration_seconds": total_seconds,
        "duration_minutes": max(1, total_seconds // 60),
        "distance_km": total_km,
        "leg_count": len(legs),
        "route_geometry": route_geometry,
        "gtfs_id": gtfs_id,
        "route_name": route_name,
        "modes": [str(l.get("mode")) for l in legs],
        # Per-leg stoptime cross-reference so the DAG can respect precise arrivals.
        "stoptimes": [
            {
                "mode": l.get("mode"),
                "start_time": l.get("startTime"),
                "end_time": l.get("endTime"),
                "from": (l.get("from") or {}).get("name"),
                "to": (l.get("to") or {}).get("name"),
                "gtfs_id": ((l.get("route") or {}).get("gtfsId")) if l.get("route") else None,
            }
            for l in legs
        ],
    }
