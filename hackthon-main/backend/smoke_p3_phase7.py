"""DTO-P3 Phase 7 smoke — Guide marketplace end-to-end.

Flow:
  1. Register guide user + create guide profile in Paris
  2. Register a traveler
  3. Search /api/guides?lat=..&tags=art → guide found
  4. Traveler POSTs booking request for tomorrow 14:00-17:00
  5. Guide accepts → status confirmed, slot locked
  6. Traveler tries a SECOND overlapping request (15:00-16:00) → guide accepts → REJECTED (lock)
  7. Non-overlapping request (evening 20:00-22:00) → accepts fine
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE = "http://127.0.0.1:8000"


def register(role: str) -> tuple[str, str]:
    email = f"{role}_{uuid.uuid4().hex[:6]}@example.com"
    r = httpx.post(
        f"{BASE}/api/auth/register",
        json={"email": email, "password": "guide12345pw", "full_name": f"{role.title()} Smoke", "country": "FR"},
        timeout=10,
    )
    r.raise_for_status()
    return email, r.json()["access_token"]


def run() -> None:
    print("=== Phase 7 smoke ===")
    _, guide_token = register("guide")
    guide_h = {"Authorization": f"Bearer {guide_token}"}
    _, trav_token = register("trav")
    trav_h = {"Authorization": f"Bearer {trav_token}"}

    # [1] Guide creates profile in Paris (Louvre area) with 'art' + 'food'
    print("\n[1] POST /api/guides (upsert)")
    profile = {
        "display_name": "Amélie · Paris art & food",
        "headline": "Louvre-to-Marais walking tours with a chef",
        "bio": "12 years leading art-history + culinary tours in central Paris.",
        "home_lat": 48.8606,
        "home_lng": 2.3376,
        "home_city": "Paris",
        "country_code": "FR",
        "radius_km": 30,
        "tags": ["art", "food", "history"],
        "languages": ["English", "French"],
        "hourly_rate_usd": 40.0,
        "min_hours": 2,
    }
    r = httpx.post(f"{BASE}/api/guides", headers=guide_h, json=profile, timeout=10)
    r.raise_for_status()
    guide = r.json()
    print(f"   guide_id={guide['id']}  rate=${guide['hourly_rate_usd']}/hr  tags={guide['tags']}")

    # [2] Traveler searches — Paris coords + art tag
    print("\n[2] GET /api/guides?lat=48.86&lng=2.35&tags=art,food")
    r = httpx.get(
        f"{BASE}/api/guides",
        params={"lat": 48.86, "lng": 2.35, "tags": "art,food", "max_distance_km": 10},
        headers=trav_h, timeout=10,
    )
    r.raise_for_status()
    hits = r.json()
    print(f"   hits: {len(hits)}")
    assert any(h["id"] == guide["id"] for h in hits), "guide not found in search"
    matched = next(h for h in hits if h["id"] == guide["id"])
    print(f"     matched_tags={matched['matched_tags']}  distance={matched['distance_km']}km")
    assert set(matched["matched_tags"]) >= {"art", "food"}

    # [3] Traveler books tomorrow 14:00-17:00
    tomorrow = datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
    payload_a = {
        "start_at": tomorrow.isoformat(),
        "end_at": (tomorrow + timedelta(hours=3)).isoformat(),
        "title": "Louvre + Marais walk",
        "location_label": "Louvre Museum",
        "location_lat": 48.8606,
        "location_lng": 2.3376,
        "tags": ["art"],
    }
    print("\n[3] POST /api/guides/{id}/bookings (14:00-17:00)")
    r = httpx.post(f"{BASE}/api/guides/{guide['id']}/bookings", headers=trav_h, json=payload_a, timeout=10)
    r.raise_for_status()
    booking_a = r.json()
    print(f"   booking_id={booking_a['id']}  status={booking_a['status']}  total=${booking_a['total_usd']}")
    assert booking_a["status"] == "requested"
    assert abs(booking_a["total_usd"] - 120.0) < 0.01

    # [4] Guide sees it in dashboard
    print("\n[4] GET /api/guides/me/bookings (guide)")
    r = httpx.get(f"{BASE}/api/guides/me/bookings", headers=guide_h, timeout=10)
    r.raise_for_status()
    my_bookings = r.json()
    print(f"   incoming: {len(my_bookings)}")
    assert any(b["id"] == booking_a["id"] for b in my_bookings)

    # [5] Guide accepts booking A → confirmed, slot locked
    print("\n[5] POST /api/guides/me/bookings/{id}/accept")
    r = httpx.post(f"{BASE}/api/guides/me/bookings/{booking_a['id']}/accept", headers=guide_h, timeout=10)
    r.raise_for_status()
    accepted = r.json()
    print(f"   status={accepted['status']}  responded_at={accepted['responded_at']}")
    assert accepted["status"] == "confirmed"

    # [6] Traveler tries a second overlapping request (15:00-16:00) — guide accept should be REJECTED
    payload_b = {
        "start_at": (tomorrow + timedelta(hours=1)).isoformat(),  # 15:00
        "end_at": (tomorrow + timedelta(hours=3)).isoformat(),    # 17:00 — overlap
        "title": "Overlap attempt",
        "tags": ["art"],
    }
    print("\n[6] POST second overlapping booking (15:00-17:00)")
    r = httpx.post(f"{BASE}/api/guides/{guide['id']}/bookings", headers=trav_h, json=payload_b, timeout=10)
    r.raise_for_status()
    booking_b = r.json()
    print(f"   booking_id={booking_b['id']}  status={booking_b['status']}")
    print("     Guide attempts to accept overlap...")
    r = httpx.post(f"{BASE}/api/guides/me/bookings/{booking_b['id']}/accept", headers=guide_h, timeout=10)
    assert r.status_code == 409, f"expected 409 on overlap, got {r.status_code}: {r.text}"
    print(f"     [OK] rejected: {r.json()['detail']}")

    # [7] Non-overlapping request (20:00-22:00) accepts fine
    payload_c = {
        "start_at": (tomorrow + timedelta(hours=6)).isoformat(),   # 20:00
        "end_at": (tomorrow + timedelta(hours=8)).isoformat(),     # 22:00
        "title": "Evening bistro walk",
        "tags": ["food"],
    }
    print("\n[7] POST non-overlap booking (20:00-22:00)")
    r = httpx.post(f"{BASE}/api/guides/{guide['id']}/bookings", headers=trav_h, json=payload_c, timeout=10)
    r.raise_for_status()
    booking_c = r.json()
    r = httpx.post(f"{BASE}/api/guides/me/bookings/{booking_c['id']}/accept", headers=guide_h, timeout=10)
    r.raise_for_status()
    print(f"   [OK] accepted: {r.json()['status']}")

    print("\n[OK] Phase 7 smoke passed.")


if __name__ == "__main__":
    run()
