"""LangGraph orchestrator — the top-level control loop.

Graph shape:

    ┌──────────┐    ┌──────────┐    ┌────────────┐
    │  plan    │──▶ │ execute  │──▶ │ supervise  │
    └──────────┘    └──────────┘    └─────┬──────┘
         ▲                                │
         │       (retry if errors)        │
         └────────────────────────────────┘
                                          │ (accept)
                                          ▼
                                        [END]

The Supervisor decides whether to retry (loop back to `plan`) or terminate.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.executor import execute_node
from app.agents.planner import plan_node
from app.agents.state import AgentState
from app.agents.supervisor import supervise_node

log = logging.getLogger("agents.orchestrator")


def _router(state: AgentState) -> str:
    """Post-Supervisor branching.

    - If Supervisor cleared `trip` and populated `errors` → replan.
    - Otherwise (accepted, or watchdog exhausted) → END.
    """
    if state.get("trip") is None and state.get("errors"):
        # But respect the watchdog — if iteration >= max, don't loop forever.
        if state.get("iteration", 0) < state.get("max_iterations", 3):
            return "plan"
    return END


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("supervise", supervise_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "supervise")
    graph.add_conditional_edges("supervise", _router, {"plan": "plan", END: END})

    return graph.compile()


# Compile once at import; the compiled graph is reused across requests.
_compiled = None


def _get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def plan_trip(
    user_goal: str,
    *,
    traveler_id: str = "USR-anon",
    constraints_hint: dict[str, Any] | None = None,
    max_iterations: int = 3,
) -> dict[str, Any]:
    """Public entry point. Kicks off the agent DAG and returns the terminal state.

    Returns a dict shaped like:
      {
        "trip": {SuperTrip JSON} | None,
        "hitl_required": bool,
        "hitl_reason": str | None,
        "errors": [...],
        "warnings": [...],
        "iterations": int,
        "trace": [{agent, ...}, ...]
      }
    """
    graph = _get_graph()
    initial: AgentState = {
        "user_goal": user_goal,
        "traveler_id": traveler_id,
        "constraints_hint": constraints_hint or {},
        "iteration": 0,
        "max_iterations": max_iterations,
        "errors": [],
        "warnings": [],
        "trace": [],
    }
    log.info("plan_trip start: goal=%s traveler=%s", user_goal[:80], traveler_id)
    final = graph.invoke(initial)
    return {
        "trip": final.get("trip"),
        "hitl_required": bool(final.get("hitl_required")),
        "hitl_reason": final.get("hitl_reason"),
        "errors": final.get("errors") or [],
        "warnings": final.get("warnings") or [],
        "iterations": final.get("iteration", 0),
        "trace": final.get("trace") or [],
    }
