"""Planner Agent — hierarchical goal decomposition.

Takes a natural-language traveler goal + soft constraints and produces a
structural DAG draft. It intentionally does NOT call travel APIs; that's the
Executor's job. The Planner reasons about:

  • which node types are needed (flights, transfers, hotels, activities)
  • temporal placement (day-of-trip + hour)
  • dependency order (depends_on_indices — positional refs into the draft)
  • rough cost budgets so Supervisor can early-reject over-budget drafts

Output is a `PlannerDraft` (Pydantic), so we get schema-enforced JSON out of
Gemini via LangChain's `with_structured_output()`.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.config import get_settings

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
    duration_hours: float = Field(ge=0.5, le=24.0, default=2.0)
    estimated_cost_usd: float = Field(ge=0.0, default=0.0)


class PlannerDraft(BaseModel):
    max_budget_usd: float = Field(gt=0)
    start_date: str = Field(description="ISO date YYYY-MM-DD")
    end_date: str = Field(description="ISO date YYYY-MM-DD, strictly after start_date")
    home_location: str | None = None
    traveler_count: int = Field(default=1, ge=1, le=20)
    preferences: list[str] = Field(default_factory=list, description="Free-form tags like 'art', 'food'")
    nodes: list[PlannerNodeDraft] = Field(min_length=2, max_length=30)


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

EXAMPLE for "5-day Paris trip from Bangalore, $2500 budget, love art":
  Day 1: flight BLR→CDG, ground transfer CDG→hotel, hotel checkin
  Day 2: Louvre morning, lunch, Musée d'Orsay afternoon, dinner
  Day 3: Versailles day-trip, dinner
  Day 4: Montmartre walking tour, lunch, Musée Rodin, dinner
  Day 5: hotel checkout, ground transfer to CDG, flight CDG→BLR

Return ONLY the PlannerDraft JSON — no prose, no markdown."""


# ---- llm factory ----------------------------------------------------------


def _get_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in backend/.env — Planner Agent cannot run. "
            "Get a free key at https://aistudio.google.com/apikey."
        )
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.6,
        max_output_tokens=4096,
    )


# ---- LangGraph node -------------------------------------------------------


def plan_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node function — reads user_goal from state, writes draft_trip."""
    user_goal = state.get("user_goal", "").strip()
    if not user_goal:
        return {"errors": ["Planner: user_goal was empty"], "iteration": state.get("iteration", 0) + 1}

    hint = state.get("constraints_hint") or {}
    prior_errors = state.get("errors") or []

    # Build the user message
    user_lines = [f"Traveler goal: {user_goal}"]
    if hint:
        user_lines.append(f"Structured hints: {hint}")
    if prior_errors:
        user_lines.append(
            "Previous attempt was rejected by the Supervisor with these errors — fix them:"
        )
        user_lines.extend(f"  - {e}" for e in prior_errors[-5:])
    user_message = "\n".join(user_lines)

    log.info("Planner iteration=%s goal=%s", state.get("iteration", 0), user_goal[:80])

    llm = _get_llm().with_structured_output(PlannerDraft)
    try:
        draft: PlannerDraft = llm.invoke(
            [SystemMessage(content=_SYSTEM), HumanMessage(content=user_message)]
        )
    except Exception as e:
        log.exception("Planner LLM call failed")
        return {
            "errors": [f"Planner LLM error: {type(e).__name__}: {e}"],
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
