"""DTO-P3 Phase 1 smoke test — Executor + Supervisor without touching Gemini.

Builds a synthetic PlannerDraft (what Gemini would emit) and runs it through
Executor + Supervisor end-to-end. Verifies the resulting SuperTrip validates
against the strict schema.

Run: python smoke_p3_agents.py
"""
from __future__ import annotations

import json

from app.agents.executor import execute_node
from app.agents.supervisor import supervise_node
from app.schemas.super_trip import SuperTrip


def synthetic_draft() -> dict:
    """A 4-day Bangalore → Paris → Bangalore trip Planner would plausibly emit."""
    return {
        "max_budget_usd": 4000.0,
        "start_date": "2027-05-10",
        "end_date": "2027-05-14",
        "home_location": "Bangalore",
        "traveler_count": 1,
        "preferences": ["art", "food"],
        "nodes": [
            # Day 1 — outbound
            {
                "type": "amadeus_flight_order",
                "title": "Flight BLR → CDG",
                "origin_city": "Bangalore",
                "destination_city": "Paris",
                "start_day": 1,
                "start_hour": 8,
                "duration_hours": 12,
                "estimated_cost_usd": 900,
                "depends_on_indices": [],
            },
            {
                "type": "otp_ground_transfer",
                "title": "CDG → Hotel Le Marais",
                "origin_city": "Paris",
                "destination_city": "Paris",
                "start_day": 1,
                "start_hour": 22,
                "duration_hours": 1,
                "estimated_cost_usd": 40,
                "depends_on_indices": [0],
            },
            {
                "type": "amadeus_hotel_booking",
                "title": "Le Marais Boutique (4 nights)",
                "location_city": "Paris",
                "start_day": 1,
                "start_hour": 23,
                "duration_hours": 80,
                "estimated_cost_usd": 480,
                "depends_on_indices": [1],
            },
            # Day 2 — Louvre + lunch
            {
                "type": "activity",
                "title": "Louvre Museum guided tour",
                "location_city": "Paris",
                "location_label": "Musée du Louvre",
                "start_day": 2,
                "start_hour": 10,
                "duration_hours": 3,
                "estimated_cost_usd": 60,
                "depends_on_indices": [2],
            },
            {
                "type": "meal",
                "title": "Bistrot Paul Bert dinner",
                "location_city": "Paris",
                "start_day": 2,
                "start_hour": 19,
                "duration_hours": 2,
                "estimated_cost_usd": 55,
                "depends_on_indices": [3],
            },
            # Day 3 — Versailles
            {
                "type": "activity",
                "title": "Versailles day-trip",
                "location_city": "Versailles",
                "start_day": 3,
                "start_hour": 9,
                "duration_hours": 8,
                "estimated_cost_usd": 90,
                "depends_on_indices": [2],
            },
            # Day 4 — return
            {
                "type": "otp_ground_transfer",
                "title": "Hotel → CDG",
                "origin_city": "Paris",
                "destination_city": "Paris",
                "start_day": 4,
                "start_hour": 6,
                "duration_hours": 1,
                "estimated_cost_usd": 40,
                "depends_on_indices": [2],
            },
            {
                "type": "amadeus_flight_order",
                "title": "Flight CDG → BLR",
                "origin_city": "Paris",
                "destination_city": "Bangalore",
                "start_day": 4,
                "start_hour": 10,
                "duration_hours": 12,
                "estimated_cost_usd": 850,
                "depends_on_indices": [6],
            },
        ],
    }


def run() -> None:
    print("=== DTO-P3 Phase 1 smoke test (Executor + Supervisor) ===")
    state = {
        "user_goal": "4-day Paris art & food trip from Bangalore, $4000 budget",
        "traveler_id": "USR-smoke-1",
        "draft_trip": synthetic_draft(),
        "iteration": 1,
        "max_iterations": 3,
        "errors": [],
        "warnings": [],
        "trace": [],
    }

    # --- Executor ---
    exec_delta = execute_node(state)
    print(f"[Executor] processed {len(exec_delta['trip']['nodes'])} nodes, "
          f"warnings={len(exec_delta.get('warnings', []))}")
    for w in exec_delta.get("warnings", [])[:3]:
        print(f"           warn: {w}")
    state.update(exec_delta)

    # --- Supervisor ---
    sup_delta = supervise_node(state)
    print(f"[Supervisor] errors={len(sup_delta.get('errors', []))} "
          f"hitl={sup_delta.get('hitl_required')} ")
    if sup_delta.get("errors"):
        for e in sup_delta["errors"][:5]:
            print(f"             err: {e}")
    if sup_delta.get("hitl_reason"):
        print(f"             hitl_reason: {sup_delta['hitl_reason']}")
    state.update(sup_delta)

    # --- Validate final trip against strict schema ---
    trip_dict = state.get("trip")
    if not trip_dict:
        print("[FAIL] no trip in final state")
        return

    trip = SuperTrip.model_validate(trip_dict)
    print(f"[OK] SuperTrip validated: {trip.super_trip_id}")
    print(f"     status={trip.status.value}")
    print(f"     nodes={len(trip.nodes)}, total_cost_usd={trip.total_cost_usd():.2f}, "
          f"budget=${trip.global_constraints.max_budget_usd:.2f}, within={trip.within_budget()}")
    print(f"     topological order: {trip.topological_order()}")

    # Blast radius from the outbound flight
    fl = next(n for n in trip.nodes if "FLIGHT" in n.node_id)
    print(f"     descendants of {fl.node_id}: {sorted(trip.descendants(fl.node_id))}")

    # Serialise the whole thing so we can see judges the money-shot JSON
    print("\n=== Final SuperTrip (first 900 chars of JSON) ===")
    payload = trip.model_dump(mode="json")
    print(json.dumps(payload, indent=2, default=str)[:900] + "...")


if __name__ == "__main__":
    run()
