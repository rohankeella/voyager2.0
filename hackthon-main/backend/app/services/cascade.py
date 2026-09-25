"""DTO-P3 Phase 5 — Cascade Protocol.

Given a SuperTrip DAG and a disruption event, this module computes:

  1. Which node the disruption hit (target node).
  2. The BLAST RADIUS — descendants that (transitively) depend on the target.
  3. New projected start/end times after propagating the delay through those
     descendants (topological pass, respects hotel-container semantics).
  4. CONFLICTS — descendants whose new start pushes past next-day boundaries,
     hotel checkout, or other hard temporal bounds. These are red-alerted.

The output feeds the recovery generator (`services/recovery_super_trip.py`),
which turns conflicts into 3 candidate strategies.

Pure functions — no DB, no side effects. Same trip dict in → same result out.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any


# Buffer minimums that trigger "at risk" (yellow) vs "conflict" (red).
_YELLOW_BUFFER_MIN = 30


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


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _shift_node(node: dict, delta: timedelta) -> None:
    ed = node.setdefault("execution_data", {})
    for k in ("start_time", "end_time"):
        cur = _parse_iso(ed.get(k))
        if cur is not None:
            ed[k] = _iso(cur + delta)


def _descendants_topological(trip: dict, source_node_id: str) -> list[str]:
    """Return descendants of `source_node_id` in topological order.

    Kahn's algorithm restricted to the source's forward cone.
    """
    nodes = trip.get("nodes") or []
    ids = [n.get("node_id") for n in nodes]
    incoming: dict[str, set[str]] = {nid: set() for nid in ids if nid}
    outgoing: dict[str, set[str]] = {nid: set() for nid in ids if nid}
    for n in nodes:
        nid = n.get("node_id")
        for dep in n.get("depends_on") or []:
            if dep in incoming and nid in incoming:
                incoming[nid].add(dep)
                outgoing[dep].add(nid)

    # BFS forward-cone descendants
    forward: set[str] = set()
    stack = [source_node_id]
    while stack:
        u = stack.pop()
        for v in outgoing.get(u, ()):
            if v not in forward:
                forward.add(v)
                stack.append(v)

    # Topological ordering restricted to `forward`. We only count edges from
    # other nodes IN `forward` — dependencies on the source itself or on
    # nodes outside the blast radius are treated as already satisfied.
    indeg = {nid: sum(1 for p in incoming[nid] if p in forward) for nid in forward}
    queue = [nid for nid, d in indeg.items() if d == 0]
    ordered: list[str] = []
    while queue:
        u = queue.pop(0)
        ordered.append(u)
        for v in outgoing[u]:
            if v not in forward:
                continue
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return ordered


def _hard_dep_end(node: dict, by_id: dict[str, dict]) -> datetime | None:
    """Latest `end_time` among this node's *hard* dependencies (non-hotel)."""
    latest: datetime | None = None
    for dep_id in node.get("depends_on") or []:
        src = by_id.get(dep_id)
        if not src:
            continue
        src_type = str(src.get("type") or "")
        if src_type.startswith("amadeus_hotel"):
            continue  # container dep — activities may run during hotel window
        end = _parse_iso((src.get("execution_data") or {}).get("end_time"))
        if end is None:
            continue
        if latest is None or end > latest:
            latest = end
    return latest


def apply_delay(trip: dict, node_id: str, delta_mins: int) -> dict[str, Any]:
    """Propagate a delay of `delta_mins` through descendants and return a
    report suitable for downstream planning.

    Returns:
      {
        "delta_mins": int,
        "affected_node_ids": [ids in topological order],
        "broken_chronology": [
          {node_id, dep_id, old_buffer_mins, new_buffer_mins}
        ],
        "hotel_late_check_ins": [{node_id, hotel_id, minutes_late}],
        "trip_after": <deep copy of trip with shifted timestamps>,
      }
    """
    trip_after = copy.deepcopy(trip)
    nodes = trip_after.get("nodes") or []
    by_id = {n.get("node_id"): n for n in nodes}
    delta = timedelta(minutes=delta_mins)

    target = by_id.get(node_id)
    if not target:
        return {"delta_mins": delta_mins, "affected_node_ids": [], "broken_chronology": [], "hotel_late_check_ins": [], "trip_after": trip_after}

    # 1. Shift the target itself
    _shift_node(target, delta)
    target["status"] = "disrupted"

    # 2. Propagate to descendants in topo order — each shifts by delta.
    affected = _descendants_topological(trip_after, node_id)
    for nid in affected:
        n = by_id.get(nid)
        if not n:
            continue
        _shift_node(n, delta)
        if str(n.get("status") or "") not in {"cancelled", "completed"}:
            n["status"] = "at_risk"

    # 3. Detect broken chronology and hotel late check-ins.
    broken: list[dict[str, Any]] = []
    late_check_ins: list[dict[str, Any]] = []

    for nid in affected + [node_id]:
        n = by_id.get(nid)
        if not n:
            continue
        n_start = _parse_iso((n.get("execution_data") or {}).get("start_time"))
        n_type = str(n.get("type") or "")
        if not n_start:
            continue

        # Hotel late check-in tracking (informational)
        if n_type.startswith("amadeus_hotel"):
            # A hotel that now starts LATER than its original planned time
            # (say, past midnight local) — flag as late check-in.
            # We don't have the original ISO in trip_after, but the delay is exactly `delta_mins`.
            if delta_mins > 60:
                late_check_ins.append(
                    {"node_id": nid, "hotel_id": (n.get("execution_data") or {}).get("hotel_id"), "minutes_late": delta_mins}
                )

        # Chronology check against hard deps
        latest_end = _hard_dep_end(n, by_id)
        if latest_end is None:
            continue
        buf = int((n_start - latest_end).total_seconds() // 60)
        if buf < 0:
            broken.append(
                {
                    "node_id": nid,
                    "reason": "target starts before hard dep completes",
                    "new_buffer_mins": buf,
                }
            )

    return {
        "delta_mins": delta_mins,
        "affected_node_ids": affected,
        "broken_chronology": broken,
        "hotel_late_check_ins": late_check_ins,
        "trip_after": trip_after,
    }


def apply_cancellation(trip: dict, node_id: str) -> dict[str, Any]:
    """Mark a node as cancelled. Descendants that HARD depend on it are
    orphaned and flagged. Container (hotel) dependents just detach.

    Returns similar report shape to `apply_delay`.
    """
    trip_after = copy.deepcopy(trip)
    nodes = trip_after.get("nodes") or []
    by_id = {n.get("node_id"): n for n in nodes}

    target = by_id.get(node_id)
    if not target:
        return {
            "delta_mins": 0,
            "affected_node_ids": [],
            "broken_chronology": [],
            "hotel_late_check_ins": [],
            "orphaned_node_ids": [],
            "trip_after": trip_after,
        }
    target["status"] = "cancelled"

    affected = _descendants_topological(trip_after, node_id)
    orphaned: list[str] = []
    for nid in affected:
        n = by_id.get(nid)
        if not n:
            continue
        # If cancelled node is a hard dep, this node is orphaned.
        for dep_id in n.get("depends_on") or []:
            if dep_id == node_id:
                src_type = str(target.get("type") or "")
                if not src_type.startswith("amadeus_hotel"):
                    n["status"] = "at_risk"
                    orphaned.append(nid)
                    break

    return {
        "delta_mins": 0,
        "affected_node_ids": affected,
        "broken_chronology": [],
        "hotel_late_check_ins": [],
        "orphaned_node_ids": orphaned,
        "trip_after": trip_after,
    }
