"""Tool registry — thin async wrappers around existing services.

The Executor Agent picks a tool based on the node's `type` and calls it to
enrich the node's `execution_data` and `financials`. All tools degrade
gracefully to mock data when external credentials are missing (same pattern
as the /api/travel router).

Tools return plain dicts so LangGraph state stays serialisable.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.amadeus import amadeus_client
from app.services import otp as otp_service
from app.services.travel_mock import (
    mock_flights,
    mock_hotels,
    mock_locations,
    resolve_iata_mock,
)


# INR → USD conversion — matches travel_mock. Real prod would call FX API.
_INR_PER_USD = 83.0


def _inr_to_usd(inr: float) -> float:
    return round(inr / _INR_PER_USD, 2)


# ---- location resolution --------------------------------------------------


async def resolve_location(keyword: str) -> dict[str, Any] | None:
    """Free-text → IATA + geo. Uses Amadeus if configured, else mock table."""
    kw = (keyword or "").strip()
    if not kw:
        return None

    if amadeus_client.is_configured:
        try:
            iata = await amadeus_client.resolve_iata(kw)
            if iata:
                return {"iata": iata, "source": "amadeus"}
        except Exception:
            pass

    hits = mock_locations(kw)
    if hits.results:
        first = hits.results[0]
        return {
            "iata": first.iata_code,
            "name": first.name,
            "city": first.city_name,
            "country": first.country_code,
            "lat": (first.geo or {}).get("latitude"),
            "lng": (first.geo or {}).get("longitude"),
            "source": "mock",
        }

    fallback = resolve_iata_mock(kw)
    return {"iata": fallback, "source": "mock"} if fallback else None


# ---- flight ---------------------------------------------------------------


async def search_flight(
    origin: str,
    destination: str,
    departure_date: str,
    *,
    return_date: str | None = None,
    adults: int = 1,
    currency: str = "INR",
) -> dict[str, Any] | None:
    """Returns the cheapest offer for the given route. Falls back to mocks."""
    orig = await resolve_location(origin)
    dest = await resolve_location(destination)
    if not orig or not dest or not orig.get("iata") or not dest.get("iata"):
        return None

    # Prefer the mock generator — deterministic, no external latency, always available.
    # Real Amadeus can be plugged in when creds are present (see travel router).
    resp = mock_flights(
        orig["iata"], dest["iata"], departure_date, return_date, currency, max_offers=3
    )
    if not resp.offers:
        return None

    cheapest = min(resp.offers, key=lambda o: float(o.total))
    first_seg = cheapest.itineraries[0].segments[0] if cheapest.itineraries else None
    last_seg = cheapest.itineraries[0].segments[-1] if cheapest.itineraries else None
    total_inr = float(cheapest.total)

    return {
        "offer_id": cheapest.id,
        "origin_iata": resp.origin,
        "destination_iata": resp.destination,
        "origin_lat": orig.get("lat"),
        "origin_lng": orig.get("lng"),
        "destination_lat": dest.get("lat"),
        "destination_lng": dest.get("lng"),
        "carrier_code": first_seg.carrier_code if first_seg else None,
        "flight_number": first_seg.number if first_seg else None,
        "departure_at": first_seg.departure_at if first_seg else None,
        "arrival_at": last_seg.arrival_at if last_seg else None,
        "cost_local": total_inr,
        "currency": cheapest.currency,
        "cost_usd": _inr_to_usd(total_inr),
        "stops": sum(s.stops for itin in cheapest.itineraries for s in itin.segments),
    }


# ---- hotel ----------------------------------------------------------------


async def search_hotel(
    city: str,
    check_in: str,
    check_out: str,
    *,
    adults: int = 1,
) -> dict[str, Any] | None:
    """Returns the cheapest hotel offer in the city."""
    loc = await resolve_location(city)
    iata = (loc or {}).get("iata") if loc else None
    if not iata:
        return None

    resp = mock_hotels(iata, check_in, check_out, adults)
    if not resp.offers:
        return None

    best_group = min(
        (g for g in resp.offers if g.offers),
        key=lambda g: float(g.offers[0].price.total),
        default=None,
    )
    if not best_group or not best_group.offers:
        return None

    off = best_group.offers[0]
    total_inr = float(off.price.total)

    # Look up matching listing to get coordinates (mock hotels have them)
    listing = next(
        (h for h in resp.hotels if h.hotel_id == best_group.hotel_id), None
    )
    geo = listing.geo if listing else None

    return {
        "hotel_id": best_group.hotel_id,
        "hotel_name": best_group.hotel_name,
        "room_description": off.room_description,
        "check_in": off.check_in_date,
        "check_out": off.check_out_date,
        "cost_local": total_inr,
        "currency": off.price.currency,
        "cost_usd": _inr_to_usd(total_inr),
        "lat": (geo or {}).get("latitude") if geo else None,
        "lng": (geo or {}).get("longitude") if geo else None,
        "city_iata": iata,
    }


# ---- ground transfer (OTP stub) ------------------------------------------


async def estimate_ground_transfer(
    from_lat: float | None,
    from_lng: float | None,
    to_lat: float | None,
    to_lng: float | None,
    *,
    depart_at: datetime | None = None,
) -> dict[str, Any]:
    """Ground-transit planner.

    Two paths:
      1. If both endpoints fall within OTP coverage (default: Finland), we
         hit the OpenTripPlanner GraphQL API and get a real transit itinerary
         with encoded polyline + per-leg stoptime cross-reference.
      2. Otherwise, Haversine + 50 km/h heuristic, same as services/logistics.
    """
    have_coords = None not in (from_lat, from_lng, to_lat, to_lng)

    # ---- OTP path -----------------------------------------------------
    if have_coords and otp_service.within_default_coverage(
        float(from_lat), float(from_lng), float(to_lat), float(to_lng)  # type: ignore[arg-type]
    ):
        try:
            itin = await otp_service.plan_route(
                float(from_lat), float(from_lng),  # type: ignore[arg-type]
                float(to_lat), float(to_lng),      # type: ignore[arg-type]
                depart_at=depart_at,
            )
        except Exception:
            itin = None
        if itin:
            summary = otp_service.summarize_itinerary(itin)
            start = depart_at or datetime.now(timezone.utc)
            duration_mins = summary.get("duration_minutes", 30) or 30
            end = start + timedelta(minutes=duration_mins)
            distance_km = summary.get("distance_km", 0.0) or 0.0
            # Cost approximation for transit: €2 base + €0.15/km, converted
            # roughly to INR at ~₹90/EUR for the mock accounting layer.
            cost_local_inr = int(200 + distance_km * 15)
            return {
                "source": "opentripplanner",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "duration_minutes": duration_mins,
                "distance_km": distance_km,
                "cost_local": cost_local_inr,
                "currency": "INR",
                "cost_usd": _inr_to_usd(cost_local_inr),
                "route_geometry": summary.get("route_geometry"),
                "gtfs_id": summary.get("gtfs_id"),
                "route_name": summary.get("route_name"),
                "modes": summary.get("modes"),
                "stoptimes": summary.get("stoptimes"),
            }

    # ---- Haversine fallback ------------------------------------------
    duration_mins = 30
    distance_km = 0.0
    if have_coords:
        distance_km = _haversine_km(
            float(from_lat), float(from_lng),   # type: ignore[arg-type]
            float(to_lat), float(to_lng),       # type: ignore[arg-type]
        )
        duration_mins = max(10, int((distance_km / 50.0) * 60))

    start = depart_at or datetime.now(timezone.utc)
    end = start + timedelta(minutes=duration_mins)
    cost_inr = 100 + int(distance_km * 15)

    return {
        "source": "haversine",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "duration_minutes": duration_mins,
        "distance_km": round(distance_km, 1),
        "cost_local": cost_inr,
        "currency": "INR",
        "cost_usd": _inr_to_usd(cost_inr),
        "route_geometry": None,
    }


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ---- activity / experience -----------------------------------------------


def estimate_activity(
    title: str,
    location_label: str | None,
    duration_hours: float = 2.0,
    *,
    start_time: datetime | None = None,
    price_hint_usd: float | None = None,
) -> dict[str, Any]:
    """Local activity slot — the Planner emits these directly, but we
    normalize price and duration here so the DAG stays realistic."""
    duration_hours = max(0.5, min(duration_hours, 8.0))
    start = start_time or datetime.now(timezone.utc)
    end = start + timedelta(hours=duration_hours)
    cost_usd = price_hint_usd if price_hint_usd is not None else 25.0

    return {
        "title": title,
        "location_label": location_label,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "cost_usd": round(cost_usd, 2),
    }


# ---- registry -------------------------------------------------------------


TOOLS = {
    "resolve_location": resolve_location,
    "search_flight": search_flight,
    "search_hotel": search_hotel,
    "estimate_ground_transfer": estimate_ground_transfer,
    "estimate_activity": estimate_activity,
}
