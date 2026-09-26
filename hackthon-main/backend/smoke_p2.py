"""Ad-hoc smoke test for P2 ledger. Run against a live uvicorn on :8765."""
import json
import urllib.error
import urllib.request


BASE = "http://127.0.0.1:8765"


def req(path, method="GET", data=None, token=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=body, method=method)
    r.add_header("content-type", "application/json")
    if token:
        r.add_header("authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def name(mid, lookup):
    return lookup.get(mid, mid[:6])


def main():
    # login demo traveler
    _, tok = req("/api/auth/login", "POST", {"email": "traveler@voyager.dev", "password": "voyager123"})
    token = tok["access_token"]
    me = tok["user"]

    # create/login friend
    s, fr = req("/api/auth/register", "POST", {"email": "friend@voyager.dev", "password": "voyager123", "full_name": "Friend"})
    if s == 409:
        _, fr = req("/api/auth/login", "POST", {"email": "friend@voyager.dev", "password": "voyager123"})
    friend_token = fr["access_token"]
    friend_user = fr["user"]

    s, grp = req("/api/groups", "POST", {
        "name": "Kyoto Weekend",
        "trip_destination": "Kyoto",
        "members": [
            {"display_name": friend_user["full_name"], "email": friend_user["email"], "user_id": friend_user["id"], "role": "participant"},
            {"display_name": "Guest Guy", "role": "participant"},
            {"display_name": "Guest Gal", "role": "participant"},
        ],
    }, token=token)
    print("group created:", s, grp["id"], "members=", len(grp["members"]))
    gid = grp["id"]
    members = {m["display_name"]: m["id"] for m in grp["members"]}
    lookup = {v: k for k, v in members.items()}
    ava_id = members[me["full_name"]]
    friend_id = members[friend_user["full_name"]]
    guy_id = members["Guest Guy"]
    gal_id = members["Guest Gal"]

    # F-09 EQUAL
    s, e1 = req(f"/api/groups/{gid}/expenses", "POST", {
        "title": "Kaiseki dinner", "amount": 10000, "currency": "INR",
        "payer_member_id": ava_id, "split_strategy": "EQUAL",
        "participants": [{"member_id": mid} for mid in (ava_id, friend_id, guy_id, gal_id)],
    }, token=token)
    print("EQUAL 10000/4:", [(name(p["member_id"], lookup), p["computed_amount_base"]) for p in e1["participants"]])

    # F-09 PERCENTAGE (rounding drift absorbed by payer)
    s, e2 = req(f"/api/groups/{gid}/expenses", "POST", {
        "title": "Taxi tour", "amount": 1000, "currency": "INR",
        "payer_member_id": friend_id, "split_strategy": "PERCENTAGE",
        "participants": [
            {"member_id": ava_id, "share_value": 33.33},
            {"member_id": friend_id, "share_value": 33.33},
            {"member_id": guy_id, "share_value": 33.34},
        ],
    }, token=token)
    print("PERCENT 33.33/33.33/33.34 of 1000:", [(name(p["member_id"], lookup), p["computed_amount_base"]) for p in e2["participants"]])
    print("  sum matches total:", round(sum(p["computed_amount_base"] for p in e2["participants"]), 2) == 1000)

    # F-09 SHARE_WEIGHTED (rooms 2:2:1:1)
    s, e3 = req(f"/api/groups/{gid}/expenses", "POST", {
        "title": "Hotel", "amount": 12000, "currency": "INR",
        "payer_member_id": ava_id, "split_strategy": "SHARE_WEIGHTED",
        "participants": [
            {"member_id": ava_id, "share_value": 2},
            {"member_id": friend_id, "share_value": 2},
            {"member_id": guy_id, "share_value": 1},
            {"member_id": gal_id, "share_value": 1},
        ],
    }, token=token)
    print("WEIGHTED 2:2:1:1 of 12000:", [(name(p["member_id"], lookup), p["computed_amount_base"]) for p in e3["participants"]])

    # F-09 ORGANIZER_COVERED
    s, e4 = req(f"/api/groups/{gid}/expenses", "POST", {
        "title": "Ava treats everyone", "amount": 800, "currency": "INR",
        "payer_member_id": ava_id, "split_strategy": "ORGANIZER_COVERED",
        "participants": [{"member_id": mid} for mid in (ava_id, friend_id, guy_id, gal_id)],
    }, token=token)
    print("ORGANIZER_COVERED 800:", [(name(p["member_id"], lookup), p["computed_amount_base"]) for p in e4["participants"]])

    # F-09 EXACT_AMOUNT — bad shares
    s, err = req(f"/api/groups/{gid}/expenses", "POST", {
        "title": "bad exact", "amount": 1000, "currency": "INR",
        "payer_member_id": ava_id, "split_strategy": "EXACT_AMOUNT",
        "participants": [{"member_id": ava_id, "share_value": 400}, {"member_id": friend_id, "share_value": 500}],
    }, token=token)
    print("EXACT bad shares -> status:", s, "detail:", err.get("detail") if isinstance(err, dict) else err)

    # F-11 + F-12 organizer ledger view
    s, view = req(f"/api/groups/{gid}/ledger", token=token)
    print("--- ORGANIZER VIEW ---")
    print("total spend:", view["total_spend_base"], "currency:", view["base_currency"])
    for b in view["balances"]:
        print(f"  {b['display_name']:<15} paid={b['paid_to_vendors']:>10.2f}  owed={b['owed_from_participation']:>10.2f}  net={b['net_balance']:>+10.2f}")
    print("settlements (min-cashflow):")
    for tr in view["settlements"]:
        print(f"  {tr['from_display_name']:<15} -> {tr['to_display_name']:<15} {tr['amount_base']:>10.2f}")

    # F-13 RBAC: friend hitting organizer view should 403
    s, err = req(f"/api/groups/{gid}/ledger", token=friend_token)
    print("friend hitting organizer view -> status:", s, "detail:", err.get("detail") if isinstance(err, dict) else err)

    # F-13 participant view for friend
    s, me_view = req(f"/api/groups/{gid}/ledger/me", token=friend_token)
    print("--- FRIEND PARTICIPANT VIEW ---")
    print(f"my net balance: {me_view['my_balance']['net_balance']:+.2f}")
    print("action items:")
    for a in me_view["action_items"]:
        verb = "owes" if a["direction"] == "owe" else "is owed by"
        print(f"  friend {verb} {a['counterpart_display_name']} {a['amount_base']:.2f}")
    print("my expenses:", [(e["title"], e["my_share_base"], "PAID" if e["paid_by_me"] else "owe") for e in me_view["my_expenses"]])

    # F-10 reactive recalc: change hotel to EQUAL
    s, e3b = req(f"/api/groups/{gid}/expenses/{e3['id']}", "PATCH", {"split_strategy": "EQUAL"}, token=token)
    print("after switching hotel to EQUAL:", [(name(p["member_id"], lookup), p["computed_amount_base"]) for p in e3b["participants"]])

    # F-10 reactive recalc: remove a participant from the hotel (drop gal), leaving 3 payers
    s, e3c = req(f"/api/groups/{gid}/expenses/{e3['id']}", "PATCH", {
        "participants": [{"member_id": ava_id}, {"member_id": friend_id}, {"member_id": guy_id}],
    }, token=token)
    print("after removing gal from hotel:", [(name(p["member_id"], lookup), p["computed_amount_base"]) for p in e3c["participants"]])


if __name__ == "__main__":
    main()
