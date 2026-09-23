# Voyager Backend (P1 + P2 + P3 + P4 + P5)

FastAPI service implementing all 5 modules of the PRD (F-01 through F-31).

## P1 — Context-Aware Local Experience Engine

| Feature | Endpoint |
| --- | --- |
| F-01 Multi-Factor Matching Engine | `POST /api/recommendations/match` · `POST /api/recommendations/for-me` |
| F-02 Unified Data Catalog | `GET /api/experiences` · `GET /api/experiences/{id}` |
| F-03 Real-Time Maps + Live Route Tracking | `POST /api/maps/distance` · `POST /api/maps/ping` · `GET /api/maps/ping/latest` |
| F-04 Time & Logistics Gatekeeper | *(applied inside recommendation endpoints)* |
| F-05 Itinerary-Gap Filler | `POST /api/recommendations/gap-fill` |
| F-06 Dynamic Re-Recommendation | `GET /api/realtime/stream` (SSE) |
| F-07 Provider Console & Listing Management | `POST /api/providers/me` · `POST /api/providers/me/experiences` etc. |

## P2 — Activity-Based Group Trip Ledger

| Feature | Endpoint |
| --- | --- |
| F-08 Per-Activity Participation Mapping | `POST /api/groups/{id}/expenses` with a `participants` array scoped per-line |
| F-09 Multi-Strategy Cost Splitting | Same endpoint — `split_strategy ∈ {EQUAL, EXACT_AMOUNT, PERCENTAGE, SHARE_WEIGHTED, ORGANIZER_COVERED}` |
| F-10 Reactive Ledger Recalculation | Any `PATCH /api/groups/{id}/expenses/{expense_id}` re-runs the splitter and re-persists computed shares |
| F-11 Two-Layer Accounting | `paid_to_vendors` (Asset) vs `owed_from_participation` (Liability) exposed on `MemberBalanceOut` |
| F-12 Minimum-Cash-Flow Settlement | `GET /api/groups/{id}/ledger` → `settlements` array (≤ N-1 transfers for N members) |
| F-13 Dual Projection Views | `GET /api/groups/{id}/ledger` (organizer, 403 for others) · `GET /api/groups/{id}/ledger/me` (participant scope) |

### Ledger endpoints in full

- Groups & members: `POST /api/groups` · `GET /api/groups` · `GET|PATCH|DELETE /api/groups/{id}` · `POST /api/groups/{id}/members` · `DELETE /api/groups/{id}/members/{member_id}`
- Expenses: `POST|GET /api/groups/{id}/expenses` · `PATCH|DELETE /api/groups/{id}/expenses/{expense_id}`
- Peer reimbursements: `POST|GET /api/groups/{id}/reimbursements` · `DELETE /api/groups/{id}/reimbursements/{reimbursement_id}`
- Ledger projections: `GET /api/groups/{id}/ledger` · `GET /api/groups/{id}/ledger/me`

## P3 — Capacity & Crowd Command Center

| Feature | Endpoint |
| --- | --- |
| F-14 Consolidated Capacity Dashboard | `GET /api/operator/dashboard` (operator-only; heatmap + forecasts + alerts + balancer) |
| F-15 Predictive Capacity Forecasting | `GET /api/capacity/forecasts` — linear/exp trend + `APPROACHING_SATURATION` when 100% crossed within 60 min |
| F-16 Zone Demand Balancer | `GET /api/capacity/balancer` — triggers at 85% density, picks closest city-local zone below 60% within 8 km |
| F-17 Event Schedule-Driven Modeling | `POST /api/zones/{id}/events` then forecasts auto-apply +25% pressure to zones with events ending within 30 min |
| F-18 Event Staggering & Route Optimizer | `POST /api/events/{id}/stagger` returns time-banded departure windows |
| F-19 Role-Based Dual UI | Attendee: `GET /api/capacity/for-attendee?zone_id=X` · Operator: `GET /api/operator/dashboard` (403 for non-operators) |
| F-20 Incentive-Driven Nudge System | `POST /api/nudges` seeds pool; balancer + attendee endpoints attach best-match nudge via `NudgeIssuance` audit rows |

### Capacity endpoints in full

- Zones: `POST|GET /api/zones` · `PATCH|DELETE /api/zones/{id}`
- Metric ingestion: `POST /api/capacity/metrics` (single) · `POST /api/capacity/metrics/batch` (batched — designed for NFR 5,000/sec/zone target)
- Events: `POST|GET /api/zones/{id}/events`
- Nudges: `POST|GET /api/nudges`
- Analytics: `GET /api/capacity/densities` · `GET /api/capacity/forecasts` · `GET /api/capacity/balancer` · `POST /api/events/{id}/stagger`
- Dual-role views: `GET /api/operator/dashboard` · `GET /api/capacity/for-attendee?zone_id=X`

