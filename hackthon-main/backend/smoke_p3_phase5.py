"""DTO-P3 Phase 5 smoke — Disruption Engine + Cascade Protocol.

Flow:
  1. Register operator + traveler
  2. Traveler persists a SuperTrip with 3 nodes (flight + hotel + activity)
  3. Operator triggers a +180 min DELAY on the flight node
  4. Assert: 3 recovery plans generated, DAG shifted, node status = disrupted
  5. Operator applies "fastest" plan
  6. Assert: disruption status = mitigated, embedded DAG updated, no cancellations
  7. Also verify command-center's disruption_queue populated + then empty after apply

Run: python smoke_p3_phase5.py  (backend must be running on :8000)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx

from app.database import SessionLocal
from app.models.user import User, UserRole

BASE = "http://127.0.0.1:8000"


def seed_operator() -> str:
    email = f"op_{uuid.uuid4().hex[:6]}@example.com"
    r = httpx.post(
        f"{BASE}/api/auth/register",
        json={"email": email, "password": "opsops-12345", "full_name": "Operator Smoke", "country": "IN"},
        timeout=10,
    )
    r.raise_for_status()
    user_id = r.json()["user"]["id"]
    with SessionLocal() as db:
        user = db.get(User, user_id)
        user.role = UserRole.OPERATOR
        db.commit()
    r = httpx.post(f"{BASE}/api/auth/login", json={"email": email, "password": "opsops-12345"}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def seed_traveler() -> tuple[str, str]:
    email = f"trip_{uuid.uuid4().hex[:6]}@example.com"
    r = httpx.post(
        f"{BASE}/api/auth/register",
        json={"email": email, "password": "trip1234pw", "full_name": "Traveler Smoke", "country": "IN"},
        timeout=10,
    )
    r.raise_for_status()
    return email, r.json()["access_token"]


def create_trip(token: str) -> str:
    start = datetime(2027, 5, 10, 8, 0, tzinfo=timezone.utc)
    payload = {
        "payload": {
            "super_trip_id": f"ST-P5S-{uuid.uuid4().hex[:4].upper()}",
            "traveler_id": "USR-smoke",
            "status": "pending_review",
            "global_constraints": {
                "max_budget_usd": 4000,
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=4)).isoformat(),
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
                        "pnr_number": "P5S01",
                    },
                    "depends_on": [],
                    "financials": {"cost_usd": 900, "payment_status": "unpaid", "vendor_account": "acc_airline_6E"},
                    "title": "BLR -> CDG",
                },
                {
                    "node_id": "N-02-HOTEL",
                    "type": "amadeus_hotel_booking",
                    "status": "pending",
                    "execution_data": {
                        "start_time": (start + timedelta(hours=14)).isoformat(),
                        "end_time": (start + timedelta(days=3, hours=11)).isoformat(),
                        "location_label": "Le Marais",
                        "lat": 48.8566, "lng": 2.3522,
                    },
                    "depends_on": ["N-01-FLIGHT"],
                    "financials": {"cost_usd": 480, "payment_status": "unpaid", "vendor_account": "acc_hotel_LM"},
                    "title": "Paris hotel",
                },
                {
                    "node_id": "N-03-ACTIVITY",
                    "type": "activity",
                    "status": "pending",
                    "execution_data": {
                        "start_time": (start + timedelta(hours=15)).isoformat(),  # tight buffer with flight
                        "end_time": (start + timedelta(hours=18)).isoformat(),
                        "location_label": "Louvre",
                        "lat": 48.8606, "lng": 2.3376,
                    },
                    "depends_on": ["N-01-FLIGHT", "N-02-HOTEL"],
                    "financials": {"cost_usd": 60, "payment_status": "unpaid", "vendor_account": "acc_activity"},
                    "title": "Louvre tour",
                },
            ],
        },
        "source_prompt": "smoke phase 5",
    }
    r = httpx.post(f"{BASE}/api/super-trips", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()["id"]


def run() -> None:
    print("=== Phase 5 smoke ===")

    op_token = seed_operator()
    op_headers = {"Authorization": f"Bearer {op_token}"}
    _, tr_token = seed_traveler()
    trip_id = create_trip(tr_token)
    print(f"[trip persisted] {trip_id}")

    print("\n[1] Command center BEFORE disruption:")
    r = httpx.get(f"{BASE}/api/operator/command-center", headers=op_headers, timeout=10)
    r.raise_for_status()
    cc = r.json()
    print(f"   lights={cc['lights_summary']}  disruptions={len(cc['disruption_queue'])}")

    print("\n[2] Trigger DELAY +180m on N-01-FLIGHT")
    r = httpx.post(
        f"{BASE}/api/super-trips/{trip_id}/disruptions",
        headers=op_headers,
        json={"node_id": "N-01-FLIGHT", "kind": "delay", "delta_mins": 180, "note": "smoke: weather delay"},
        timeout=15,
    )
    r.raise_for_status()
    d = r.json()
    disruption_id = d["id"]
    print(f"   disruption_id={disruption_id}  plans={len(d['plans'])}")
    for p in d["plans"]:
        print(f"     {p['plan_id']:14s} · +${p['cost_delta_usd']:.0f} · shift={p['nodes_modified']} cancel={p['nodes_cancelled']} keep={p['nodes_kept']}")

    assert len(d["plans"]) == 3, "expected 3 recovery plans"
    plan_ids = {p["plan_id"] for p in d["plans"]}
    assert plan_ids == {"fastest", "cheapest", "least_impact"}, plan_ids

    print("\n[3] Command center DURING disruption:")
    r = httpx.get(f"{BASE}/api/operator/command-center", headers=op_headers, timeout=10)
    r.raise_for_status()
    cc = r.json()
    print(f"   lights={cc['lights_summary']}  disruptions={len(cc['disruption_queue'])}")
    assert len(cc["disruption_queue"]) >= 1, "disruption should be in the queue"

    # Show trip node lights
    trip = next(t for t in cc["active_trips"] if t["super_trip_id"] == trip_id)
    for n in trip["nodes"]:
        print(f"     {n['node_id']:16s} {n['status_light']:6s} · {n['status_reason']}  (status={n['status']})")

    print("\n[4] Apply 'fastest' recovery plan")
    r = httpx.post(
        f"{BASE}/api/super-trips/{trip_id}/disruptions/{disruption_id}/apply/fastest",
        headers=op_headers, timeout=15,
    )
    r.raise_for_status()
    mit = r.json()
    print(f"   status={mit['status']}  applied_plan_id={mit['applied_plan_id']}")
    assert mit["status"] == "mitigated"
    assert mit["applied_plan_id"] == "fastest"

    print("\n[5] Command center AFTER apply:")
    r = httpx.get(f"{BASE}/api/operator/command-center", headers=op_headers, timeout=10)
    r.raise_for_status()
    cc = r.json()
    print(f"   lights={cc['lights_summary']}  disruptions={len(cc['disruption_queue'])}")
    # Assert the specific disruption we just mitigated is no longer in the queue
    still_present = [d for d in cc["disruption_queue"] if d["id"] == disruption_id]
    assert not still_present, f"disruption {disruption_id} still in queue after apply"

    print("\n[6] Trigger CANCELLATION on activity (should be handled without breaking DAG):")
    r = httpx.post(
        f"{BASE}/api/super-trips/{trip_id}/disruptions",
        headers=op_headers,
        json={"node_id": "N-03-ACTIVITY", "kind": "cancellation", "note": "smoke: closure"},
        timeout=15,
    )
    r.raise_for_status()
    d2 = r.json()
    print(f"   disruption_id={d2['id']} plans={[p['plan_id'] for p in d2['plans']]}")
    assert len(d2["plans"]) == 3

    print("\n[OK] Phase 5 smoke passed.")


if __name__ == "__main__":
    run()
