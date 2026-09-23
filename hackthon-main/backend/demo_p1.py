"""P1 live end-to-end demo. Hits every recommendation-engine endpoint in
sequence against a running server on :8000 with real API output printed
in-line."""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


BASE = "http://127.0.0.1:8000"


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


def section(title):
    print()
    print("═" * 70)
    print(f"  {title}")
    print("═" * 70)


def main():
    # ---------- 0. Health ----------
    section("0. Health check")
    s, h = req("/health")
    print(f"  GET /health -> {s} {h}")
    assert s == 200

    # ---------- 1. Auth ----------
    section("1. Auth · POST /api/auth/login (existing traveler)")
    s, tok = req("/api/auth/login", "POST",
                 {"email": "traveler@voyager.dev", "password": "voyager123"})
    print(f"  -> {s}  user={tok['user']['email']}  role={tok['user']['role']}")
    print(f"  token (first 40): {tok['access_token'][:40]}...")
    token = tok["access_token"]

    _, me = req("/api/auth/me", token=token)
    print(f"  GET /api/auth/me -> preferences.activities = {me['preferences'].get('activities')}")

    # ---------- 2. F-02 Unified Data Catalog ----------
    section("2. F-02 Unified Data Catalog · GET /api/experiences?city=Kyoto")
    _, exps = req("/api/experiences?city=Kyoto&limit=100")
    print(f"  Kyoto catalog: {len(exps)} experiences")
    by_cat = {}
    for e in exps:
        by_cat.setdefault(e["category"], []).append(e["title"])
    for cat, titles in by_cat.items():
        print(f"    [{cat:<9}] {len(titles):>2}  {titles[0]}"
              + (f"  ... +{len(titles)-1}" if len(titles) > 1 else ""))

    # ---------- 3. F-01 + F-04 matching ----------
    section("3. F-01 Multi-Factor Matching · POST /api/recommendations/for-me")
    print("  Scenario: traveler in downtown Kyoto with a 4-hour window starting now")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    window_end = now + timedelta(hours=4)
    match_req = {
        "lat": 35.0116, "lng": 135.7681,
        "at": now.isoformat(),
        "window_end": window_end.isoformat(),
        "interests": [],       # will be filled from stored preferences
        "priorities": [],
        "travel_mode": "walking",
        "limit": 10,
        "city": "Kyoto",
    }
    _, res = req("/api/recommendations/for-me", "POST", match_req, token=token)
    print(f"  candidates scanned: {res['candidates_scanned']}  ·  returned: {len(res['results'])}")
    print(f"  window: {res['query_window_mins']} min")
    print()
    print(f"  {'score':<6} {'transit':<8} {'dur':<5} {'cost':<10} {'category':<10} title")
    for r in res["results"][:5]:
        e = r["experience"]
        print(f"  {r['score']:<6.1f} {r['transit_mins']:>4}m    {e['duration_mins']:>3}m  "
              f"INR {e['base_cost']:>5.0f}   {e['category']:<10} {e['title'][:36]}")

    print()
    print("  Top result's score breakdown:")
    top = res["results"][0]
    b = top["breakdown"]
    print(f"    interest={b['interest']:.2f}  logistics={b['logistics']:.2f}  "
          f"budget={b['budget']:.2f}  fit={b['fit']:.2f}")
    print("  Reasons:")
    for reason in top["reasons"][:4]:
        print(f"    · {reason}")

    # ---------- 4. F-04 gatekeeper hard-filter proof ----------
    section("4. F-04 Gatekeeper · same query, 60-min window (short)")
    short_req = {**match_req,
                 "window_end": (now + timedelta(minutes=60)).isoformat()}
    _, short = req("/api/recommendations/for-me", "POST", short_req, token=token)
    print(f"  candidates scanned: {short['candidates_scanned']}")
    print(f"  returned:           {len(short['results'])}")
    for r in short["results"]:
        e = r["experience"]
        assert r["transit_mins"] + e["duration_mins"] <= 60, "gatekeeper violation!"
        print(f"    {r['score']:<5.1f}  {e['title'][:36]:<36} transit={r['transit_mins']}m dur={e['duration_mins']}m ({r['transit_mins']+e['duration_mins']} <= 60 ✓)")
    print("  ✓ Every result fits the 60-min window — gatekeeper hard-filter proven")

    # ---------- 5. F-03 Maps ----------
    section("5. F-03 Maps · POST /api/maps/distance")
    dist_req = {
        "origin":      {"lat": 35.0116, "lng": 135.7681},   # Kyoto Sta.
        "destination": {"lat": 34.9977, "lng": 135.7854},   # Kiyomizu-dera
        "mode": "walking",
    }
    _, d = req("/api/maps/distance", "POST", dist_req, token=token)
    print(f"  Kyoto Sta. -> Kiyomizu-dera walking: {d['distance_km']} km · {d['duration_mins']} min · provider={d['provider']}")

    section("6. F-03 Live Tracking · POST /api/maps/ping")
    # Get the seeded Kyoto trip's earliest slot for anchor testing
    _, its = req("/api/itineraries", token=token)
    kyoto = next((i for i in its if i["title"] == "Kyoto Weekend"), None)
    if kyoto and kyoto["slots"]:
        anchor = min(kyoto["slots"], key=lambda s: s["start_at"])
        print(f"  Anchoring against slot: '{anchor['title']}' start={anchor['start_at']}")
        ping_req = {"lat": 34.9700, "lng": 135.7600, "speed_kmh": 12}
        _, ping_res = req(f"/api/maps/ping?itinerary_id={kyoto['id']}", "POST", ping_req, token=token)
        if ping_res.get("alert"):
            a = ping_res["alert"]
            print(f"  ⚠ DriftAlert [{a['severity']}]: {a['message']}")
        else:
            print(f"  No drift alert — projected arrival on time.")
    else:
        # Fall back to a plain slot-less itinerary
        print("  (no slots seeded on Kyoto itinerary — skipping anchor test)")
        ping_req = {"lat": 34.9700, "lng": 135.7600, "speed_kmh": 12}
        _, ping_res = req("/api/maps/ping", "POST", ping_req, token=token)
        print(f"  Ping accepted: id={ping_res['ping']['id'][:8]}, alert={ping_res['alert']}")

    # ---------- 7. F-05 Gap-Filler ----------
    section("7. F-05 Itinerary Gap-Filler · POST /api/recommendations/gap-fill")
    # Create a mini itinerary with two anchored slots leaving a 2h30 gap
    tomorrow_9 = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    tiny = {
        "title": "Kyoto Day",
        "destination_city": "Kyoto",
        "slots": [
            {"title": "Museum tour", "kind": "activity",
             "start_at": tomorrow_9.isoformat(),
             "end_at": (tomorrow_9 + timedelta(hours=2)).isoformat(),
             "lat": 35.0100, "lng": 135.7700, "buffer_after_mins": 15},
            {"title": "Dinner reservation", "kind": "activity",
             "start_at": (tomorrow_9 + timedelta(hours=5, minutes=30)).isoformat(),
             "end_at":   (tomorrow_9 + timedelta(hours=7)).isoformat(),
             "lat": 35.0150, "lng": 135.7720, "buffer_before_mins": 15},
        ],
    }
    _, mini = req("/api/itineraries", "POST", tiny, token=token)
    print(f"  Created itinerary '{mini['title']}' with {len(mini['slots'])} anchors")
    print(f"    slot 1: {mini['slots'][0]['title']}  {mini['slots'][0]['start_at'][11:16]}-{mini['slots'][0]['end_at'][11:16]}")
    print(f"    slot 2: {mini['slots'][1]['title']}  {mini['slots'][1]['start_at'][11:16]}-{mini['slots'][1]['end_at'][11:16]}")
    print(f"    → expected gap: ~2h30 between them")

    _, gf = req("/api/recommendations/gap-fill", "POST", {
        "itinerary_id": mini["id"],
        "interests": ["food-tours", "photography"],
        "priorities": ["food"],
        "per_gap_limit": 3,
        "travel_mode": "walking",
    }, token=token)
    print(f"\n  Detected {len(gf['gaps'])} fillable gap(s):")
    for gap in gf["gaps"]:
        g = gap["gap"]
        print(f"    Gap: {g['start_at'][11:16]} → {g['end_at'][11:16]} ({g['duration_mins']} min)")
        print(f"          between '{g['anchor_before']}' and '{g['anchor_after']}'")
        print(f"          {len(gap['suggestions'])} suggestion(s):")
        for s in gap["suggestions"]:
            e = s["experience"]
            print(f"            · {s['score']:<5.1f}  {e['title']:<36} {e['duration_mins']}m  INR {e['base_cost']:.0f}")

    # ---------- 8. F-06 SSE + F-07 Provider ----------
    section("8. F-07 Provider CRUD + F-06 SSE burst")
    # Log in as provider, create an experience, watch that a catalog:changed event fires
    _, pr_login = req("/api/auth/login", "POST",
                      {"email": "provider@voyager.dev", "password": "voyager123"})
    pr_tok = pr_login["access_token"]
    print(f"  Provider logged in as {pr_login['user']['email']} (role={pr_login['user']['role']})")

    # Start listening on SSE in a background thread and see the event
    import threading
    events_seen: list[dict] = []

    def sse_listener():
        try:
            r = urllib.request.Request(f"{BASE}/api/realtime/stream")
            with urllib.request.urlopen(r, timeout=6) as resp:
                for line in resp:
                    line = line.decode().rstrip()
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                        try:
                            events_seen.append(json.loads(payload))
                        except Exception:
                            pass
                    if len(events_seen) >= 2:
                        break
        except Exception:
            pass

    t = threading.Thread(target=sse_listener, daemon=True)
    t.start()
    time.sleep(0.5)  # give the listener a beat to open the stream

    # Now write to the catalog
    body = {
        "title": "Secret Ramen Bar Pop-up (live-demo)",
        "description": "New popup in Gion tonight.",
        "category": "FOOD",
        "base_cost": 850,
        "currency": "INR",
        "duration_mins": 75,
        "lat": 35.0037, "lng": 135.7788,
        "city": "Kyoto",
        "country": "Japan",
        "capacity_max": 20,
        "seats_available": 20,
        "interest_tags": ["food-tours"],
        "hours": [{"day_of_week": d, "open_time": "18:00", "close_time": "23:00"} for d in range(7)],
    }
    s, new_exp = req("/api/providers/me/experiences", "POST", body, token=pr_tok)
    print(f"  POST /api/providers/me/experiences -> {s}  id={new_exp['id'][:8]}  slug={new_exp['slug']}")

    # Give the SSE stream 3s to deliver
    time.sleep(3)
    print(f"\n  SSE events captured on /api/realtime/stream:")
    for ev in events_seen[:5]:
        print(f"    · {ev}")
    assert any(ev.get("type") == "catalog:changed" for ev in events_seen), \
        "expected a catalog:changed event on the SSE stream"
    print("  ✓ SSE delivered catalog:changed — F-06 dynamic re-recommendation trigger fires")

    # ---------- 9. Verify the fresh listing is in match queries immediately ----------
    section("9. F-06 downstream: new listing appears in traveler recommendations")
    # Look for it right now
    _, fresh = req("/api/recommendations/for-me", "POST", {
        "lat": 35.0037, "lng": 135.7788,
        "at": now.isoformat(),
        "window_end": (now + timedelta(hours=6)).isoformat(),
        "interests": ["food-tours"],
        "priorities": ["food"],
        "travel_mode": "walking",
        "limit": 20,
        "city": "Kyoto",
    }, token=token)
    hit = next((r for r in fresh["results"]
                if r["experience"]["title"].startswith("Secret Ramen Bar")), None)
    if hit:
        print(f"  New listing surfaced at rank "
              f"{[i for i, r in enumerate(fresh['results']) if r['experience']['id']==hit['experience']['id']][0]+1} "
              f"with score {hit['score']}")
    else:
        print("  New listing not in top-20 for this window (may need broader window).")

    print()
    print("═" * 70)
    print("  ✓ P1 live end-to-end complete — every feature exercised against a real server")
    print("═" * 70)


if __name__ == "__main__":
    main()
