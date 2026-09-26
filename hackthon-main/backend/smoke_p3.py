"""End-to-end P3 smoke test. Assumes uvicorn on :8765 with seeded data."""
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


def main():
    # login operator + traveler
    _, op = req("/api/auth/login", "POST", {"email": "operator@voyager.dev", "password": "voyager123"})
    op_tok = op["access_token"]
    _, tr = req("/api/auth/login", "POST", {"email": "traveler@voyager.dev", "password": "voyager123"})
    tr_tok = tr["access_token"]

    # RBAC — traveler must not be able to POST a zone or view operator dashboard
    s, err = req("/api/zones", "POST", {"city": "X", "name": "X", "center_lat": 0, "center_lng": 0}, token=tr_tok)
    print("traveler POSTs /api/zones ->", s, err.get("detail") if isinstance(err, dict) else "")
    s, err = req("/api/operator/dashboard", token=tr_tok)
    print("traveler GETs /api/operator/dashboard ->", s, err.get("detail") if isinstance(err, dict) else "")

    # zones list is public
    _, zones = req("/api/zones", token=tr_tok)
    print(f"\nzones seeded: {len(zones)}")
    zone_by_name = {z["name"]: z for z in zones}
    gion = zone_by_name["Gion"]
    arashi = zone_by_name["Arashiyama"]

    # --- F-14 operator dashboard: densities + forecasts + balancer ---
    _, dash = req("/api/operator/dashboard", token=op_tok)
    print("\n--- F-14 OPERATOR DASHBOARD ---")
    print(f"{'zone':<15} {'density%':>10} {'proj60m%':>10} {'slope/min':>10} {'to_sat':>10} {'status':<25} {'evt_press':<8}")
    for f in dash["forecasts"]:
        d = next((x for x in dash["zone_densities"] if x["zone_id"] == f["zone_id"]), None)
        print(f"{f['zone_name']:<15} {d['density_pct'] if d else 0:>10.2f} {f['projected_density_pct_60m']:>10.2f} "
              f"{f['slope_pct_per_min']:>10.3f} {(f['minutes_to_saturation'] or float('nan')):>10.1f} "
              f"{f['status']:<25} {str(f['event_pressure_applied']):<8}")

    print("\n--- F-15 acceptance: Gion projected to saturate within 60m ---")
    gion_forecast = next(f for f in dash["forecasts"] if f["zone_id"] == gion["id"])
    passes = gion_forecast["status"] == "APPROACHING_SATURATION" and (
        gion_forecast["minutes_to_saturation"] or 999
    ) <= 60
    print(f"  Gion status={gion_forecast['status']}, minutes_to_saturation={gion_forecast['minutes_to_saturation']} -> passes={passes}")

    print("\n--- F-17 acceptance: Gion event ends in 20m -> event_pressure_applied=True ---")
    print(f"  event_pressure_applied={gion_forecast['event_pressure_applied']}")

    print("\n--- F-16 acceptance: balancer suggests low-density Arashiyama for congested Gion ---")
    for r in dash["balancer_recommendations"]:
        print(f"  from={r['from_zone_name']} ({r['from_density_pct']}%) -> to={r['to_zone_name']} ({r['to_density_pct']}%) dist={r['distance_km']}km")
        if r.get("attached_nudge"):
            n = r["attached_nudge"]
            print(f"    F-20 nudge: [{n['kind']}] {n['title']}")

    # --- F-18 staggering plan for the concert ---
    _, events = req(f"/api/zones/{gion['id']}/events", token=op_tok)
    ev = events[0]
    _, plan = req(f"/api/events/{ev['id']}/stagger", "POST",
                  {"event_id": ev["id"], "max_per_band": 500, "band_minutes": 15}, token=op_tok)
    print("\n--- F-18 STAGGERING PLAN ---")
    print(f"  event: {plan['event_name']} ends at {plan['event_end_at']}, attendees={plan['total_attendees']}")
    for b in plan["bands"]:
        print(f"    band {b['label']}: {b['start_at']} -> {b['end_at']}  headcount={b['assigned_headcount']}")

    # --- F-19 attendee-scoped view ---
    print("\n--- F-19 ATTENDEE VIEW (in Gion) ---")
    _, view = req(f"/api/capacity/for-attendee?zone_id={gion['id']}", token=tr_tok)
    print(f"  zone={view['zone_name']} density={view['density_pct']}% status={view['status']}")
    print(f"  tip: {view['tip']}")
    if view.get("suggested_alternative"):
        alt = view["suggested_alternative"]
        print(f"  suggested_alternative: {alt['to_zone_name']} ({alt['to_density_pct']}%) dist={alt['distance_km']}km")
        if alt.get("attached_nudge"):
            n = alt["attached_nudge"]
            print(f"  attached nudge: [{n['kind']}] {n['title']}")

    print("\n--- F-19 ATTENDEE VIEW (in quiet Arashiyama) ---")
    _, view2 = req(f"/api/capacity/for-attendee?zone_id={arashi['id']}", token=tr_tok)
    print(f"  zone={view2['zone_name']} status={view2['status']}, suggested_alt={view2.get('suggested_alternative')}")
    print(f"  tip: {view2['tip']}")

    # --- 5,000 metrics/sec ingestion sanity: batch of 200 ---
    import time
    batch = {"metrics": [
        {"zone_id": gion["id"], "source_kind": "TRANSIT", "source_label": f"bus-{i}",
         "occupancy_count": 40 + i % 20, "capacity_max": 60} for i in range(200)
    ]}
    t0 = time.perf_counter()
    s, rows = req("/api/capacity/metrics/batch", "POST", batch, token=op_tok)
    dt = time.perf_counter() - t0
    print(f"\n--- ingestion sanity ---")
    print(f"  batch of 200 metrics: status={s} inserted={len(rows) if isinstance(rows, list) else 'err'} time={dt*1000:.1f}ms")


if __name__ == "__main__":
    main()
