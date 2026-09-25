"""DTO-P3 Phase 6 — Razorpay Route split-payment mock.

Deterministic Python-side simulation of what Razorpay Route actually does in
production. Same JSON shape as the real API so a future swap to live keys
only touches this module. The IDs use a `_MOCK_` marker so operator dashboards
can badge them "sandbox".

Split logic (per PRD § "Financial Orchestration"):
  • Every node → transfer to its `financials.vendor_account` for
    `financials.cost_usd`. Nodes without a vendor go into an
    `unassigned` bucket (the demo will still show them).
  • The platform commission is a fixed 15% of the trip total, held in an
    internal `acc_voyager_platform` account. The PRD's 45/30/10/15 example
    (airline/hotel/guide/platform) emerges naturally when the DAG happens to
    have those exact splits.

Pure functions — no DB, no external calls.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


# Platform commission — matches the 15% in the PRD.
PLATFORM_COMMISSION = 0.15
PLATFORM_VENDOR = "acc_voyager_platform"


def _hex_id(prefix: str, seed: str) -> str:
    """Deterministic Razorpay-shaped id (18 chars after prefix) from a seed."""
    h = hashlib.blake2b(seed.encode(), digest_size=9).hexdigest().upper()
    return f"{prefix}_MOCK_{h}"


def _classify_purpose(node_type: str) -> str:
    if node_type.startswith("amadeus_flight"):
        return "flight"
    if node_type.startswith("amadeus_hotel"):
        return "hotel"
    if node_type == "otp_ground_transfer":
        return "ground_transit"
    if node_type == "guide_session":
        return "guide"
    if node_type == "meal":
        return "meal"
    if node_type == "activity":
        return "activity"
    return "misc"


def build_transfers(trip: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    """Group DAG nodes by vendor_account. Add a 15% platform commission.
    Returns `(transfers, total_usd)` where each transfer is Razorpay-shaped.
    """
    super_trip_id = trip.get("super_trip_id") or "ST-UNKNOWN"
    nodes = trip.get("nodes") or []

    # Aggregate cost per vendor + count of nodes + purpose set
    by_vendor: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"amount_usd": 0.0, "node_ids": [], "purposes": set()}
    )
    subtotal = 0.0
    for n in nodes:
        fin = n.get("financials") or {}
        # Skip cancelled nodes — they're not being paid for.
        if str(n.get("status")) == "cancelled":
            continue
        vendor = fin.get("vendor_account") or "unassigned"
        cost = float(fin.get("cost_usd") or 0)
        if cost <= 0:
            continue
        by_vendor[vendor]["amount_usd"] += cost
        by_vendor[vendor]["node_ids"].append(n.get("node_id"))
        by_vendor[vendor]["purposes"].add(_classify_purpose(str(n.get("type"))))
        subtotal += cost

    commission = round(subtotal * PLATFORM_COMMISSION, 2)
    total = round(subtotal + commission, 2)

    transfers: list[dict[str, Any]] = []
    order_seed = f"{super_trip_id}::route"

    for vendor, data in by_vendor.items():
        amount = round(data["amount_usd"], 2)
        pct = round((amount / total) * 100.0, 1) if total else 0.0
        transfers.append(
            {
                "transfer_id": _hex_id("trf", f"{order_seed}::{vendor}"),
                "account": vendor,
                "amount_usd": amount,
                "percent_of_total": pct,
                "purpose": sorted(data["purposes"])[0] if data["purposes"] else "misc",
                "node_ids": data["node_ids"],
                "status": "pending",   # flipped to "routed" on capture
                "on_hold": vendor == "acc_guide_escrow",   # escrow releases post-service
            }
        )

    # Platform commission — always last so UIs render it at the bottom.
    if commission > 0:
        transfers.append(
            {
                "transfer_id": _hex_id("trf", f"{order_seed}::platform"),
                "account": PLATFORM_VENDOR,
                "amount_usd": commission,
                "percent_of_total": round(PLATFORM_COMMISSION * 100.0, 1),
                "purpose": "platform_commission",
                "node_ids": [],
                "status": "pending",
                "on_hold": False,
            }
        )

    return transfers, total


def create_order(super_trip_id: str, amount_usd: float) -> str:
    return _hex_id("order", f"{super_trip_id}::{amount_usd:.2f}")


def capture_payment(order_id: str) -> str:
    """Simulate a successful capture — returns the payment_id."""
    return _hex_id("pay", f"{order_id}::captured")


def route_transfers(transfers: list[dict[str, Any]], captured_at: datetime | None = None) -> list[dict[str, Any]]:
    """Flip each transfer's status to `routed` (or `on_hold` for escrow).
    Returns a new list — does not mutate input."""
    captured_at = captured_at or datetime.now(timezone.utc)
    out: list[dict[str, Any]] = []
    for t in transfers:
        copy = dict(t)
        if copy.get("on_hold"):
            copy["status"] = "on_hold"
        else:
            copy["status"] = "routed"
        copy["routed_at"] = captured_at.isoformat()
        out.append(copy)
    return out


def build_refund_for_node(payment_id: str, node: dict[str, Any]) -> dict[str, Any] | None:
    """Return a Razorpay-shaped refund object for a cancelled node, or None
    if the node has no billable cost.
    """
    fin = node.get("financials") or {}
    amount = float(fin.get("cost_usd") or 0)
    if amount <= 0:
        return None
    node_id = str(node.get("node_id") or "unknown")
    return {
        "refund_id": _hex_id("rfnd", f"{payment_id}::{node_id}"),
        "payment_id": payment_id,
        "node_id": node_id,
        "vendor_account": fin.get("vendor_account"),
        "amount_usd": round(amount, 2),
        "reason": "node_cancelled",
        "status": "processed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
