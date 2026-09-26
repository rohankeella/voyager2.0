"""Traffic-light classifier for SuperTrip nodes.

Per DTO-P3 PRD § "Global Fleet Tracking and Gantt Visualization":

  Green (Nominal):  on-schedule, no disruption, or already complete.
  Yellow (Warning): temporal drift detected — a delay has narrowed the buffer
                    but downstream deps still fit.
  Red (Critical):   the delay has invalidated at least one downstream node
                    (i.e. buffer is now negative on some edge), OR the node
                    itself has an explicit disruption in `execution_data`.

The classifier is deterministic and pure — no DB touches, no clock jitter
in tests (accepts an explicit `now` for reproducibility).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any


class StatusLight(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GREY = "grey"     # completed / cancelled — visually muted


# A buffer under 30 minutes to the next node ⇒ yellow warning.
_TIGHT_BUFFER_MIN = 30


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


def classify_node(
    node: dict[str, Any],
    trip_nodes: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return {'light': StatusLight, 'reason': str, 'buffer_mins': int|None}.

    `trip_nodes` is the full list of nodes on the same SuperTrip (needed to
    check downstream buffers). `node` is one of those.
    """
    now = now or datetime.now(timezone.utc)
    status = str(node.get("status") or "").lower()
    ed = node.get("execution_data") or {}
    start = _parse_iso(ed.get("start_time"))
    end = _parse_iso(ed.get("end_time"))

    # Terminal states are muted.
    if status in {"completed", "cancelled", "replaced"}:
        return {"light": StatusLight.GREY.value, "reason": status, "buffer_mins": None}

    # Explicit disruption on this node → red.
    if status == "disrupted":
        return {"light": StatusLight.RED.value, "reason": "node disrupted", "buffer_mins": None}

    # Node's chronology invalid vs its dependencies → red.
    by_id = {n.get("node_id"): n for n in trip_nodes}
    tightest_buffer: int | None = None
    for dep_id in node.get("depends_on") or []:
        src = by_id.get(dep_id)
        if not src:
            continue
        src_end = _parse_iso((src.get("execution_data") or {}).get("end_time"))
        if src_end and start:
            delta_mins = int((start - src_end).total_seconds() // 60)
            # For hotel container deps, being "inside" the hotel window is fine.
            src_type = str(src.get("type") or "")
            is_container = src_type.startswith("amadeus_hotel")
            if is_container:
                # Only violation is starting BEFORE hotel check-in.
                src_start = _parse_iso((src.get("execution_data") or {}).get("start_time"))
                if src_start and start < src_start:
                    return {
                        "light": StatusLight.RED.value,
                        "reason": f"starts before hotel {dep_id} check-in",
                        "buffer_mins": delta_mins,
                    }
                continue
            if delta_mins < 0:
                return {
                    "light": StatusLight.RED.value,
                    "reason": f"scheduling conflict with {dep_id} (buffer {delta_mins}m)",
                    "buffer_mins": delta_mins,
                }
            if tightest_buffer is None or delta_mins < tightest_buffer:
                tightest_buffer = delta_mins

    # If any hard dependency has a tight buffer, warn (yellow).
    if tightest_buffer is not None and tightest_buffer < _TIGHT_BUFFER_MIN:
        return {
            "light": StatusLight.YELLOW.value,
            "reason": f"tight buffer of {tightest_buffer}m from upstream",
            "buffer_mins": tightest_buffer,
        }

    # Nothing wrong. If node is completed relative to `now`, grey; else green.
    if end and end < now:
        return {"light": StatusLight.GREY.value, "reason": "completed", "buffer_mins": tightest_buffer}
    return {"light": StatusLight.GREEN.value, "reason": "nominal", "buffer_mins": tightest_buffer}


def summarise_trip(trip_nodes: list[dict[str, Any]], *, now: datetime | None = None) -> dict[str, int]:
    """Count each StatusLight across `trip_nodes`."""
    counts = {light.value: 0 for light in StatusLight}
    for n in trip_nodes:
        info = classify_node(n, trip_nodes, now=now)
        counts[info["light"]] = counts.get(info["light"], 0) + 1
    return counts
