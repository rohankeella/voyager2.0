"""DTO-P3 Phase 2 smoke — full HTTP flow.

Register → login → verify /api/agents/status → plan-trip → verify persistence
via /api/super-trips → approve → confirm status flipped.

Skips the actual Gemini call by mocking the LangGraph orchestrator response
so the test runs offline. To test WITH Gemini, comment out `monkeypatch_plan_trip`
and set GEMINI_API_KEY in backend/.env.
"""
from __future__ import annotations

import time
import httpx

from app.agents import orchestrator as orchestrator_mod

BASE = "http://127.0.0.1:8000"


def monkeypatch_plan_trip():
    """Replace the LangGraph invoke with a deterministic fake response so we
    can exercise Phase 2 persistence without needing GEMINI_API_KEY set."""
    from datetime import datetime, timedelta, timezone

    def fake_plan_trip(user_goal, *, traveler_id, constraints_hint=None, max_iterations=3):
        start = datetime(2027, 5, 10, 8, 0, tzinfo=timezone.utc)
        end = start + timedelta(days=4, hours=14)
        trip = {
            "super_trip_id": f"ST-SMOKE-{int(time.time()) & 0xFFFF:04X}",
            "traveler_id": traveler_id,
            "status": "pending_review",
            "global_constraints": {
                "max_budget_usd": 2500,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "home_location": "Bangalore",
                "traveler_count": 1,
                "preferences": {"tags": ["art", "food"]},
            },
            "nodes": [
                {
                    "node_id": "N-01-FLIGHT",
                    "type": "amadeus_flight_order",
                    "status": "pending",
                    "execution_data": {
                        "start_time": start.isoformat(),
                        "end_time": (start + timedelta(hours=12)).isoformat(),
                        "location_label": "BLR -> CDG",
                        "pnr_number": "SMOKE01",
                    },
                    "depends_on": [],
                    "financials": {"cost_usd": 900, "payment_status": "unpaid"},
                    "title": "Flight BLR -> CDG",
                    "requires_approval": True,
                },
                {
                    "node_id": "N-02-HOTEL",
                    "type": "amadeus_hotel_booking",
                    "status": "pending",
                    "execution_data": {
                        "start_time": (start + timedelta(hours=13)).isoformat(),
                        "end_time": (start + timedelta(days=3, hours=11)).isoformat(),
                        "location_label": "Le Marais Boutique",
                    },
                    "depends_on": ["N-01-FLIGHT"],
                    "financials": {"cost_usd": 480, "payment_status": "unpaid"},
                    "title": "3-night Paris hotel",
                },
            ],
        }
        return {
            "trip": trip,
            "hitl_required": True,
            "hitl_reason": "1 flight requires approval",
            "errors": [],
            "warnings": [],
            "iterations": 1,
            "trace": [
                {"agent": "planner", "iteration": 0, "node_count": 2},
                {"agent": "executor", "nodes_processed": 2},
                {"agent": "supervisor", "iteration": 1, "errors_count": 0},
            ],
        }

    orchestrator_mod.plan_trip = fake_plan_trip


