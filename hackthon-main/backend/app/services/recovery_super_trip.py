"""DTO-P3 Phase 5 — Recovery plan generator for SuperTrip DAGs.

Per PRD § "Cascade Protocol" step 4: after cascade detects conflicts, we
generate 3 candidate mitigation strategies for the operator (or the traveler
via the /copilot banner) to pick from:

  1. **fastest**       — accept the delay as-is on every downstream node.
                          Cancels/adjusts the minimum necessary. Best when
                          the delay is small enough that buffers absorb it.
  2. **cheapest**      — cancel the highest-cost non-refundable downstream
                          activities that no longer fit. Minimises out-of-pocket
                          penalty by voiding what would otherwise be missed.
  3. **least_impact**  — keep the largest number of downstream nodes intact:
                          shift only up to the first hard bound (e.g. return
                          flight), cancel anything beyond that.

Each plan carries:
  - `plan_id` (deterministic: `fastest` / `cheapest` / `least_impact`)
  - `actions` (list of `{action, node_id, detail, monetary_penalty?}` )
  - `cost_delta_usd` (positive = extra cost, negative = savings from cancellation)
  - `time_delta_mins` (total additional delay across trip)
  - `nodes_modified`, `nodes_cancelled`, `nodes_kept`
  - `summary` (one-line human description for the UI)
  - `trip_after` (a SuperTrip dict the operator can apply verbatim)

Pure functions: same inputs → same output.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_iso(v: Any) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        s = str(v).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _cost_penalty(node: dict) -> float:
    """How much money is lost if we cancel this node?

    Since our schema doesn't yet carry refundability, we approximate:
      - flights, hotel bookings → 50% non-refundable
      - transfers, activities, meals → 100% non-refundable (small tickets)
      - guide sessions → 100% (locked slot)
    """
    cost = float((node.get("financials") or {}).get("cost_usd") or 0)
    t = str(node.get("type") or "")
    if t in {"amadeus_flight_order", "amadeus_hotel_booking"}:
        return round(cost * 0.5, 2)
    return round(cost, 2)


# ---- individual plan generators -------------------------------------------


def _plan_fastest(trip: dict, cascade: dict) -> dict[str, Any]:
    """Accept the delay wholesale — shift everything, cancel nothing.

    Only works cleanly when `broken_chronology` is empty; if it isn't, we
    still keep everything but note that some nodes are now at-risk.
    """
    delta = int(cascade.get("delta_mins") or 0)
    trip_after = copy.deepcopy(cascade["trip_after"])
    affected = cascade.get("affected_node_ids") or []
    late = cascade.get("hotel_late_check_ins") or []

    actions: list[dict[str, Any]] = []
    for hotel in late:
        actions.append(
            {
                "action": "notify_late_check_in",
                "node_id": hotel["node_id"],
                "detail": f"Hotel arrival slips by {hotel['minutes_late']}m — request late-arrival protocol.",
                "monetary_penalty": 0.0,
            }
        )
    for aid in affected:
        actions.append(
            {
                "action": "shift",
                "node_id": aid,
                "detail": f"Push start/end by {delta}m.",
                "monetary_penalty": 0.0,
            }
        )

    nodes = trip_after.get("nodes") or []
    kept = len([n for n in nodes if str(n.get("status")) not in {"cancelled"}])

    summary = (
        f"Accept the {delta}m slip; no bookings cancelled. "
        f"{len(late)} late arrival(s) flagged."
    )
    return {
        "plan_id": "fastest",
        "label": "Fastest recovery",
        "summary": summary,
        "actions": actions,
        "cost_delta_usd": 0.0,
        "time_delta_mins": delta,
        "nodes_modified": len(affected),
        "nodes_cancelled": 0,
        "nodes_kept": kept,
        "trip_after": trip_after,
    }


def _plan_cheapest(trip: dict, cascade: dict) -> dict[str, Any]:
    """Cancel high-cost non-refundable items that no longer fit chronologically.

    Ranks broken nodes by `_cost_penalty` — cancelling the biggest liabilities
    first minimises out-of-pocket exposure.
    """
    trip_after = copy.deepcopy(cascade["trip_after"])
    nodes = trip_after.get("nodes") or []
    by_id = {n.get("node_id"): n for n in nodes}
    broken_ids = {b["node_id"] for b in (cascade.get("broken_chronology") or [])}

    # Rank descending by cost — cancel the most expensive broken node first.
    candidates = [n for n in nodes if n.get("node_id") in broken_ids]
    candidates.sort(key=_cost_penalty, reverse=True)

    actions: list[dict[str, Any]] = []
    total_penalty = 0.0
    cancelled: list[str] = []
    for n in candidates:
        penalty = _cost_penalty(n)
        n["status"] = "cancelled"
        cancelled.append(n.get("node_id"))
        actions.append(
            {
                "action": "cancel",
                "node_id": n.get("node_id"),
                "detail": f"Cancel {n.get('title') or n.get('type')} to avoid chronology break.",
                "monetary_penalty": penalty,
            }
        )
        total_penalty += penalty

    # Any hotel late check-ins still need flagging.
    for hotel in cascade.get("hotel_late_check_ins") or []:
        actions.append(
            {
                "action": "notify_late_check_in",
                "node_id": hotel["node_id"],
                "detail": f"Hotel arrival slips by {hotel['minutes_late']}m.",
                "monetary_penalty": 0.0,
            }
        )

    kept = len([n for n in nodes if str(n.get("status")) not in {"cancelled"}])

    # Cost delta = penalty (money burned) minus refunds already booked. Since
    # we do not model refunds yet, treat penalty as extra cost.
    cost_delta = total_penalty

    return {
        "plan_id": "cheapest",
        "label": "Cheapest recovery",
        "summary": (
            f"Cancel {len(cancelled)} affected node(s) to avoid rebooking fees. "
            f"Est. penalty ${cost_delta:.0f}."
        ),
        "actions": actions,
        "cost_delta_usd": round(cost_delta, 2),
        "time_delta_mins": int(cascade.get("delta_mins") or 0),
        "nodes_modified": len(cascade.get("affected_node_ids") or []),
        "nodes_cancelled": len(cancelled),
        "nodes_kept": kept,
        "trip_after": trip_after,
    }


def _plan_least_impact(trip: dict, cascade: dict) -> dict[str, Any]:
    """Preserve as many downstream nodes as possible by absorbing the delay
    against the shortest tolerant buffer, and only cancelling the minimum
    strictly required to fit the day-of-return flight.

    For a hackathon-shaped demo we approximate: keep all nodes whose new
    start still lands within the trip's `global_constraints.end_date`,
    cancel anything that spills past the return flight.
    """
    trip_after = copy.deepcopy(cascade["trip_after"])
    nodes = trip_after.get("nodes") or []
    gc = trip_after.get("global_constraints") or {}
    hard_end = _parse_iso(gc.get("end_date"))

    actions: list[dict[str, Any]] = []
    cancelled: list[str] = []
    total_penalty = 0.0

    # Find the return flight (last node whose type == amadeus_flight_order).
    return_flight = None
    for n in reversed(nodes):
        if str(n.get("type")) == "amadeus_flight_order":
            return_flight = n
            break

    if return_flight is not None and hard_end is not None:
        rf_start = _parse_iso((return_flight.get("execution_data") or {}).get("start_time"))
        if rf_start and rf_start > hard_end:
            # We're spilling past the trip end — cancel the shortest
            # non-flight non-hotel nodes until we might fit. For simplicity
            # in Phase 5, cancel the smallest activities.
            candidates = [
                n for n in nodes
                if str(n.get("type")) in {"activity", "meal", "guide_session", "custom"}
                and str(n.get("status")) not in {"cancelled", "completed"}
            ]
            candidates.sort(key=lambda n: float((n.get("financials") or {}).get("cost_usd") or 0))
            for n in candidates[:2]:  # cap the cascade
                penalty = _cost_penalty(n)
                n["status"] = "cancelled"
                cancelled.append(n.get("node_id"))
                actions.append(
                    {
                        "action": "cancel",
                        "node_id": n.get("node_id"),
                        "detail": f"Trim {n.get('title')} to free up return-flight time.",
                        "monetary_penalty": penalty,
                    }
                )
                total_penalty += penalty

    # Shift-notes for the rest
    for aid in cascade.get("affected_node_ids") or []:
        if aid in cancelled:
            continue
        actions.append(
            {
                "action": "shift",
                "node_id": aid,
                "detail": f"Slide start/end by {cascade.get('delta_mins')}m; absorbed by buffer.",
                "monetary_penalty": 0.0,
            }
        )

    kept = len([n for n in nodes if str(n.get("status")) not in {"cancelled"}])

    return {
        "plan_id": "least_impact",
        "label": "Least impact",
        "summary": (
            f"Preserve {kept} node(s); cancel {len(cancelled)} smallest items "
            f"only if the return flight is at risk."
        ),
        "actions": actions,
        "cost_delta_usd": round(total_penalty, 2),
        "time_delta_mins": int(cascade.get("delta_mins") or 0),
        "nodes_modified": len(cascade.get("affected_node_ids") or []) - len(cancelled),
        "nodes_cancelled": len(cancelled),
        "nodes_kept": kept,
        "trip_after": trip_after,
    }


def generate_recovery_plans(trip: dict, cascade: dict) -> list[dict[str, Any]]:
    """Return the 3 candidate plans in a stable order."""
    return [
        _plan_fastest(trip, cascade),
        _plan_cheapest(trip, cascade),
        _plan_least_impact(trip, cascade),
    ]
