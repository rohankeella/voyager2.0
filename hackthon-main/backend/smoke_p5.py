"""End-to-end P5 smoke test. Assumes uvicorn on :8765 with seeded data."""
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
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, None


def name(nid, lookup):
    return lookup.get(nid, nid[:6])


def main():
    _, tok = req("/api/auth/login", "POST", {"email": "traveler@voyager.dev", "password": "voyager123"})
    token = tok["access_token"]

    # Find the seeded Kyoto trip
    _, its = req("/api/itineraries", token=token)
    kyoto = next(i for i in its if i["title"] == "Kyoto Weekend")
    itid = kyoto["id"]
    _, g = req(f"/api/itineraries/{itid}/graph", token=token)
    print(f"F-25 graph loaded: {len(g['nodes'])} nodes, {len(g['edges'])} edges")
    nodes_by_id = {n["id"]: n["title"] for n in g["nodes"]}

    for n in sorted(g["nodes"], key=lambda x: x["start_at"]):
        print(f"  [{n['kind']:<8}] {n['title']:<32} {n['start_at'][11:16]} -> {n['end_at'][11:16]}  refund={n['refund_class']}")

    # F-30: risks — the seed builds a 25-min transfer buffer < 45 required
    print("\nF-30 buffer risks")
    _, risks = req(f"/api/itineraries/{itid}/risks", token=token)
    for r in risks["risks"]:
        print(f"  [{r['severity']:<8}] {r['from_title']} -> {r['to_title']}: {r['actual_buffer_mins']}m actual / {r['required_buffer_mins']}m required")
        print(f"       {r['message']}")
    assert any(r["from_title"].startswith("Flight BOM") and r["to_title"].startswith("Airport") for r in risks["risks"]), "expected tight flight->transfer risk"
    print(f"  at_risk_node_ids: {[name(x, nodes_by_id) for x in risks['at_risk_node_ids']]}")

    # persist AT_RISK statuses
    _, applied = req(f"/api/itineraries/{itid}/risks/apply", "POST", token=token)
    print(f"  after apply -> {len(applied['at_risk_node_ids'])} nodes flagged")

    # --- F-26 + F-31: multi-disruption ---
    flight_in_id = next(n["id"] for n in g["nodes"] if n["kind"] == "FLIGHT" and n["title"].startswith("Flight BOM"))
    hotel_in_id = next(n["id"] for n in g["nodes"] if n["title"].startswith("Hotel Check-in"))
    print("\nF-26 + F-31 multi-root disruption: flight delayed 120m AND hotel-in delayed 60m")
    s, ds = req(f"/api/itineraries/{itid}/disruptions", "POST", [
        {"node_id": flight_in_id, "kind": "DELAY", "delta_mins": 120, "note": "ATC hold"},
        {"node_id": hotel_in_id, "kind": "DELAY", "delta_mins": 60, "note": "overbooking"},
    ], token=token)
    print(f"  declared {len(ds)} disruptions -> {s}")

    _, impact = req(f"/api/itineraries/{itid}/impact", token=token)
    print(f"F-26 downstream impact: {len(impact['impacted_node_ids'])} nodes IMPACTED")
    for n in impact["impacted_nodes"]:
        print(f"    - {n['title']:<32} status={n['status']}")

    # --- F-27 recovery generation (returns >= 2 distinct plans) ---
    print("\nF-27 recovery generation")
    _, resp = req(f"/api/itineraries/{itid}/recovery", "POST", token=token)
    print(f"  disruptions considered: {len(resp['disruptions'])}")
    print(f"  plans returned: {len(resp['plans'])}")
    assert len(resp["plans"]) >= 2, "F-27 acceptance requires at least two options"
    for p in resp["plans"]:
        print(f"  --- {p['label']:<24} strategy={p['strategy']:<12} penalty={p['penalty']:>8.1f}")
        print(f"       Δcost=₹{p['cost_delta']:>7.0f}  Δtime={p['time_delta_mins']:>4}min  touches={p['nodes_modified']} nodes")
        print(f"       {p['summary']}")
        for a in p["actions"][:3]:
            print(f"         · [{a['kind']:<14}] {a['detail']}  (Δ{a['delta_mins']}m ₹{a['monetary_penalty']:.0f})")
        if len(p["actions"]) > 3:
            print(f"         · … +{len(p['actions']) - 3} more actions")

    # --- F-29 apply the fastest plan ---
    fastest = next(p for p in resp["plans"] if p["strategy"] == "fastest")
    print(f"\nF-29 apply plan: {fastest['label']}")
    _, applied_report = req(f"/api/itineraries/{itid}/recovery/{fastest['id']}/apply", "POST", token=token)
    print(f"  shifted={applied_report['nodes_shifted']} modified={applied_report['nodes_modified']} "
          f"cancelled={applied_report['nodes_cancelled']} dropped={applied_report['nodes_dropped']} "
          f"edges_removed={applied_report['edges_removed']}")

    print("\ngraph after apply:")
    for n in sorted(applied_report["graph"]["nodes"], key=lambda x: x["start_at"]):
        print(f"  [{n['kind']:<8}] {n['title']:<32} {n['start_at'][11:16]} -> {n['end_at'][11:16]}  status={n['status']}")

    # No lingering IMPACTED / DISRUPTED
    residual = [n for n in applied_report["graph"]["nodes"] if n["status"] in ("IMPACTED", "DISRUPTED")]
    print(f"\nresidual IMPACTED/DISRUPTED nodes: {len(residual)}  (should be 0)")

    # Re-apply should 409
    s, err = req(f"/api/itineraries/{itid}/recovery/{fastest['id']}/apply", "POST", token=token)
    print(f"\napply same plan again -> {s} {err.get('detail') if isinstance(err, dict) else ''}")


if __name__ == "__main__":
    main()