## P4 — Editorial & Narrative Discovery

| Feature | Endpoint |
| --- | --- |
| F-21 Structured Story Post Format | `StoryPost` model + `POST /api/stories` — editorial markdown body plus first-class filter fields (`context_tags`, `city`, `experience_id`, `narrative_quality_score`) |
| F-22 Editorial Local Business Promotion | `GET /api/stories` + `GET /api/stories/for-me` — ranker uses only `narrative_quality_score`, tag match, and freshness (no review counts) |
| F-23 Natural-Language Context Tags | `GET /api/context-tags` (registry) · `GET /api/stories?tag=Budget` (filter) · every write auto-parses `#Tag` mentions from `body_md` |
| F-24 In-Post Adaptive Updates | `POST /api/stories/{id}/updates` (author) · `GET /api/stories/{slug}?weather=rain&crowd_pct=30` (reader — server resolves matching banners) |

### Editorial endpoints in full

- Registry: `GET /api/context-tags`
- Feed: `GET /api/stories` (public, sortable via `?tag=` or `?city=`) · `GET /api/stories/for-me` (personalised against caller preferences)
- Read: `GET /api/stories/{slug}` — accepts `?weather=`, `?temperature_c=`, `?hour_utc=`, `?crowd_pct=` and returns matching `active_updates`
- Provider writes: `POST /api/stories` · `PATCH /api/stories/{id}` · `POST /api/stories/{id}/publish` · `DELETE /api/stories/{id}`
- Adaptive updates: `POST /api/stories/{id}/updates` · `DELETE /api/stories/{id}/updates/{update_id}`

## P5 — Graph-Based Dependency & Recovery Engine

| Feature | Endpoint |
| --- | --- |
| F-25 Itinerary Dependency Graph Model | `ItineraryNode` + `ItineraryEdge` tables · `GET /api/itineraries/{id}/graph` · CRUD on nodes/edges (cycle-guarded) |
| F-26 Automated Ripple-Effect Impact | `GET /api/itineraries/{id}/impact` — BFS from all active disruptions |
| F-27 Tradeoff-Scored Recovery | `POST /api/itineraries/{id}/recovery` — returns three plans (Fastest / Cheapest / Least Impact) with `Penalty = w_cost·ΔCost + w_time·ΔTime + w_impact·NodesModified` |
| F-28 Policy-Aware Rule Engine | Every `RefundClass` (fully / partial / non-refundable) feeds into per-action `monetary_penalty` used by the recovery scorer |
| F-29 Interactive Graph Rewriting | `POST /api/itineraries/{id}/recovery/{plan_id}/apply` — shifts / modifies / cancels / drops nodes in one transaction, marks the plan applied, returns the rewritten graph |
| F-30 Proactive Buffer & Risk Flagging | `GET /api/itineraries/{id}/risks` (default safety threshold: 30 min) · `POST /api/itineraries/{id}/risks/apply` persists AT_RISK status on nodes |
| F-31 Simultaneous Multi-Disruption | `POST /api/itineraries/{id}/disruptions` accepts an array — a single traversal handles the union of downstream subtrees, no infinite loops (visited set in `DependencyGraph.downstream`) |

### Graph endpoints in full

- Structure: `GET /api/itineraries/{id}/graph` · `POST /api/itineraries/{id}/nodes` · `PATCH /api/itineraries/{id}/nodes/{node_id}` · `DELETE /api/itineraries/{id}/nodes/{node_id}` · `POST /api/itineraries/{id}/edges` (cycle-guarded) · `DELETE /api/itineraries/{id}/edges/{edge_id}`
- Risk: `GET /api/itineraries/{id}/risks` · `POST /api/itineraries/{id}/risks/apply`
- Disruption + impact: `POST /api/itineraries/{id}/disruptions` · `GET /api/itineraries/{id}/impact`
- Recovery: `POST /api/itineraries/{id}/recovery` · `POST /api/itineraries/{id}/recovery/{plan_id}/apply`

Auth is JWT (bcrypt-hashed passwords, 24h token TTL by default).

## Prerequisites

- Python 3.11+
- pip

## Setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env    # (macOS/Linux: cp .env.example .env)
```

Generate a real JWT secret and paste it into `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Seed the demo data

```bash
python -m app.seed
```

Creates:

