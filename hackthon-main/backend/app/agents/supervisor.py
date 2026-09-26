"""Supervisor Agent — quality control + max-iteration watchdog.

Runs after the Executor. Validates the assembled SuperTrip against:

  1. Schema — the Pydantic SuperTrip model rejects cycles, unknown deps,
     duplicates, and end<start dates automatically.
  2. Budget — total cost must fit inside global_constraints.max_budget_usd.
  3. Chronology — every edge's target.start_time must be after source.end_time.
  4. HITL — if any node is `requires_approval` or if total cost is high,
     it flips hitl_required so the API surface can hold the trip in
     `pending_review` state until the user clicks approve.

If any check fails and iterations remain, it clears `trip` so the graph can
loop back to Planner with the errors as feedback. If we've exhausted
max_iterations, we return whatever we have and mark it as `hitl_required`
with an explanation (matches the "compile crisis report" behaviour in PRD §
"The Supervisor Agent").
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.agents.state import AgentState
from app.schemas.super_trip import NodeType, SuperTrip

# Hotel/hotel-offer nodes are containers — dependents may run inside the
# checkin→checkout window, not necessarily after checkout.
_CONTAINER_TYPES = {NodeType.AMADEUS_HOTEL_BOOKING, NodeType.AMADEUS_HOTEL_OFFER}

log = logging.getLogger("agents.supervisor")


# Any single node cost above this triggers HITL approval.
_HIGH_VALUE_USD = 500.0
_MAX_ITERATIONS_DEFAULT = 3


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def supervise_node(state: AgentState) -> dict[str, Any]:
    trip = state.get("trip")
    if not trip:
        return {"errors": (state.get("errors") or []) + ["Supervisor: no trip to validate"]}

    errors: list[str] = []
    warnings: list[str] = list(state.get("warnings") or [])

    # 1. Schema validation — this catches cycles, dup ids, unknown deps, etc.
    validated: SuperTrip | None = None
    try:
        validated = SuperTrip.model_validate(trip)
    except ValidationError as e:
        # Pydantic emits a list of errors; keep them terse for the Planner.
        for err in e.errors()[:5]:
            loc = ".".join(str(x) for x in err["loc"])
            errors.append(f"schema[{loc}]: {err['msg']}")

    # 2. Budget check
    if validated is not None:
        if not validated.within_budget():
            errors.append(
                f"budget: total ${validated.total_cost_usd():.2f} exceeds "
                f"max ${validated.global_constraints.max_budget_usd:.2f}"
            )

    # 3. Chronology on edges. Two flavours:
    #    - Container dep (hotel): target may start any time between
    #      source.start and source.end (activities happen DURING the stay).
    #    - Hard dep (flight/transfer/activity/meal): target.start >= source.end.
    if validated is not None:
        by_id = {n.node_id: n for n in validated.nodes}
        for n in validated.nodes:
            for dep in n.depends_on:
                src = by_id.get(dep)
                if not src:
                    continue
                src_start = _parse_iso(src.execution_data.start_time)
                src_end = _parse_iso(src.execution_data.end_time)
                tgt_start = _parse_iso(n.execution_data.start_time)
                if not tgt_start:
                    continue

                if src.type in _CONTAINER_TYPES:
                    if src_start and tgt_start < src_start:
                        errors.append(
                            f"chronology: {n.node_id} starts before its hotel {dep} checks in "
                            f"({tgt_start.isoformat()} < {src_start.isoformat()})"
                        )
                else:
                    if src_end and tgt_start < src_end:
                        errors.append(
                            f"chronology: {n.node_id} starts before {dep} ends "
                            f"({tgt_start.isoformat()} < {src_end.isoformat()})"
                        )

    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", _MAX_ITERATIONS_DEFAULT)

    trace_entry = {
        "agent": "supervisor",
        "iteration": iteration,
        "errors_count": len(errors),
        "budget_ok": validated.within_budget() if validated else False,
        "total_cost_usd": validated.total_cost_usd() if validated else None,
    }
    trace = (state.get("trace") or []) + [trace_entry]

    if errors and iteration < max_iter:
        # Loop back for another Planner pass.
        log.info("Supervisor rejected trip (iter=%s), looping back with %s errors", iteration, len(errors))
        return {
            "errors": errors,
            "trip": None,          # clear invalid trip so orchestrator re-plans
            "draft_trip": None,
            "warnings": warnings,
            "trace": trace,
        }

    if errors and iteration >= max_iter:
        # Watchdog fired — HITL escalation.
        log.warning("Supervisor exhausted %s iterations with %s errors", max_iter, len(errors))
        return {
            "errors": errors,
            "trip": trip,           # keep the flawed trip for human review
            "warnings": warnings,
            "hitl_required": True,
            "hitl_reason": (
                f"Automated planning could not satisfy all constraints after "
                f"{max_iter} attempts. Please review the following issues: "
                + "; ".join(errors[:3])
            ),
            "trace": trace,
        }

    # Success — trip is valid and within constraints.
    hitl_needed = False
    hitl_reason: str | None = None
    if validated is not None:
        approvable = [n for n in validated.nodes if n.requires_approval or n.financials.cost_usd >= _HIGH_VALUE_USD]
        if approvable:
            hitl_needed = True
            hitl_reason = (
                f"{len(approvable)} node(s) require your approval before booking "
                f"(flights + high-value items). Click 'Review & Approve' to continue."
            )

    log.info(
        "Supervisor accepted trip iter=%s total=$%.2f hitl=%s",
        iteration,
        validated.total_cost_usd() if validated else 0.0,
        hitl_needed,
    )
    return {
        "errors": [],
        "trip": trip,
        "warnings": warnings,
        "hitl_required": hitl_needed,
        "hitl_reason": hitl_reason,
        "trace": trace,
    }
