"""DTO-P3 Phase 4 — Operator Command Center endpoint.

Aggregates:
  • Active SuperTrips with per-node traffic-light status (Gantt data)
  • Vendor status matrix (grouped by vendor_account, counts pending/routed)
  • Disruption queue (Phase 5 populates; Phase 4 returns [])

Auth: requires OPERATOR or ADMIN role (`require_operator`).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_operator
from app.models.disruption import SuperDisruption, SuperDisruptionStatus
from app.models.super_trip import SuperTripRecord, SuperTripStatus
from app.models.user import User
from app.services.node_status import classify_node

router = APIRouter(prefix="/api/operator", tags=["operator"])


# Trips in these states appear on the Gantt (draft is excluded).
_ACTIVE_STATUSES = {
    SuperTripStatus.PENDING_REVIEW,
    SuperTripStatus.APPROVED,
    SuperTripStatus.ACTIVE,
}


@router.get("/command-center")
def command_center(
    db: Session = Depends(get_db),
    _user: User = Depends(require_operator),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    rows = (
        db.query(SuperTripRecord)
        .filter(SuperTripRecord.status.in_(list(_ACTIVE_STATUSES)))
        .order_by(SuperTripRecord.created_at.desc())
        .all()
    )

    active_trips: list[dict[str, Any]] = []
    vendor_agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "vendor_account": "",
            "node_count": 0,
            "total_usd": 0.0,
            "routed_usd": 0.0,
            "types": defaultdict(int),
            "payment_status": defaultdict(int),
        }
    )

    total_lights = {"green": 0, "yellow": 0, "red": 0, "grey": 0}

    for row in rows:
        trip = dict(row.payload_json or {})
        nodes = trip.get("nodes") or []

        annotated_nodes: list[dict[str, Any]] = []
        trip_lights = {"green": 0, "yellow": 0, "red": 0, "grey": 0}

        for node in nodes:
            info = classify_node(node, nodes, now=now)
            light = info["light"]
            trip_lights[light] = trip_lights.get(light, 0) + 1
            total_lights[light] = total_lights.get(light, 0) + 1

            fin = node.get("financials") or {}
            vendor = fin.get("vendor_account") or "unassigned"
            cost = float(fin.get("cost_usd") or 0)
            pay = str(fin.get("payment_status") or "unpaid")

            agg = vendor_agg[vendor]
            agg["vendor_account"] = vendor
            agg["node_count"] += 1
            agg["total_usd"] += cost
            if pay == "routed":
                agg["routed_usd"] += cost
            agg["types"][str(node.get("type"))] += 1
            agg["payment_status"][pay] += 1

            ed = node.get("execution_data") or {}
            annotated_nodes.append(
                {
                    "node_id": node.get("node_id"),
                    "type": node.get("type"),
                    "title": node.get("title") or node.get("type"),
                    "status": node.get("status"),
                    "start_time": ed.get("start_time"),
                    "end_time": ed.get("end_time"),
                    "location_label": ed.get("location_label"),
                    "cost_usd": cost,
                    "vendor_account": vendor,
                    "payment_status": pay,
                    "status_light": light,
                    "status_reason": info["reason"],
                    "buffer_mins": info.get("buffer_mins"),
                    "depends_on": node.get("depends_on") or [],
                }
            )

        gc = trip.get("global_constraints") or {}
        active_trips.append(
            {
                "super_trip_id": row.id,
                "traveler_id": row.traveler_id,
                "title": row.title,
                "status": row.status.value,
                "total_cost_usd": row.total_cost_usd,
                "max_budget_usd": row.max_budget_usd,
                "node_count": row.node_count,
                "created_at": row.created_at.isoformat(),
                "approved_at": row.approved_at.isoformat() if row.approved_at else None,
                "start_date": gc.get("start_date"),
                "end_date": gc.get("end_date"),
                "home_location": gc.get("home_location"),
                "lights": trip_lights,
                "nodes": annotated_nodes,
            }
        )

    # Normalize vendor aggregates for JSON.
    vendors_out: list[dict[str, Any]] = []
    for v in vendor_agg.values():
        vendors_out.append(
            {
                "vendor_account": v["vendor_account"],
                "node_count": v["node_count"],
                "total_usd": round(v["total_usd"], 2),
                "routed_usd": round(v["routed_usd"], 2),
                "settled_ratio": round(v["routed_usd"] / v["total_usd"], 3) if v["total_usd"] > 0 else 0.0,
                "types": dict(v["types"]),
                "payment_status": dict(v["payment_status"]),
            }
        )
    vendors_out.sort(key=lambda v: v["total_usd"], reverse=True)

    # ---- Phase 5: open disruption queue -------------------------------
    open_rows = (
        db.query(SuperDisruption)
        .filter(SuperDisruption.status == SuperDisruptionStatus.OPEN)
        .order_by(SuperDisruption.created_at.desc())
        .all()
    )
    disruption_queue: list[dict[str, Any]] = []
    trip_titles = {t["super_trip_id"]: t["title"] for t in active_trips}
    for r in open_rows:
        disruption_queue.append(
            {
                "id": r.id,
                "super_trip_id": r.super_trip_id,
                "trip_title": trip_titles.get(r.super_trip_id, r.super_trip_id),
                "node_id": r.node_id,
                "kind": r.kind.value,
                "delta_mins": r.delta_mins,
                "note": r.note,
                "source": r.source,
                "created_at": r.created_at.isoformat(),
                "plans": r.plans_json or [],
            }
        )

    return {
        "generated_at": now.isoformat(),
        "active_trip_count": len(active_trips),
        "lights_summary": total_lights,
        "active_trips": active_trips,
        "vendor_matrix": vendors_out,
        "disruption_queue": disruption_queue,
    }
