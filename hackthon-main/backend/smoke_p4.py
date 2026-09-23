"""End-to-end P4 smoke test. Assumes uvicorn on :8765 with seeded data."""
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
    _, prov_login = req("/api/auth/login", "POST", {"email": "provider@voyager.dev", "password": "voyager123"})
    prov_tok = prov_login["access_token"]
    _, tr_login = req("/api/auth/login", "POST", {"email": "traveler@voyager.dev", "password": "voyager123"})
    tr_tok = tr_login["access_token"]

    # F-23 registry
    _, tags = req("/api/context-tags")
    print(f"F-23 context tag registry — {len(tags)} tags")
    for t in tags[:4]:
        print(f"  #{t['display']:<20} filter: {t['experience_filter_summary']}")
    print(f"  … +{max(0, len(tags)-4)} more")

    # F-22 feed
    _, feed = req("/api/stories")
    print(f"\nF-22 feed — considered {feed['considered']} stories")
    for r in feed["stories"]:
        p = r["post"]
        print(f"  score={r['score']:>5.1f}  quality={r['quality_component']:.2f}  fresh={r['freshness_component']:.2f}  '{p['title'][:40]}'")
        print(f"        tags={p['context_tags']}  narrative_score={p['narrative_quality_score']}")

    # F-22 acceptance: a brand new post (days_old=0) should beat a 30-day-old post
    # of similar quality. The Gion story is fresh; Arashiyama is 30 days old.
    print("\nF-22 acceptance: fresh post beats older on freshness alone")
    fresh = next((r for r in feed["stories"] if r["post"]["slug"].startswith("rainy-afternoons")), None)
    older = next((r for r in feed["stories"] if r["post"]["slug"].startswith("under")), None)
    if fresh and older:
        print(f"  fresh score={fresh['score']}  vs  older score={older['score']}  passes={fresh['score'] > older['score']}")

    # F-23 tag filter
    print("\nF-23 tag filter — ?tag=RainyDayFriendly")
    _, filtered = req("/api/stories?tag=RainyDayFriendly")
    print(f"  applied_tag={filtered['applied_tag']}  hits={len(filtered['stories'])}")
    for r in filtered["stories"]:
        print(f"    - {r['post']['title']}  tags={r['post']['context_tags']}")

    print("\nF-23 tag filter — ?tag=Budget")
    _, budget_hits = req("/api/stories?tag=Budget")
    print(f"  applied_tag={budget_hits['applied_tag']}  hits={len(budget_hits['stories'])}")
    for r in budget_hits["stories"]:
        print(f"    - {r['post']['title']}")

    # F-24 in-post updates — rainy afternoons post has weather + crowd updates
    slug = "rainy-afternoons-in-gion-quietly"

    print(f"\nF-24 read /stories/{slug} — no context")
    _, r1 = req(f"/api/stories/{slug}")
    print(f"  active_updates: {[u['message'][:60] for u in r1['active_updates']]}")

    print(f"F-24 read /stories/{slug} — weather=rain")
    _, r2 = req(f"/api/stories/{slug}?weather=rain")
    print(f"  active_updates ({len(r2['active_updates'])}):")
    for u in r2["active_updates"]:
        print(f"    [{u['kind']}] {u['message']}")

    print(f"F-24 read /stories/{slug} — crowd_pct=30 (quiet)")
    _, r3 = req(f"/api/stories/{slug}?crowd_pct=30")
    for u in r3["active_updates"]:
        print(f"    [{u['kind']}] {u['message']}")

    print(f"F-24 read /stories/{slug} — crowd_pct=80 (busy) → crowd banner should NOT appear")
    _, r4 = req(f"/api/stories/{slug}?crowd_pct=80")
    print(f"  active_updates: {[u['message'][:60] for u in r4['active_updates']]}")

    # F-22 personalised feed based on preferences
    print("\nF-22 personalised /stories/for-me (traveler has activities=[food-tours,photography,museums], priorities=[food,culture])")
    _, mine = req("/api/stories/for-me", token=tr_tok)
    for r in mine["stories"]:
        p = r["post"]
        print(f"  score={r['score']:>5.1f} matched={r['matched_tags']}  '{p['title'][:45]}'")

    # RBAC — traveler cannot create a story (must be a provider)
    s, err = req("/api/stories", "POST", {
        "title": "traveler tries to post",
        "body_md": "just testing #Budget",
    }, token=tr_tok)
    print(f"\ntraveler POST /api/stories -> {s} {err.get('detail') if isinstance(err, dict) else ''}")

    # Provider create -> auto tag parse + narrative score
    s, brand_new = req("/api/stories", "POST", {
        "title": "Brand-new Bali food walk with zero reviews",
        "summary": "Ubud after dark, three warungs the guides miss.",
        "body_md": "## Warung 1\n\nOpen-air satay. #Foodie #DateNight #HiddenGem\n\n## Warung 2\n\nBabi guling that runs out by 9pm.\n\n- come hungry\n- bring cash\n\nWorth the walk.",
        "city": "Bali",
    }, token=prov_tok)
    print(f"\nprovider POST /api/stories -> {s}")
    if isinstance(brand_new, dict):
        print(f"  parsed tags: {brand_new['context_tags']}")
        print(f"  narrative_quality_score: {brand_new['narrative_quality_score']}")

    # Publish
    if isinstance(brand_new, dict) and brand_new.get("id"):
        s, _ = req(f"/api/stories/{brand_new['id']}/publish", "POST", token=prov_tok)
        print(f"  publish -> {s}")


if __name__ == "__main__":
    main()
