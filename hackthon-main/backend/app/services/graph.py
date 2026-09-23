"""Directed acyclic graph utilities for the itinerary dependency model
(F-25, F-26, F-31).

Nothing here touches the database — routers hand in ORM rows and receive
plain dataclasses / dicts back. Keeps the graph math testable and reusable
by the recovery service.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.graph import EdgeKind, ItineraryEdge, ItineraryNode


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


@dataclass
class DependencyGraph:
    """In-memory view of the itinerary DAG. Kept immutable — mutations go
    through the router which persists the change and rebuilds the graph."""

    nodes: dict[str, ItineraryNode]
    edges: list[ItineraryEdge]
    outgoing: dict[str, list[ItineraryEdge]] = field(default_factory=lambda: defaultdict(list))
    incoming: dict[str, list[ItineraryEdge]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def build(cls, nodes: list[ItineraryNode], edges: list[ItineraryEdge]) -> "DependencyGraph":
        by_id = {n.id: n for n in nodes}
        g = cls(nodes=by_id, edges=list(edges))
        for e in edges:
            g.outgoing[e.from_node_id].append(e)
            g.incoming[e.to_node_id].append(e)
        return g

    # --- validation ---------------------------------------------------------

    def would_create_cycle(self, from_id: str, to_id: str) -> bool:
        """True if adding from_id -> to_id would introduce a cycle. Used by
        the edge-create endpoint so we can 400 rather than persist a bad
        edge."""
        if from_id == to_id:
            return True
        # If `to_id` can already reach `from_id`, adding the reverse closes a loop.
        stack = [to_id]
        seen: set[str] = set()
        while stack:
            cur = stack.pop()
            if cur == from_id:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            for e in self.outgoing.get(cur, []):
                stack.append(e.to_node_id)
        return False

    # --- F-26 ripple traversal ---------------------------------------------

    def downstream(self, node_ids: list[str]) -> list[str]:
        """BFS from every root in `node_ids`. Returns downstream nodes only
        (roots excluded), in traversal order. Idempotent across duplicate
        roots — the F-31 multi-root case reduces to a single pass rather
        than N passes with de-dup."""
        seen: set[str] = set(node_ids)
        order: list[str] = []
        queue: deque[str] = deque(node_ids)
        while queue:
            cur = queue.popleft()
            for e in self.outgoing.get(cur, []):
                nxt = e.to_node_id
                if nxt in seen:
                    continue
                seen.add(nxt)
                order.append(nxt)
                queue.append(nxt)
        return order

    def upstream_predecessors(self, node_id: str) -> list[str]:
        preds: list[str] = []
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            cur = stack.pop()
            for e in self.incoming.get(cur, []):
                if e.from_node_id in seen:
                    continue
                seen.add(e.from_node_id)
                preds.append(e.from_node_id)
                stack.append(e.from_node_id)
        return preds

    # --- topological helpers -----------------------------------------------

    def topological_order(self) -> list[str]:
        """Kahn's algorithm — falls back to insertion order if the graph is
        empty. Assumes `would_create_cycle` has been enforced on writes so
        we never receive a cyclic graph here."""
        indeg = {nid: 0 for nid in self.nodes}
        for e in self.edges:
            if e.to_node_id in indeg:
                indeg[e.to_node_id] += 1
        queue = deque([n for n, d in indeg.items() if d == 0])
        order: list[str] = []
        while queue:
            n = queue.popleft()
            order.append(n)
            for e in self.outgoing.get(n, []):
                indeg[e.to_node_id] -= 1
                if indeg[e.to_node_id] == 0:
                    queue.append(e.to_node_id)
        return order

    # --- convenience for schedule-shifting ---------------------------------

    def critical_downstream_end(self, root_id: str, extra_delay_mins: int) -> datetime | None:
        """Return the latest end-time in the downstream subtree after
        propagating `extra_delay_mins` from `root_id`. Used by the recovery
        scorer to estimate a plan's time delta without materialising every
        shifted timing."""
        root = self.nodes.get(root_id)
        if root is None:
            return None
        latest = _as_utc(root.end_at)
        seen = {root_id}
        stack = [(root_id, extra_delay_mins)]
        while stack:
            cur, delay = stack.pop()
            for e in self.outgoing.get(cur, []):
                nxt = self.nodes.get(e.to_node_id)
                if nxt is None or e.to_node_id in seen:
                    continue
                seen.add(e.to_node_id)
                # SEQUENCED / REQUIRES: propagate. OPTIONAL: don't push delay.
                pushed = 0 if e.edge_kind == EdgeKind.OPTIONAL else delay
                nxt_end = _as_utc(nxt.end_at)
                if latest is None or (nxt_end is not None and nxt_end > latest):
                    latest = nxt_end
                stack.append((e.to_node_id, pushed))
        return latest
