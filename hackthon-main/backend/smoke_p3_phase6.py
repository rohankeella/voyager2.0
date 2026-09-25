"""DTO-P3 Phase 6 smoke — Razorpay Route split payment end-to-end.

Flow:
  1. Register traveler
  2. Create + approve a SuperTrip
  3. POST /checkout → transfers created (pending)
  4. POST /checkout/capture → transfers routed, trip status = active
  5. Trigger cancellation on one node via Phase 5 disruption
  6. Apply "cheapest" plan → cascade cancels + refund auto-created
  7. GET /payment → verify refund is present

Run: python smoke_p3_phase6.py  (backend must be running on :8000)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE = "http://127.0.0.1:8000"


def register_traveler() -> str:
    email = f"pay_{uuid.uuid4().hex[:6]}@example.com"
    r = httpx.post(
        f"{BASE}/api/auth/register",
        json={"email": email, "password": "paypay12345", "full_name": "Pay Smoke", "country": "IN"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def create_and_approve_trip(token: str) -> str:
    start = datetime(2027, 5, 10, 8, 0, tzinfo=timezone.utc)
    payload = {
        "payload": {
            "super_trip_id": f"ST-PAY-{uuid.uuid4().hex[:4].upper()}",
            "traveler_id": "USR-pay",
            "status": "pending_review",
            "global_constraints": {
                "max_budget_usd": 4000,
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=5)).isoformat(),
                "home_location": "Bangalore",
                "traveler_count": 1,
                "preferences": {"tags": ["art"]},
            },
            "nodes": [
                {
                    "node_id": "N-01-FLIGHT",
                    "type": "amadeus_flight_order",
                    "status": "pending",
                    "execution_data": {
                        "start_time": start.isoformat(),
                        "end_time": (start + timedelta(hours=12)).isoformat(),
                        "origin_lat": 13.2, "origin_lng": 77.7,
                        "destination_lat": 49.0, "destination_lng": 2.5,
                        "pnr_number": "PAY01",
                    },
                    "depends_on": [],
                    "financials": {"cost_usd": 900, "payment_status": "unpaid", "vendor_account": "acc_airline_6E"},
                    "title": "BLR -> CDG",
                },
                {
                    "node_id": "N-02-HOTEL",
                    "type": "amadeus_hotel_booking",
                    "status": "pending",
                    "execution_data": {
                        "start_time": (start + timedelta(hours=14)).isoformat(),
                        "end_time": (start + timedelta(days=4, hours=11)).isoformat(),
                        "location_label": "Le Marais",
                        "lat": 48.86, "lng": 2.35,
                    },
                    "depends_on": ["N-01-FLIGHT"],
                    "financials": {"cost_usd": 480, "payment_status": "unpaid", "vendor_account": "acc_hotel_LM"},
                    "title": "Paris hotel",
                },
                {
                    "node_id": "N-03-ACTIVITY",
                    "type": "activity",
                    "status": "pending",
                    "execution_data": {
                        "start_time": (start + timedelta(days=1, hours=10)).isoformat(),
                        "end_time": (start + timedelta(days=1, hours=13)).isoformat(),
                        "location_label": "Louvre",
                        "lat": 48.86, "lng": 2.34,
                    },
                    "depends_on": ["N-02-HOTEL"],
                    "financials": {"cost_usd": 60, "payment_status": "unpaid", "vendor_account": "acc_activity"},
                    "title": "Louvre tour",
                },
                {
                    "node_id": "N-04-GUIDE",
                    "type": "guide_session",
                    "status": "pending",
                    "execution_data": {
                        "start_time": (start + timedelta(days=2, hours=10)).isoformat(),
                        "end_time": (start + timedelta(days=2, hours=13)).isoformat(),
                        "location_label": "Montmartre",
                        "lat": 48.89, "lng": 2.34,
                    },
                    "depends_on": ["N-02-HOTEL"],
                    "financials": {"cost_usd": 120, "payment_status": "unpaid", "vendor_account": "acc_guide_escrow"},
                    "title": "Montmartre walk",
                },
            ],
        },
        "source_prompt": "phase 6 smoke",
    }
    h = {"Authorization": f"Bearer {token}"}
    r = httpx.post(f"{BASE}/api/super-trips", headers=h, json=payload, timeout=10)
    r.raise_for_status()
    trip_id = r.json()["id"]

    r = httpx.post(f"{BASE}/api/super-trips/{trip_id}/approve", headers=h, timeout=10)
    r.raise_for_status()
    return trip_id


def run() -> None:
    print("=== Phase 6 smoke ===")
    token = register_traveler()
    h = {"Authorization": f"Bearer {token}"}
    trip_id = create_and_approve_trip(token)
    print(f"[trip approved] {trip_id}")

    # -- checkout ---
    print("\n[1] POST /checkout")
    r = httpx.post(f"{BASE}/api/super-trips/{trip_id}/checkout", headers=h, timeout=10)
    r.raise_for_status()
    p = r.json()
    print(f"   payment_id={p['id']}  order={p['razorpay_order_id']}  status={p['status']}  total=${p['total_usd']}")
    print(f"   transfers ({len(p['transfers'])}):")
    for t in p["transfers"]:
        hold = " [ESCROW]" if t.get("on_hold") else ""
        print(f"     {t['account']:24s} ${t['amount_usd']:7.2f}  {t['percent_of_total']:5.1f}%  {t['purpose']:20s} {t['status']}{hold}")

    assert p["status"] == "pending"
    total_subs = round(sum(t["amount_usd"] for t in p["transfers"]), 2)
    assert abs(total_subs - p["total_usd"]) < 0.01, "transfer sum != total"
    # 15% commission check
    commission = next((t for t in p["transfers"] if t["purpose"] == "platform_commission"), None)
    assert commission is not None
    assert abs(commission["percent_of_total"] - 15.0) < 0.05, f"commission not 15%: {commission['percent_of_total']}"

    # -- capture ---
    print("\n[2] POST /checkout/capture")
    r = httpx.post(f"{BASE}/api/super-trips/{trip_id}/checkout/capture", headers=h, timeout=10)
    r.raise_for_status()
    p = r.json()
    print(f"   status={p['status']}  payment_id={p['razorpay_payment_id']}")
    for t in p["transfers"]:
        print(f"     {t['account']:24s} {t['status']}")
    assert p["status"] == "captured"
    assert p["razorpay_payment_id"] is not None
    for t in p["transfers"]:
        if t.get("on_hold"):
            assert t["status"] == "on_hold"
        else:
            assert t["status"] == "routed"

    # -- cancel a node via Phase 5 disruption + apply cheapest --
    print("\n[3] Trigger cancellation on N-03-ACTIVITY (Louvre)")
    r = httpx.post(
        f"{BASE}/api/super-trips/{trip_id}/disruptions",
        headers=h,
        json={"node_id": "N-03-ACTIVITY", "kind": "cancellation", "note": "smoke: cancelled"},
        timeout=15,
    )
    r.raise_for_status()
    d = r.json()
    print(f"   disruption_id={d['id']}  plans={len(d['plans'])}")

    print("\n[4] Apply 'cheapest' plan (should cancel the activity + auto-refund)")
    r = httpx.post(
        f"{BASE}/api/super-trips/{trip_id}/disruptions/{d['id']}/apply/cheapest",
        headers=h, timeout=15,
    )
    r.raise_for_status()

    # -- verify refund ---
    print("\n[5] GET /payment (verify auto-refund)")
    r = httpx.get(f"{BASE}/api/super-trips/{trip_id}/payment", headers=h, timeout=10)
    r.raise_for_status()
    p = r.json()
    print(f"   status={p['status']}  refunded=${p['refunded_usd']}  refunds={len(p['refunds'])}")
    for rf in p["refunds"]:
        print(f"     {rf['refund_id']} · node={rf['node_id']} · vendor={rf['vendor_account']} · ${rf['amount_usd']}")

    assert p["status"] in ("partially_refunded", "refunded"), f"expected partial refund, got {p['status']}"
    assert p["refunded_usd"] > 0, "no refund recorded"

    print("\n[OK] Phase 6 smoke passed.")


if __name__ == "__main__":
    run()
