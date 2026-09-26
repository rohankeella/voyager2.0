"""Planner Agent — hierarchical goal decomposition.

Takes a natural-language traveler goal + soft constraints and produces a
structural DAG draft. It intentionally does NOT call travel APIs; that's the
Executor's job. The Planner reasons about:

  • which node types are needed (flights, transfers, hotels, activities)
  • temporal placement (day-of-trip + hour)
  • dependency order (depends_on_indices — positional refs into the draft)
  • rough cost budgets so Supervisor can early-reject over-budget drafts

Output is a `PlannerDraft` (Pydantic), validated after Groq JSON generation.
"""

from __future__ import annotations

import logging
import json
import re
from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

from app.agents.state import AgentState
from app.services.groq import complete

log = logging.getLogger("agents.planner")


# ---- planner output schema ------------------------------------------------


class PlannerNodeDraft(BaseModel):
    type: str = Field(
        description=(
            "One of: amadeus_flight_order, amadeus_hotel_booking, "
            "otp_ground_transfer, activity, guide_session, meal, custom"
        )
    )
    title: str = Field(min_length=1, max_length=120)
    description: str | None = None
    depends_on_indices: list[int] = Field(
        default_factory=list,
        description=(
            "0-indexed positions of prerequisite nodes in this same list. "
            "Every flight must come before its downstream ground_transfer/hotel/activity."
        ),
    )
    origin_city: str | None = Field(
        default=None, description="Required for amadeus_flight_order and otp_ground_transfer"
    )
    destination_city: str | None = Field(
        default=None, description="Required for amadeus_flight_order and otp_ground_transfer"
    )
    location_city: str | None = Field(
        default=None,
        description="City for hotel/activity/meal/guide_session — where this happens",
    )
    location_label: str | None = None
    start_day: int = Field(ge=1, le=60, description="1-indexed day of trip (day 1 is start_date)")
    start_hour: int = Field(ge=0, le=23, default=10)
    duration_hours: float = Field(ge=0.5, le=24.0 * 60, default=2.0)  # hotel stays span days
    estimated_cost_usd: float = Field(ge=0.0, default=0.0)


class PlannerDraft(BaseModel):
    max_budget_usd: float = Field(gt=0)
    start_date: str = Field(description="ISO date YYYY-MM-DD")
    end_date: str = Field(description="ISO date YYYY-MM-DD, strictly after start_date")
    home_location: str | None = None
    destination: str | None = None
    traveler_count: int = Field(default=1, ge=1, le=20)
    preferences: list[str] = Field(default_factory=list, description="Free-form tags like 'art', 'food'")
    nodes: list[PlannerNodeDraft] = Field(min_length=2, max_length=30)

    @model_validator(mode="after")
    def validate_schedule(self):
        start, end = date.fromisoformat(self.start_date), date.fromisoformat(self.end_date)
        if start < date.today():
            raise ValueError("Choose future travel dates; the start date is in the past.")
        if end < start or (end - start).days >= 60:
            raise ValueError("Trip dates must span 1 to 60 days in chronological order.")
        for index, node in enumerate(self.nodes):
            if node.start_day > (end - start).days + 1:
                raise ValueError("An itinerary stop falls outside the requested dates.")
            if any(dep < 0 or dep >= index for dep in node.depends_on_indices):
                raise ValueError("Each dependency must refer to an earlier itinerary stop.")
        return self


# ---- system prompt --------------------------------------------------------


