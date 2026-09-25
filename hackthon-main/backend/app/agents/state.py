"""Shared state carried across the LangGraph nodes.

LangGraph merges partial dicts returned from each node into this TypedDict,
so each agent only needs to return the fields it produces. Anything derived
during a single node call goes here so downstream nodes can read it.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Inputs from the user
    user_goal: str                        # natural-language request
    traveler_id: str                      # USR-... identifier
    constraints_hint: dict[str, Any]      # optional structured constraint hints (budget, dates)

    # Outputs progressively built by agents
    draft_trip: dict[str, Any]            # Planner's rough DAG (may be invalid)
    trip: dict[str, Any]                  # Final validated SuperTrip JSON

    # Bookkeeping / control
    errors: list[str]                     # accumulated validation failures
    warnings: list[str]                   # non-fatal notes surfaced to UI
    iteration: int                        # how many Planner passes have run
    max_iterations: int                   # Supervisor's watchdog limit
    hitl_required: bool                   # true → block until user approves
    hitl_reason: str | None               # explanation shown in the Review card

    # Trace for debugging / demo transparency
    trace: list[dict[str, Any]]           # per-agent step log
