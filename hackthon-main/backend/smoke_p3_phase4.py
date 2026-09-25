"""DTO-P3 Phase 4 smoke — Operator Command Center end-to-end.

Flow:
  1. Register operator user (via SQL direct — no self-serve upgrade path)
  2. Register two traveller users
  3. Each traveller POSTs a SuperTrip to /api/super-trips
  4. Operator hits /api/operator/command-center
  5. Assert: 2 active trips, both appear in Gantt data, vendor matrix rolls up

Run: python smoke_p3_phase4.py  (backend must already be running on :8000)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx

from app.database import SessionLocal
from app.models.user import User, UserRole

BASE = "http://127.0.0.1:8000"


def seed_operator() -> tuple[str, str]:
    """Register a traveler then flip their role to OPERATOR directly in the DB."""
    email = f"op_{uuid.uuid4().hex[:6]}@example.com"
    r = httpx.post(
        f"{BASE}/api/auth/register",
        json={"email": email, "password": "opsops-12345", "full_name": "Operator Smoke", "country": "IN"},
        timeout=10,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    user_id = r.json()["user"]["id"]

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.role = UserRole.OPERATOR
        db.commit()

    print(f"[operator] seeded {email} as OPERATOR")

    # Re-login to get a fresh token that reflects the role (JWT payload uses sub only,
    # so role changes take effect immediately — but new tokens are still cleaner).
    r = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": "opsops-12345"},
        timeout=10,
    )
    r.raise_for_status()
    return email, r.json()["access_token"]


def seed_traveler(idx: int) -> str:
    email = f"t{idx}_{uuid.uuid4().hex[:6]}@example.com"
    r = httpx.post(
        f"{BASE}/api/auth/register",
        json={"email": email, "password": "trip1234pw", "full_name": f"Traveler {idx}", "country": "IN"},
        timeout=10,
    )
    r.raise_for_status()
    print(f"[traveler {idx}] registered {email}")
    return r.json()["access_token"]


def sample_trip(super_trip_id: str) -> dict:
    start = datetime(2027, 5, 10, 8, 0, tzinfo=timezone.utc)
    return {
        "super_trip_id": super_trip_id,
        "traveler_id": "USR-smoke",
        "status": "pending_review",
        "global_constraints": {
            "max_budget_usd": 4000,
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=5)).isoformat(),
            "home_location": "Bangalore",
            "traveler_count": 1,
            "preferences": {"tags": ["art"]},
        },
        "nodes": [
            {
                "node_id": "N-01-FLIGHT",
                "type": "amadeus_flight_order",
                "status": "pending",
                "execution_data": {
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(hours=12)).isoformat(),
                    "origin_lat": 13.1979, "origin_lng": 77.7063,
                    "destination_lat": 49.0097, "destination_lng": 2.5479,
                    "pnr_number": "SMK01",
                },
                "depends_on": [],
                "financials": {"cost_usd": 900, "payment_status": "unpaid", "vendor_account": "acc_airline_6E"},
                "title": "BLR -> CDG",
                "requires_approval": True,
            },
            {
                "node_id": "N-02-HOTEL",
                "type": "amadeus_hotel_booking",
                "status": "pending",
                "execution_data": {
                    "start_time": (start + timedelta(hours=14)).isoformat(),
                    "end_time": (start + timedelta(days=4, hours=11)).isoformat(),
                    "location_label": "Le Marais Boutique",
                    "lat": 48.8566, "lng": 2.3522,
                },
                "depends_on": ["N-01-FLIGHT"],
                "financials": {"cost_usd": 480, "payment_status": "unpaid", "vendor_account": "acc_hotel_LM"},
                "title": "Paris hotel · 4 nights",
            },
            {
                "node_id": "N-03-ACTIVITY",
                "type": "activity",
                "status": "pending",
                "execution_data": {
                    "start_time": (start + timedelta(days=1, hours=10)).isoformat(),
                    "end_time": (start + timedelta(days=1, hours=13)).isoformat(),
                    "location_label": "Louvre Museum",
                    "lat": 48.8606, "lng": 2.3376,
                },
                "depends_on": ["N-02-HOTEL"],
                "financials": {"cost_usd": 60, "payment_status": "unpaid", "vendor_account": "acc_activity"},
                "title": "Louvre guided tour",
            },
        ],
    }


def run() -> None:
    print("=== Phase 4 smoke ===")

    _, op_token = seed_operator()
    op_headers = {"Authorization": f"Bearer {op_token}"}

    t1 = seed_traveler(1)
    t2 = seed_traveler(2)

    for i, tok in enumerate([t1, t2], start=1):
        payload = {"payload": sample_trip(f"ST-SMK-{uuid.uuid4().hex[:4].upper()}"), "source_prompt": "smoke"}
        r = httpx.post(
            f"{BASE}/api/super-trips",
            headers={"Authorization": f"Bearer {tok}"},
            json=payload, timeout=10,
        )
        r.raise_for_status()
        print(f"[traveler {i}] persisted {r.json()['id']}")

    print("\n[operator] GET /api/operator/command-center")
    r = httpx.get(f"{BASE}/api/operator/command-center", headers=op_headers, timeout=15)
    r.raise_for_status()
    data = r.json()

    print(f"  active_trip_count = {data['active_trip_count']}")
    print(f"  lights_summary    = {data['lights_summary']}")
    print(f"  vendor_matrix rows= {len(data['vendor_matrix'])}")
    for v in data["vendor_matrix"]:
        print(f"    {v['vendor_account']:20s} nodes={v['node_count']} total=${v['total_usd']:.0f} routed=${v['routed_usd']:.0f}")
    for trip in data["active_trips"][:2]:
        print(f"  trip {trip['super_trip_id']}: {len(trip['nodes'])} nodes, lights={trip['lights']}")
        for n in trip["nodes"]:
            print(f"    {n['node_id']:16s} {n['type']:22s} {n['status_light']:6s} · {n['status_reason']}")

    # Assertions
    assert data["active_trip_count"] >= 2, "expected ≥2 active trips"
    assert len(data["vendor_matrix"]) >= 3, "expected ≥3 vendors (airline+hotel+activity)"
    airline = next((v for v in data["vendor_matrix"] if v["vendor_account"] == "acc_airline_6E"), None)
    assert airline is not None
    # Two trips × 1 flight each × $900
    assert abs(airline["total_usd"] - 1800.0) < 1e-3, f"airline total should be $1800, got {airline['total_usd']}"

    print("\n[OK] Phase 4 smoke passed.")


if __name__ == "__main__":
    run()