- traveler account — `traveler@voyager.dev` / `voyager123`
- provider account — `provider@voyager.dev` / `voyager123`
- operator account — `operator@voyager.dev` / `voyager123` (P3)
- one provider profile (Local Guides Co.)
- ~25 experiences across **Bali, Kyoto, Paris, Mumbai** with realistic operating hours
- 4 Kyoto zones (Gion, Arashiyama, Higashiyama, Kyoto Sta.) with a 60-min rising-density time series
- One concert in Gion ending in ~20 min (F-17 pressure trigger)
- 3 nudges (Arashiyama discount, generic priority pass, badge)
- 3 story posts (Gion in rain, Arashiyama on ₹700, Mumbai after sunset) with parseable `#Tags` in the body and 2 adaptive updates on the Gion story (weather=rain, crowd_lte=50)
- A "Kyoto Weekend" trip itinerary with a 7-node dependency graph (flight → transfer → hotel → activity → optional walk → hotel checkout → return flight), including an intentionally tight 25-min airport transfer buffer so F-30 lights up immediately

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- Interactive docs: <http://localhost:8000/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>
- Health check: <http://localhost:8000/health>

The database is `voyager.db` in `backend/` (SQLite). Tables are auto-created
on startup, so no migration step is required for local dev.

## Testing the matching engine (curl)

```bash
# Get a token
curl -X POST http://localhost:8000/api/auth/login \
  -H "content-type: application/json" \
  -d '{"email":"traveler@voyager.dev","password":"voyager123"}'

# Public match — 3-hour window starting now, near Kyoto centre
curl -X POST http://localhost:8000/api/recommendations/match \
  -H "content-type: application/json" \
  -d '{
    "lat": 35.0116,
    "lng": 135.7681,
    "at": "'"$(date -u +%FT%TZ)"'",
    "window_end": "'"$(date -u -d '+3 hours' +%FT%TZ)"'",
    "interests": ["food-tours", "photography"],
    "priorities": ["food"],
    "budget_max": 5000,
    "city": "Kyoto"
  }'
```

## Architecture at a glance

```
app/
  main.py                 FastAPI app + router registration
  config.py               pydantic-settings (env-driven)
  database.py             SQLAlchemy engine, session, Base
  security.py             bcrypt + JWT helpers
  deps.py                 auth dependencies (get_current_user, require_provider)

  models/                 SQLAlchemy 2.0 ORM
    user.py               User + UserRole enum
    provider.py           Provider (1:1 with user)
    experience.py         Experience + OperatingHour + ExperienceCategory enum (F-02)
    itinerary.py          Itinerary + ItinerarySlot
    location.py           UserLocationPing (F-03 tracking)
    group.py              Group + GroupMember + GroupMemberRole enum (P2)
    ledger.py             Expense + ExpenseParticipant + PeerReimbursement + SplitStrategy enum (P2)
    capacity.py           Zone + CapacityMetric + ZoneEvent + Nudge + NudgeIssuance (P3)
    editorial.py          StoryPost + StoryUpdate + StoryUpdateKind (P4)
    graph.py              ItineraryNode + ItineraryEdge + Disruption + RecoveryPlan + enums (P5)

  schemas/                Pydantic request/response models

  routers/
    auth.py               /api/auth/* — register, login, me, preferences
    providers.py          /api/providers/* — become-a-provider, my profile
    experiences.py        /api/experiences/* — public catalog + provider CRUD (F-02, F-07)
    recommendations.py    /api/recommendations/* — match, for-me, gap-fill (F-01, F-04, F-05)
    itineraries.py        /api/itineraries/* — trips + slots
    maps.py               /api/maps/* — distance + live pings (F-03)
    realtime.py           /api/realtime/stream — SSE bus (F-06)
    groups.py             /api/groups/* — group + membership CRUD (P2)
    expenses.py           /api/groups/{id}/expenses & reimbursements (P2 — F-08/F-09/F-10)
    ledger.py             /api/groups/{id}/ledger[/me] — projections (P2 — F-11/F-12/F-13)
    capacity.py           /api/{zones,capacity,nudges,operator,events}/* — all P3 endpoints
    stories.py            /api/stories/* + /api/context-tags — P4 (F-21/F-22/F-23/F-24)
    graph.py              /api/itineraries/{id}/{graph,nodes,edges,risks,disruptions,impact,recovery} — all P5

  services/
    matching.py           Scoring formula + gatekeeper (F-01, F-04)
    logistics.py          Haversine + operating-hour utilities
    events.py             In-process pub/sub feeding the SSE stream (F-06)
    ledger.py             Split strategies + two-layer accounting + min-cashflow solver (P2)
    forecasting.py        Linear-regression saturation projection + event pressure + balancer (P3 — F-15/F-16/F-17)
    staggering.py         Departure band generator (P3 — F-18)
    nudges.py             Nudge picker (P3 — F-20)
    context_tags.py       #Tag registry + parser + SQL filter builders (P4 — F-23)
    editorial.py          Narrative quality scorer + feed ranker + adaptive update resolver (P4 — F-22/F-24)
    graph.py              DependencyGraph: adjacency, cycle guard, downstream BFS (P5 — F-25/F-26/F-31)
    risk.py               Buffer threshold flagging (P5 — F-30)
    policy.py             Refund-class-aware penalty scoring (P5 — F-28)
    recovery.py           Three-strategy plan generator + multi-root handling (P5 — F-27/F-31)
    rewrite.py            Graph mutator ("Apply Fix") + status reset (P5 — F-29)
    slug.py

  seed.py                 Idempotent demo seeder
  smoke_p2.py             Ad-hoc P2 end-to-end verification script
  smoke_p3.py             Ad-hoc P3 end-to-end verification script
  smoke_p4.py             Ad-hoc P4 end-to-end verification script
  smoke_p5.py             Ad-hoc P5 end-to-end verification script
```

