"""F-29 · Interactive Graph Rewriting ("Apply Fix").

Given a persisted `RecoveryPlan` and the live graph, walk `plan.actions`
and mutate the ORM in place:

  * SHIFT        — shifts start_at + end_at by delta_mins.
  * MODIFY       — same shift, plus mark node REPLACED so the frontend
                   shows it as vendor-touched. Also increments cost.
  * CANCEL       — remove all outgoing edges from the node, then delete
                   the node itself.
  * REBOOK       — same as MODIFY (kept as a distinct action label for
                   clarity in the plan; behaviour matches).
  * DROP_OPTIONAL— remove the node and every edge touching it.

After all actions run:
  * Reset any node still marked DISRUPTED / IMPACTED back to SCHEDULED
    (the topology has been repaired).
  * Return an `ApplyReport` summarising what changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.graph import (
    Disruption,
    ItineraryEdge,
    ItineraryNode,
    NodeStatus,
    RecoveryPlan,
)
from app.services.graph import _as_utc


@dataclass
class ApplyReport:
    plan_id: str
    label: str
    strategy: str
    nodes_shifted: int
    nodes_modified: int
    nodes_cancelled: int
    nodes_dropped: int
    edges_removed: int
    residual_conflicts: list[str]


def _shift_node(node: ItineraryNode, delta_mins: int) -> None:
    if delta_mins == 0:
        return
    start = _as_utc(node.start_at) or node.start_at
    end = _as_utc(node.end_at) or node.end_at
    node.start_at = start + timedelta(minutes=delta_mins)
    node.end_at = end + timedelta(minutes=delta_mins)


def apply_plan(
    db: Session,
    plan: RecoveryPlan,
    nodes_by_id: dict[str, ItineraryNode],
    edges: list[ItineraryEdge],
    disruptions: list[Disruption],
) -> ApplyReport:
    report = ApplyReport(
        plan_id=plan.id,
        label=plan.label,
        strategy=plan.strategy,
        nodes_shifted=0,
        nodes_modified=0,
        nodes_cancelled=0,
        nodes_dropped=0,
        edges_removed=0,
        residual_conflicts=[],
    )

    to_delete_node_ids: set[str] = set()
    for raw in plan.actions or []:
        node_id = raw.get("node_id")
        kind = raw.get("kind")
        delta = int(raw.get("delta_mins", 0))
        node = nodes_by_id.get(node_id)
        if node is None:
            report.residual_conflicts.append(f"action targets missing node {node_id}")
            continue

        if kind == "SHIFT":
            _shift_node(node, delta)
            report.nodes_shifted += 1
        elif kind in ("MODIFY", "REBOOK"):
            _shift_node(node, delta)
            node.status = NodeStatus.REPLACED
            node.cost = float(node.cost) + float(raw.get("monetary_penalty", 0.0))
            report.nodes_modified += 1
        elif kind == "CANCEL":
            to_delete_node_ids.add(node_id)
            report.nodes_cancelled += 1
        elif kind == "DROP_OPTIONAL":
            to_delete_node_ids.add(node_id)
            report.nodes_dropped += 1
        else:
            report.residual_conflicts.append(f"unknown action kind '{kind}' on {node_id}")

    # Drop edges touching removed nodes.
    if to_delete_node_ids:
        for e in list(edges):
            if e.from_node_id in to_delete_node_ids or e.to_node_id in to_delete_node_ids:
                db.delete(e)
                report.edges_removed += 1
        for nid in to_delete_node_ids:
            n = nodes_by_id.get(nid)
            if n is not None:
                db.delete(n)

    # Resolve disruptions + reset any lingering statuses.
    for d in disruptions:
        d.is_resolved = True

    for n in nodes_by_id.values():
        if n.id in to_delete_node_ids:
            continue
        if n.status in (NodeStatus.DISRUPTED, NodeStatus.IMPACTED, NodeStatus.AT_RISK):
            n.status = NodeStatus.SCHEDULED

    plan.is_applied = True
    plan.applied_at = datetime.now(timezone.utc)
    return report
