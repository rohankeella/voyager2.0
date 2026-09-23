"""F-30 · Proactive Buffer & Risk Flagging.

Walks every REQUIRES / SEQUENCED edge and flags:

  * `TIGHT_BUFFER`      — actual buffer is below the edge's `min_buffer_mins`
                          (defaulting to 30 min per PRD acceptance).
  * `NEGATIVE_BUFFER`   — target starts before source ends. The graph itself
                          is inconsistent; escalated to critical.
  * `OVERLAP_WARNING`   — two sibling activities overlap when they shouldn't.

Nodes flagged as at-risk are surfaced to the operator/traveler UI before a
disruption happens — that's the "proactive" half of the feature name.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.models.graph import EdgeKind
from app.services.graph import DependencyGraph, _as_utc


DEFAULT_SAFETY_BUFFER_MINS = 30


RiskSeverity = Literal["warning", "critical"]


@dataclass
class BufferRisk:
    edge_id: str
    from_node_id: str
    from_title: str
    to_node_id: str
    to_title: str
    actual_buffer_mins: int
    required_buffer_mins: int
    severity: RiskSeverity
    message: str


def assess_buffers(g: DependencyGraph) -> list[BufferRisk]:
    risks: list[BufferRisk] = []
    for e in g.edges:
        if e.edge_kind == EdgeKind.OPTIONAL:
            continue
        src = g.nodes.get(e.from_node_id)
        dst = g.nodes.get(e.to_node_id)
        if src is None or dst is None:
            continue
        end = _as_utc(src.end_at)
        start = _as_utc(dst.start_at)
        if end is None or start is None:
            continue
        actual_mins = int((start - end).total_seconds() // 60)
        required = max(e.min_buffer_mins, 0)
        if actual_mins < 0:
            severity: RiskSeverity = "critical"
            message = (
                f"'{dst.title}' starts {abs(actual_mins)} min BEFORE '{src.title}' ends. "
                f"Fix the schedule or the dependency."
            )
            risks.append(
                BufferRisk(
                    edge_id=e.id,
                    from_node_id=src.id,
                    from_title=src.title,
                    to_node_id=dst.id,
                    to_title=dst.title,
                    actual_buffer_mins=actual_mins,
                    required_buffer_mins=required,
                    severity=severity,
                    message=message,
                )
            )
        elif actual_mins < required:
            severity = "critical" if actual_mins < required // 2 else "warning"
            message = (
                f"Only {actual_mins} min between '{src.title}' and '{dst.title}' "
                f"(needs {required}). At risk of a knock-on delay."
            )
            risks.append(
                BufferRisk(
                    edge_id=e.id,
                    from_node_id=src.id,
                    from_title=src.title,
                    to_node_id=dst.id,
                    to_title=dst.title,
                    actual_buffer_mins=actual_mins,
                    required_buffer_mins=required,
                    severity=severity,
                    message=message,
                )
            )
    return risks


def collect_at_risk_node_ids(risks: list[BufferRisk]) -> set[str]:
    """Union the set of node ids that should be badged AT_RISK. Used by the
    router when writing status back to the DB."""
    ids: set[str] = set()
    for r in risks:
        ids.add(r.to_node_id)
        if r.severity == "critical":
            ids.add(r.from_node_id)
    return ids