## P2 ledger recap (`services/ledger.py`)

Three pure functions:

1. **`compute_splits`** — implements F-09 across the five supported strategies. Rounding remainders (e.g. `1000 / 3 = 333.33 × 3 = 999.99`) are absorbed onto the payer's line so the sum of participant shares always equals the total to the cent.
2. **`compute_balances`** — F-11 two-layer accounting. Returns per-member `paid_to_vendors`, `owed_from_participation`, `reimbursements_sent`, `reimbursements_received`, and derived `net_balance`.
3. **`min_cashflow_settlements`** — F-12 greedy netting. Repeatedly settles the largest debtor against the largest creditor; guaranteed ≤ N-1 transfers for N members.

Because *every* create/update path calls `compute_splits` and re-persists `ExpenseParticipant.computed_amount_base`, F-10 (reactive recalc) is a compile-time guarantee, not an eventual-consistency promise.

## Scoring recap (`services/matching.py`)

Per PRD formula:

```
Score = w1 * S_interest + w2 * S_logistics + w3 * S_budget + w4 * S_fit
```

Defaults: `w1 = 0.40, w2 = 0.25, w3 = 0.20, w4 = 0.15`.

Key invariant (F-01 acceptance): `S_logistics = 0` when `transit_mins +
duration_mins > window_mins`, and the gatekeeper (F-04) hard-filters those
rows before scoring — so a 90-minute free window returns zero experiences
whose total time exceeds 90 minutes.

## P3 recap (`services/forecasting.py`, `staggering.py`, `nudges.py`)

- **`latest_density_by_zone`** collapses raw `CapacityMetric` rows into per-zone rollups — one entry per source_kind for the heatmap tooltip, worst-case density surfaced as the headline number (F-14).
- **`project_saturation`** runs least-squares linear regression over the last 90 min of samples. Flags `APPROACHING_SATURATION` when the trendline hits 100% within 60 min. Verified: seed populates Gion at ~92% climbing at 0.79%/min → status `APPROACHING_SATURATION`, `minutes_to_saturation ≈ 10.2` (F-15).
- **`apply_event_pressure`** stacks a +25% surcharge on the 60-min projection for zones with an event ending within 30 min — realises F-17's "elevate metrics 30 minutes prior to known event conclusion" verbatim.
- **`nearby_low_density_zones`** triggers at 85% density (F-16 acceptance), searches same-city zones under 60% density within 8 km, picks the closest.
- **`generate_staggered_departures`** produces bands centred on `event_end_at`, capped at `max_per_band` (F-18).
- **`pick_nudge_for_zone`** ranks the active pool: zone-targeted first, then PRIORITY_PASS > DISCOUNT > BADGE (F-20). Every issuance logs a `NudgeIssuance` audit row.

## P4 recap (`services/editorial.py`, `context_tags.py`)

- **`parse_context_tags`** pulls `#Tag` mentions out of markdown so authors don't maintain a parallel metadata block — the same word appears in the prose and as a queryable filter (F-21 spec: "displays full editorial text while maintaining standard JSON metadata fields for background filtering").
- **`narrative_quality_score`** is a 0..100 heuristic over title/summary/body length + cover image + tag count + formatting cues. Deterministic so authors can predict their score.
- **`rank_stories_for_reader`** is `w_quality * quality + w_match * preference_match + w_freshness * decay`. Crucially, no review-count term appears anywhere — that's what makes F-22 acceptance (zero-review new listings can rise to the top) a compile-time property rather than a policy hope.
- **`resolve_active_updates`** matches each `StoryUpdate.condition` against a `RuntimeContext` (weather, hour, crowd_pct, temperature) supplied by the client. Unknown conditions fail closed — an update that references data the client didn't send is silently withheld rather than surfaced spuriously.
- **`services/context_tags.py`** owns the tag registry and returns SQLAlchemy `WHERE` expressions (so tag filters can compose with any other query).