_SYSTEM = """You are the Planner Agent for Voyager, a Dynamic Tour Operations platform.

Your job: decompose a traveler's natural-language goal into a Directed Acyclic Graph (DAG)
of trip nodes. Every trip begins with a flight FROM home TO the first destination
and ends with a flight home. Between them: hotels, ground transfers, activities.

RULES YOU MUST FOLLOW:
1. Output valid JSON matching the PlannerDraft schema. Nothing else.
2. Use node types: amadeus_flight_order (flights), amadeus_hotel_booking (hotels),
   otp_ground_transfer (taxi/train/bus between two coords), activity (museum, tour,
   sight), meal (restaurant), guide_session (local guide), custom (anything else).
3. Set depends_on_indices as 0-based positions in THIS list. A hotel check-in
   depends on the flight that arrives that day. An activity depends on the hotel.
4. Assume USD costs. Ballpark estimates only — the Executor will refine with
   real API prices. Rough guides: intl flight $600-1200, hotel $80-250/night,
   activity $20-80, meal $15-60, ground transfer $10-80.
5. Total estimated cost must stay UNDER max_budget_usd. Leave ~15% headroom.
6. Days: day 1 = start_date, day 2 = start_date+1, etc.
7. Every non-flight node MUST depend on at least one earlier node (the flight
   or transfer that got the traveler to that city).
8. Return HOME as the last flight — its origin_city = trip destination, destination_city = home.
9. Avoid over-packing days. Max 3-4 activities per day, with meals between.
10. Respect the exact requested duration: a 5-day trip ends start_date + 4 days.
    Use future dates, never dates from examples. Structured travel dates are binding.
11. Set destination to the city being visited, not the home/departure city.
    Prefer saved travel preferences unless the current request overrides them.
12. Prices and transport schedules are estimates, not live availability or reservations.

EXAMPLE for "5-day Paris trip from Bangalore, $2500 budget, love art":
  Day 1: flight BLR→CDG, ground transfer CDG→hotel, hotel checkin
  Day 2: Louvre morning, lunch, Musée d'Orsay afternoon, dinner
  Day 3: Versailles day-trip, dinner
  Day 4: Montmartre walking tour, lunch, Musée Rodin, dinner
  Day 5: hotel checkout, ground transfer to CDG, flight CDG→BLR

Return ONLY the PlannerDraft JSON — no prose, no markdown."""


# ---- LangGraph node -------------------------------------------------------


def plan_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node function — reads user_goal from state, writes draft_trip."""
    user_goal = state.get("user_goal", "").strip()
    if not user_goal:
        return {"errors": ["Planner: user_goal was empty"], "iteration": state.get("iteration", 0) + 1}

    hint = state.get("constraints_hint") or {}
    prior_errors = state.get("errors") or []

    # Build the user message
    user_lines = [f"Today: {date.today().isoformat()}. If no dates are specified, start on {(date.today() + timedelta(days=30)).isoformat()}.", f"Traveler goal: {user_goal}"]
    duration = re.search(r"\b(\d{1,2})[ -]*days?\b", user_goal, re.I)
    if duration:
        user_lines.append(f"Required duration: {duration.group(1)} calendar days, including departure and return.")
    if hint:
        user_lines.append(f"Structured hints: {hint}")
    if prior_errors:
        user_lines.append(
            "Previous attempt was rejected by the Supervisor with these errors — fix them:"
        )
        user_lines.extend(f"  - {e}" for e in prior_errors[-5:])
    user_message = "\n".join(user_lines)

    log.info("Planner iteration=%s goal=%s", state.get("iteration", 0), user_goal[:80])

    try:
        draft = PlannerDraft.model_validate_json(complete([
            {"role": "system", "content": _SYSTEM + "\nJSON schema:\n" + json.dumps(PlannerDraft.model_json_schema())},
            {"role": "user", "content": user_message},
        ], json_mode=True))
        if hint.get("start_date") and draft.start_date != hint["start_date"]:
            raise ValueError("Use the traveler's selected start_date exactly.")
        if hint.get("end_date") and draft.end_date != hint["end_date"]:
            raise ValueError("Use the traveler's selected end_date exactly.")
        if duration and not hint.get("end_date") and (date.fromisoformat(draft.end_date) - date.fromisoformat(draft.start_date)).days + 1 != int(duration.group(1)):
            raise ValueError(f"Use exactly {duration.group(1)} calendar days, including departure and return.")
    except Exception as e:
        log.warning("Planner LLM call failed: %s", type(e).__name__)
        return {
            "errors": [str(e.detail) if isinstance(e, HTTPException) else f"Planner draft needs correction: {str(e)[:400]}"],
            "draft_trip": {},
            "trip": None,
            # Provider failures will not improve by spending more free-tier quota.
            "max_iterations": state.get("iteration", 0) + 1 if isinstance(e, HTTPException) else state.get("max_iterations", 3),
            "iteration": state.get("iteration", 0) + 1,
        }

    trace_entry = {
        "agent": "planner",
        "iteration": state.get("iteration", 0),
        "node_count": len(draft.nodes),
        "budget_est": sum(n.estimated_cost_usd for n in draft.nodes),
    }

    return {
        "draft_trip": draft.model_dump(mode="json"),
        "iteration": state.get("iteration", 0) + 1,
        "errors": [],  # clear prior errors — Planner has attempted a fix
        "trace": (state.get("trace") or []) + [trace_entry],
    }
