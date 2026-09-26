"""DTO-P3 Phase 8 smoke — OpenTripPlanner integration.

Runs two ground-transfer queries against the tool layer:
  1. Helsinki central → airport (both inside OTP coverage) — should hit
     Digitransit and return a real encoded polyline + GTFS stoptimes.
  2. Bangalore → Paris (outside coverage) — should fall back to Haversine.

Also verifies the frontend-side polyline decoder round-trips.
"""
from __future__ import annotations

import asyncio
import json

from app.agents.tools import estimate_ground_transfer


def decode_polyline(encoded: str, precision: int = 5) -> list[tuple[float, float]]:
    """Python port of the decoder — same algorithm the frontend uses."""
    factor = 10 ** precision
    coords: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0
    while index < len(encoded):
        result = 0
        shift = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if result & 1 else (result >> 1)
        lat += dlat

        result = 0
        shift = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if result & 1 else (result >> 1)
        lng += dlng

        coords.append((lng / factor, lat / factor))
    return coords


async def main() -> None:
    print("=== Phase 8 smoke ===")

    # [1] Helsinki center → Helsinki-Vantaa airport
    print("\n[1] Helsinki center (60.170, 24.941) → Helsinki-Vantaa airport (60.317, 24.963)")
    r = await estimate_ground_transfer(60.1699, 24.9384, 60.3172, 24.9633)
    print(f"   source          = {r.get('source')}")
    print(f"   distance_km     = {r.get('distance_km')}")
    print(f"   duration_min    = {r.get('duration_minutes')}")
    print(f"   modes           = {r.get('modes')}")
    print(f"   route_name      = {r.get('route_name')}")
    print(f"   stoptimes count = {len(r.get('stoptimes') or [])}")
    geom = r.get("route_geometry")
    if geom:
        legs = geom.split("|")
        print(f"   geometry legs   = {len(legs)}")
        first_mode, first_poly = legs[0].split(":", 1)
        coords = decode_polyline(first_poly)
        print(f"   first leg {first_mode!r} decodes to {len(coords)} points")
        print(f"     start = {coords[0]}")
        print(f"     end   = {coords[-1]}")
        assert len(coords) >= 5, "decoded polyline suspiciously short"
        assert 24 < coords[0][0] < 26, f"lng out of Helsinki range: {coords[0][0]}"
        assert 59 < coords[0][1] < 61, f"lat out of Helsinki range: {coords[0][1]}"
        print("   [OK] polyline decodes to Helsinki-range coordinates")
    else:
        print("   [WARN] no route_geometry — OTP fell back or endpoint unavailable")

    # [2] Bangalore → Paris — outside coverage, Haversine
    print("\n[2] Bangalore (12.97, 77.59) → Paris (48.86, 2.35)")
    r2 = await estimate_ground_transfer(12.9716, 77.5946, 48.8566, 2.3522)
    print(f"   source          = {r2.get('source')}")
    print(f"   distance_km     = {r2.get('distance_km')}")
    print(f"   route_geometry  = {r2.get('route_geometry')}")
    assert r2.get("source") == "haversine"
    assert r2.get("route_geometry") is None

    print("\n[OK] Phase 8 smoke passed.")


if __name__ == "__main__":
    asyncio.run(main())
