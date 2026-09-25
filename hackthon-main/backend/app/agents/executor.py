"""Executor Agent — converts Planner draft into a fully-realised SuperTrip.

For each Planner node, the Executor:
  1. Picks the right tool based on `type`
  2. Calls the tool (async, in an event loop) to get real (or mocked) travel data
  3. Fills execution_data (start_time, end_time, coordinates, PNR, etc.)
  4. Fills financials.cost_usd from the tool's real price

The Executor does NOT talk to the LLM — it's deterministic, tool-driven code.
This keeps costs low and gives the Supervisor a predictable output shape.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, time, timedelta, timezone
from typing import Any

from app.agents.state import AgentState
from app.agents.tools import (
    estimate_activity,
    estimate_ground_transfer,
    resolve_location,
    search_flight,
    search_hotel,
)
from app.schemas.super_trip import (
    NodeExecutionData,
    NodeFinancials,
    NodeStatus,
    NodeType,
    PaymentStatus,
    TripNode,
    TripStatus,
    make_node_id,
    make_super_trip_id,
)

log = logging.getLogger("agents.executor")


# ---- helpers --------------------------------------------------------------


def _iso_date_to_dt(date_str: str, hour: int = 0) -> datetime:
    d = datetime.fromisoformat(date_str)
    return d.replace(hour=hour, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def _day_offset(start_date: str, day: int, hour: int) -> datetime:
    """Day 1 = start_date. Day 2 = start_date + 1. ..."""
    base = _iso_date_to_dt(start_date)
    return base + timedelta(days=max(0, day - 1), hours=max(0, hour))


def _normalize_type(raw: str) -> NodeType:
    raw = (raw or "").lower().replace("-", "_")
    aliases = {
        "flight": NodeType.AMADEUS_FLIGHT_ORDER,
        "flights": NodeType.AMADEUS_FLIGHT_ORDER,
        "amadeus_flight": NodeType.AMADEUS_FLIGHT_ORDER,
        "hotel": NodeType.AMADEUS_HOTEL_BOOKING,
        "amadeus_hotel": NodeType.AMADEUS_HOTEL_BOOKING,
        "transfer": NodeType.OTP_GROUND_TRANSFER,
        "ground_transfer": NodeType.OTP_GROUND_TRANSFER,
        "otp": NodeType.OTP_GROUND_TRANSFER,
    }
    if raw in aliases:
        return aliases[raw]
    try:
        return NodeType(raw)
    except ValueError:
        return NodeType.CUSTOM


def _fake_pnr() -> str:
    return secrets.token_hex(4).upper()


# ---- per-node executors ---------------------------------------------------


async def _exec_flight(planner_node: dict, planner_draft: dict, day_start: datetime) -> tuple[NodeExecutionData, NodeFinancials, str | None]:
    origin = planner_node.get("origin_city") or planner_draft.get("home_location") or ""
    destination = planner_node.get("destination_city") or ""
    if not origin or not destination:
        return (
            NodeExecutionData(start_time=day_start, end_time=day_start + timedelta(hours=2)),
            NodeFinancials(cost_usd=planner_node.get("estimated_cost_usd") or 500.0),
            f"Missing origin/destination for flight: {origin}->{destination}",
        )

    depart_date = day_start.date().isoformat()
    offer = await search_flight(origin, destination, depart_date)
    if not offer:
        return (
            NodeExecutionData(
                start_time=day_start,
                end_time=day_start + timedelta(hours=3),
                location_label=f"{origin} → {destination}",
            ),
            NodeFinancials(cost_usd=planner_node.get("estimated_cost_usd") or 500.0),
            f"No flight offers for {origin}->{destination}",
        )

    dep_at = _parse_iso(offer["departure_at"]) or day_start
    arr_at = _parse_iso(offer["arrival_at"]) or dep_at + timedelta(hours=3)

    # Show the arrival airport as the primary marker location so the globe
    # places the flight node at its destination, while the arc uses both endpoints.
    exec_data = NodeExecutionData(
        start_time=dep_at,
        end_time=arr_at,
        location_label=f"{offer['origin_iata']} → {offer['destination_iata']}",
        lat=offer.get("destination_lat"),
        lng=offer.get("destination_lng"),
        pnr_number=_fake_pnr(),
    )
    # Attach extra data via extra="allow"
    exec_data_dict = exec_data.model_dump()
    exec_data_dict.update(
        {
            "carrier_code": offer.get("carrier_code"),
            "flight_number": offer.get("flight_number"),
            "stops": offer.get("stops", 0),
            "origin_iata": offer["origin_iata"],
            "destination_iata": offer["destination_iata"],
            "origin_lat": offer.get("origin_lat"),
            "origin_lng": offer.get("origin_lng"),
            "destination_lat": offer.get("destination_lat"),
            "destination_lng": offer.get("destination_lng"),
        }
    )
    exec_data = NodeExecutionData(**exec_data_dict)

    financials = NodeFinancials(
        cost_usd=offer["cost_usd"],
        payment_status=PaymentStatus.UNPAID,
        vendor_account=f"acc_airline_{offer.get('carrier_code','XX')}",
    )
    return exec_data, financials, None


async def _exec_hotel(planner_node: dict, planner_draft: dict, day_start: datetime) -> tuple[NodeExecutionData, NodeFinancials, str | None]:
    city = planner_node.get("location_city") or planner_node.get("destination_city") or ""
    if not city:
        return (
            NodeExecutionData(start_time=day_start, end_time=day_start + timedelta(days=1)),
            NodeFinancials(cost_usd=planner_node.get("estimated_cost_usd") or 100.0),
            "Missing city for hotel",
        )

    # Default 1-night — Executor will merge multi-night stays later
    duration_hours = max(1.0, planner_node.get("duration_hours") or 20.0)
    check_in = day_start.date().isoformat()
    check_out = (day_start + timedelta(hours=duration_hours)).date().isoformat()
    if check_out == check_in:
        check_out = (day_start + timedelta(days=1)).date().isoformat()

    offer = await search_hotel(city, check_in, check_out)
    if not offer:
        return (
            NodeExecutionData(
                start_time=day_start,
                end_time=day_start + timedelta(hours=duration_hours),
                location_label=planner_node.get("location_label") or city,
            ),
            NodeFinancials(cost_usd=planner_node.get("estimated_cost_usd") or 120.0),
            f"No hotel offers for {city}",
        )

    exec_data = NodeExecutionData(
        start_time=day_start,
        end_time=day_start + timedelta(hours=duration_hours),
        location_label=offer.get("hotel_name") or planner_node.get("location_label") or city,
        lat=offer.get("lat"),
        lng=offer.get("lng"),
    )
    exec_data_dict = exec_data.model_dump()
    exec_data_dict.update(
        {
            "hotel_id": offer.get("hotel_id"),
            "room_description": offer.get("room_description"),
            "check_in": offer.get("check_in"),
            "check_out": offer.get("check_out"),
        }
    )
    exec_data = NodeExecutionData(**exec_data_dict)

    financials = NodeFinancials(
        cost_usd=offer["cost_usd"],
        payment_status=PaymentStatus.UNPAID,
        vendor_account=f"acc_hotel_{offer.get('hotel_id','X')[:6]}",
    )
    return exec_data, financials, None


async def _exec_transfer(planner_node: dict, planner_draft: dict, day_start: datetime) -> tuple[NodeExecutionData, NodeFinancials, str | None]:
    origin_city = planner_node.get("origin_city") or ""
    dest_city = planner_node.get("destination_city") or ""

    from_loc = await resolve_location(origin_city) if origin_city else None
    to_loc = await resolve_location(dest_city) if dest_city else None

    transfer = await estimate_ground_transfer(
        (from_loc or {}).get("lat"),
        (from_loc or {}).get("lng"),
        (to_loc or {}).get("lat"),
        (to_loc or {}).get("lng"),
        depart_at=day_start,
    )
    start = _parse_iso(transfer["start_time"]) or day_start
    end = _parse_iso(transfer["end_time"]) or start + timedelta(hours=1)

    exec_data = NodeExecutionData(
        start_time=start,
        end_time=end,
        location_label=f"{origin_city} → {dest_city}",
        lat=(to_loc or {}).get("lat"),
        lng=(to_loc or {}).get("lng"),
        route_geometry=transfer.get("route_geometry"),
    )
    # Attach both endpoints for the globe polyline + OTP metadata when present.
    exec_data_dict = exec_data.model_dump()
    exec_data_dict.update(
        {
            "origin_lat": (from_loc or {}).get("lat"),
            "origin_lng": (from_loc or {}).get("lng"),
            "destination_lat": (to_loc or {}).get("lat"),
            "destination_lng": (to_loc or {}).get("lng"),
            "transit_source": transfer.get("source"),
            "gtfs_id": transfer.get("gtfs_id"),
            "route_name": transfer.get("route_name"),
            "transit_modes": transfer.get("modes"),
            "stoptimes": transfer.get("stoptimes"),
        }
    )
    exec_data = NodeExecutionData(**exec_data_dict)
    financials = NodeFinancials(
        cost_usd=transfer["cost_usd"],
        payment_status=PaymentStatus.UNPAID,
        vendor_account="acc_ground_transit",
    )
    return exec_data, financials, None


def _exec_activity_like(
    planner_node: dict, planner_draft: dict, day_start: datetime
) -> tuple[NodeExecutionData, NodeFinancials, str | None]:
    """Activities, meals, guide sessions, custom — same shape, different price hints."""
    duration_hours = planner_node.get("duration_hours") or 2.0
    cost = planner_node.get("estimated_cost_usd") or 25.0
    label = planner_node.get("location_label") or planner_node.get("location_city") or planner_node.get("title")

    end = day_start + timedelta(hours=duration_hours)
    exec_data = NodeExecutionData(
        start_time=day_start,
        end_time=end,
        location_label=label,
    )
    financials = NodeFinancials(
        cost_usd=round(float(cost), 2),
        payment_status=PaymentStatus.UNPAID,
    )
    return exec_data, financials, None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Accept "2027-05-10T14:30:00Z" and "2027-05-10T14:30:00+00:00"
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


# ---- LangGraph node -------------------------------------------------------


def execute_node(state: AgentState) -> dict[str, Any]:
    """Convert Planner draft → final SuperTrip dict."""
    draft = state.get("draft_trip")
    if not draft:
        return {"errors": ["Executor: no draft_trip in state"]}

    traveler_id = state.get("traveler_id") or "USR-anon"
    if not traveler_id.startswith("USR-"):
        traveler_id = f"USR-{traveler_id}"

    warnings: list[str] = []
    planner_nodes = draft.get("nodes") or []
    start_date = draft.get("start_date")
    if not start_date:
        return {"errors": ["Executor: draft.start_date missing"]}

    # Build final trip nodes sequentially so downstream nodes can peek at
    # earlier ones' coordinates (used by ground_transfer, hotel proximity).
    final_nodes: list[TripNode] = []
    index_to_node_id: dict[int, str] = {}
    kind_counters: dict[NodeType, int] = {}

    async def process_all() -> None:
        for idx, pnode in enumerate(planner_nodes):
            node_type = _normalize_type(pnode.get("type", ""))
            kind_counters[node_type] = kind_counters.get(node_type, 0) + 1
            node_index = len(final_nodes) + 1
            node_id = make_node_id(node_index, node_type)

            day_start = _day_offset(
                start_date, pnode.get("start_day", 1), pnode.get("start_hour", 10)
            )

            try:
                if node_type == NodeType.AMADEUS_FLIGHT_ORDER:
                    exec_data, fin, warn = await _exec_flight(pnode, draft, day_start)
                elif node_type == NodeType.AMADEUS_HOTEL_BOOKING:
                    exec_data, fin, warn = await _exec_hotel(pnode, draft, day_start)
                elif node_type == NodeType.OTP_GROUND_TRANSFER:
                    exec_data, fin, warn = await _exec_transfer(pnode, draft, day_start)
                else:
                    exec_data, fin, warn = _exec_activity_like(pnode, draft, day_start)
            except Exception as e:
                log.exception("Executor failed on planner index %s", idx)
                warnings.append(f"Node {idx} ({node_type.value}) failed: {e}")
                exec_data = NodeExecutionData(
                    start_time=day_start,
                    end_time=day_start + timedelta(hours=1),
                )
                fin = NodeFinancials(cost_usd=pnode.get("estimated_cost_usd") or 0.0)

            if warn:
                warnings.append(warn)

            depends_on = [
                index_to_node_id[i]
                for i in (pnode.get("depends_on_indices") or [])
                if i in index_to_node_id
            ]

            node = TripNode(
                node_id=node_id,
                type=node_type,
                status=NodeStatus.PENDING,
                execution_data=exec_data,
                depends_on=depends_on,
                financials=fin,
                title=pnode.get("title"),
                description=pnode.get("description"),
                requires_approval=fin.cost_usd >= 500.0,
            )
            final_nodes.append(node)
            index_to_node_id[idx] = node_id

    # Run all the awaits.
    try:
        asyncio.run(process_all())
    except RuntimeError:
        # An event loop is already running (unlikely inside FastAPI request
        # handlers because we run this in threadpool — but guard anyway).
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(process_all())
        finally:
            loop.close()

    # ---- temporal sweep -----------------------------------------------
    # After the raw pass, shift each node's start_time forward to respect
    # its dependencies. Hard deps (flights, transfers, activities, meals)
    # must FULLY complete first; hotel deps are containers (target can start
    # during the hotel window). This resolves the common case where the
    # Planner-hinted departure time predates the actual flight arrival.
    from datetime import timedelta as _td  # local alias — module already imports it

    _HARD_END = {
        NodeType.AMADEUS_FLIGHT_ORDER,
        NodeType.AMADEUS_FLIGHT_OFFER,
        NodeType.OTP_GROUND_TRANSFER,
        NodeType.ACTIVITY,
        NodeType.MEAL,
        NodeType.GUIDE_SESSION,
        NodeType.CUSTOM,
    }
    _CONTAINER = {NodeType.AMADEUS_HOTEL_BOOKING, NodeType.AMADEUS_HOTEL_OFFER}
    _BUFFER_MIN = 15

    by_id = {n.node_id: n for n in final_nodes}
    for n in final_nodes:
        if not n.depends_on:
            continue
        earliest_start: datetime | None = None
        for dep_id in n.depends_on:
            src = by_id.get(dep_id)
            if not src:
                continue
            src_start = src.execution_data.start_time
            src_end = src.execution_data.end_time
            if src.type in _CONTAINER and src_start:
                # target may begin any time inside the container
                candidate = src_start
            elif src_end:
                candidate = src_end + _td(minutes=_BUFFER_MIN)
            else:
                continue
            if earliest_start is None or candidate > earliest_start:
                earliest_start = candidate
        if earliest_start is None:
            continue
        cur_start = n.execution_data.start_time
        if cur_start is None or cur_start < earliest_start:
            duration = (
                (n.execution_data.end_time - cur_start)
                if (n.execution_data.end_time and cur_start)
                else _td(hours=2)
            )
            new_start = earliest_start
            new_end = new_start + duration
            merged = n.execution_data.model_dump()
            merged["start_time"] = new_start
            merged["end_time"] = new_end
            n.execution_data = NodeExecutionData(**merged)

    # Assemble SuperTrip dict — the Supervisor will validate it against the
    # strict schema and raise if the DAG has any issues.
    super_trip = {
        "super_trip_id": make_super_trip_id(draft.get("home_location") or "TRIP"),
        "traveler_id": traveler_id,
        "status": TripStatus.PENDING_REVIEW.value,
        "global_constraints": {
            "max_budget_usd": draft.get("max_budget_usd", 1000.0),
            "start_date": _iso_date_to_dt(draft["start_date"]).isoformat(),
            "end_date": _iso_date_to_dt(draft["end_date"], hour=22).isoformat(),
            "home_location": draft.get("home_location"),
            "traveler_count": draft.get("traveler_count", 1),
            "preferences": {"tags": draft.get("preferences") or []},
        },
        "nodes": [n.model_dump(mode="json") for n in final_nodes],
    }

    trace_entry = {
        "agent": "executor",
        "nodes_processed": len(final_nodes),
        "tool_calls": sum(
            1 for n in final_nodes if n.type in {NodeType.AMADEUS_FLIGHT_ORDER, NodeType.AMADEUS_HOTEL_BOOKING}
        ),
        "warnings_count": len(warnings),
    }

    return {
        "trip": super_trip,
        "warnings": (state.get("warnings") or []) + warnings,
        "trace": (state.get("trace") or []) + [trace_entry],
    }