## P5 recap (`services/graph.py`, `risk.py`, `policy.py`, `recovery.py`, `rewrite.py`)

- **`DependencyGraph`** builds adjacency maps + implements `would_create_cycle`, `downstream` (BFS with visited set — safe for the F-31 multi-root case), and `topological_order`.
- **`assess_buffers`** walks every non-optional edge and flags any gap below its `min_buffer_mins` (default 30 min). Severity escalates to `critical` if the actual gap is negative (target starts before source ends) or less than half the requirement.
- **`policy.evaluate_*`** returns `PolicyEvaluation` for cancellation / modification / shift given a node's `RefundClass` + `change_fee`. Non-refundable modifications intentionally take a 30% sunk-cost hit on top of the change fee so the scorer prefers touching refundable inventory.
- **`generate_recovery_plans`** produces **three** ranked drafts — Fastest, Cheapest, Least Impact — using distinct weight profiles so the "at least two distinct options" acceptance (F-27) becomes structural rather than accidental.
- **`apply_plan`** replays the persisted `RecoveryPlan.actions` list against the graph in one transaction, clears IMPACTED / DISRUPTED statuses when the fix zeroes them out, and marks the plan `is_applied=True` so a repeat call 409s.

## Live services bus

`services/events.py` publishes:
`ledger:changed` / `group:changed` / `capacity:changed` / `story:changed`
/ `catalog:changed` / `itinerary:changed` / `location:drift` /
`graph:changed`.

Any frontend listening to `GET /api/realtime/stream` (SSE) receives these
in real time — that's the substrate the F-06 dynamic re-recommendation
engine + the F-14 operator dashboard both use to auto-refresh.

## Verifying P2 / P3 / P4 / P5 quickly

```bash
uvicorn app.main:app --port 8765     # in one terminal

python -X utf8 smoke_p2.py           # in another — walks ledger flow
python -X utf8 smoke_p3.py           # walks capacity flow
python -X utf8 smoke_p4.py           # walks editorial flow
python -X utf8 smoke_p5.py           # walks dependency graph + recovery flow
```

`smoke_p2.py` prints EQUAL/PERCENTAGE/WEIGHTED/ORGANIZER_COVERED splits,
EXACT_AMOUNT validation failure, organizer ledger view with computed
min-cashflow settlements, 403 for a non-organizer, participant scoped
view, and reactive recalc after PATCH.

`smoke_p3.py` prints RBAC for zones + operator dashboard, per-zone
density/forecast/slope/minutes-to-saturation, verified F-15 acceptance
(Gion `APPROACHING_SATURATION`, ~10 min to saturation), F-17 event
pressure applied, F-16 balancer recommendation with attached F-20 nudge,
F-18 staggering plan with three 500-headcount bands, F-19 attendee view
showing crowd-avoidance tip + alternative + nudge, plus a batch
ingestion sanity check.

`smoke_p4.py` prints the F-23 context-tag registry, the F-22 ranked feed
(showing a fresh post beating an older one on freshness alone with no
review count involved), F-23 `?tag=RainyDayFriendly` and `?tag=Budget`
filters returning the correct posts, F-24 read-time update resolution
(weather=rain surfaces a WEATHER banner, crowd_pct=30 surfaces a CROWD
banner, crowd_pct=80 correctly suppresses it), RBAC (traveler POST
`/api/stories` → 403), and a provider create-then-publish round trip
that auto-parses `#Foodie #DateNight #HiddenGem` from the body markdown
and computes a fresh narrative quality score.

`smoke_p5.py` prints the F-25 seeded DAG (7 nodes, 6 edges), F-30 buffer
risk detected on the tight 25-min flight → transfer edge (< 45 required),
F-26 + F-31 multi-root disruption declared (flight +120 min AND hotel
+60 min) with 5 downstream nodes correctly marked IMPACTED, F-27
recovery generation returning three distinct plans (Fastest: 7 nodes /
₹22,100 / +120 min · Cheapest: 2 nodes / ₹0 / +240 min · Least Impact:
2 nodes / ₹0 / +145 min), F-29 apply of the fastest plan leaving zero
residual IMPACTED / DISRUPTED nodes, and a repeat-apply attempt correctly
returning 409.
