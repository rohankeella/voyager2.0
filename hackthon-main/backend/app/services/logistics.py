"""Distance / travel-time helpers used by the gatekeeper (F-04) and maps
routes (F-03).

If GOOGLE_MAPS_API_KEY is set the maps router upgrades to the real Distance
Matrix API. Otherwise everything falls back to Haversine + a fixed
per-mode speed heuristic, so the recommendation engine still works offline.
"""

from __future__ import annotations

import math
from datetime import datetime, time
from typing import Literal

TravelMode = Literal["walking", "driving", "transit"]

# Rough average speeds (km/h) for the offline heuristic. Deliberately
# conservative so we don't under-estimate travel time.
MODE_SPEED_KMH: dict[TravelMode, float] = {
    "walking": 4.5,
    "driving": 25.0,   # city driving with lights/traffic
    "transit": 20.0,   # bus/metro effective end-to-end
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometers."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def estimated_travel_mins(
    lat1: float, lng1: float, lat2: float, lng2: float, mode: TravelMode = "driving"
) -> int:
    dist_km = haversine_km(lat1, lng1, lat2, lng2)
    speed = MODE_SPEED_KMH.get(mode, MODE_SPEED_KMH["driving"])
    hours = dist_km / speed if speed > 0 else 0
    return max(1, int(round(hours * 60)))


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def is_open_at(
    hours: list, target: datetime
) -> bool:
    """Given a list of OperatingHour ORM rows (or dict-like) and a datetime,
    return True if the venue is open. Empty hours means 24/7."""
    if not hours:
        return True
    weekday = target.weekday()  # 0=Mon
    t = target.time()
    for h in hours:
        dow = getattr(h, "day_of_week", None) if not isinstance(h, dict) else h.get("day_of_week")
        open_s = getattr(h, "open_time", None) if not isinstance(h, dict) else h.get("open_time")
        close_s = getattr(h, "close_time", None) if not isinstance(h, dict) else h.get("close_time")
        if dow != weekday:
            continue
        if _parse_hhmm(open_s) <= t <= _parse_hhmm(close_s):
            return True
    return False


def window_overlaps_hours(
    hours: list, arrive_at: datetime, depart_by: datetime
) -> bool:
    """True if the venue is open for at least part of [arrive_at, depart_by]."""
    if not hours:
        return True
    if arrive_at >= depart_by:
        return False
    weekday = arrive_at.weekday()
    for h in hours:
        dow = getattr(h, "day_of_week", None) if not isinstance(h, dict) else h.get("day_of_week")
        if dow != weekday:
            continue
        open_s = getattr(h, "open_time", None) if not isinstance(h, dict) else h.get("open_time")
        close_s = getattr(h, "close_time", None) if not isinstance(h, dict) else h.get("close_time")
        open_t = _parse_hhmm(open_s)
        close_t = _parse_hhmm(close_s)
        if arrive_at.time() <= close_t and depart_by.time() >= open_t:
            return True
    return False