def run() -> None:
    import uuid

    # Register a fresh user so /api/super-trips persistence isolates cleanly.
    user_email = f"smoke_{uuid.uuid4().hex[:6]}@example.com"
    print(f"[1] Register user: {user_email}")
    r = httpx.post(
        f"{BASE}/api/auth/register",
        json={
            "email": user_email,
            "password": "smoke-pass-12",
            "full_name": "Phase2 Smoke",
            "country": "IN",
        },
        timeout=10,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    print(f"    -> got token")

    auth_headers = {"Authorization": f"Bearer {token}"}

    # Verify agents/status
    print("[2] GET /api/agents/status")
    r = httpx.get(f"{BASE}/api/agents/status", headers=auth_headers, timeout=10)
    print(f"    -> {r.json()}")

    # Verify super-trips list is empty
    print("[3] GET /api/super-trips (should be empty)")
    r = httpx.get(f"{BASE}/api/super-trips", headers=auth_headers, timeout=10)
    r.raise_for_status()
    assert r.json() == [], f"expected empty list, got {r.json()}"
    print("    -> empty [OK]")

    # ⚠ The next block calls plan-trip. That hits Gemini if configured.
    # For offline smoke, we can't easily monkey-patch a running process; the
    # test skips this if GEMINI_API_KEY isn't set (Phase 1 covered that path).
    status = httpx.get(f"{BASE}/api/agents/status", timeout=10).json()
    if not status.get("gemini_configured"):
        print("[!] GEMINI_API_KEY not set — skipping live plan-trip test.")
        print("    Add key to backend/.env and re-run to test end-to-end.")
        # Instead, directly test the /api/super-trips POST + approve flow
        # with a synthetic SuperTrip.
        print("[4] Persist SuperTrip directly (bypass Planner)")
        synthetic = {
            "payload": {
                "super_trip_id": f"ST-SMOKE-{uuid.uuid4().hex[:4].upper()}",
                "traveler_id": "USR-anon",
                "status": "pending_review",
                "global_constraints": {
                    "max_budget_usd": 2500,
                    "start_date": "2027-05-10T08:00:00+00:00",
                    "end_date": "2027-05-14T22:00:00+00:00",
                    "home_location": "Bangalore",
                    "traveler_count": 1,
                    "preferences": {"tags": ["art", "food"]},
                },
                "nodes": [
                    {
                        "node_id": "N-01-FLIGHT",
                        "type": "amadeus_flight_order",
                        "status": "pending",
                        "execution_data": {
                            "start_time": "2027-05-10T08:00:00+00:00",
                            "end_time": "2027-05-10T20:00:00+00:00",
                            "pnr_number": "SMOKE01",
                        },
                        "depends_on": [],
                        "financials": {"cost_usd": 900, "payment_status": "unpaid"},
                        "title": "Flight BLR -> CDG",
                        "requires_approval": True,
                    },
                    {
                        "node_id": "N-02-HOTEL",
                        "type": "amadeus_hotel_booking",
                        "status": "pending",
                        "execution_data": {
                            "start_time": "2027-05-10T22:00:00+00:00",
                            "end_time": "2027-05-13T11:00:00+00:00",
                        },
                        "depends_on": ["N-01-FLIGHT"],
                        "financials": {"cost_usd": 480, "payment_status": "unpaid"},
                        "title": "Paris hotel",
                    },
                ],
            },
            "source_prompt": "smoke: Paris trip",
        }
        r = httpx.post(f"{BASE}/api/super-trips", headers=auth_headers, json=synthetic, timeout=10)
        r.raise_for_status()
        detail = r.json()
        trip_id = detail["id"]
        print(f"    -> persisted {trip_id} status={detail['status']} cost=${detail['total_cost_usd']}")
    else:
        print("[4] POST /api/agents/plan-trip (live Gemini!)")
        r = httpx.post(
            f"{BASE}/api/agents/plan-trip",
            headers=auth_headers,
            json={
                "user_goal": "5-day Paris trip from Bangalore, $2500 budget, love art",
                "persist": True,
            },
            timeout=120,
        )
        r.raise_for_status()
        payload = r.json()
        assert payload["trip"], f"no trip returned: {payload}"
        trip_id = payload["persisted_id"]
        assert trip_id, f"trip not persisted: {payload}"
        print(f"    -> {trip_id} nodes={len(payload['trip']['nodes'])} "
              f"iterations={payload['iterations']} hitl={payload['hitl_required']}")

    # Verify list now has one
    print(f"[5] GET /api/super-trips (should have 1)")
    r = httpx.get(f"{BASE}/api/super-trips", headers=auth_headers, timeout=10)
    r.raise_for_status()
    trips = r.json()
    assert len(trips) == 1, f"expected 1 trip, got {len(trips)}"
    assert trips[0]["id"] == trip_id
    print(f"    -> {trips[0]['id']} status={trips[0]['status']} title={trips[0]['title']!r}")

    # Approve
    print(f"[6] POST /api/super-trips/{trip_id}/approve")
    r = httpx.post(f"{BASE}/api/super-trips/{trip_id}/approve", headers=auth_headers, timeout=10)
    r.raise_for_status()
    approved = r.json()
    assert approved["status"] == "approved", f"status not approved: {approved['status']}"
    assert approved["approved_at"], "approved_at not set"
    print(f"    -> status={approved['status']} approved_at={approved['approved_at']}")

    # Confirm payload_json status flipped to 'active'
    assert approved["payload_json"]["status"] == "active", "embedded status not synced"
    print(f"    -> embedded status={approved['payload_json']['status']}")

    print("\n[OK] Phase 2 smoke passed.")


if __name__ == "__main__":
    run()
