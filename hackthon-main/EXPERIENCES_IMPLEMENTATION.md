# Voyager experiences — implementation handoff

The existing Next.js application now exposes `/experiences` and `/experience/[id]`, using the existing FastAPI/SQLAlchemy catalog. The existing Discover and landing pages remain intact. This repository is Voyager, not the separate GoFlexi architecture described in the supplied reference document.

## Delivered behavior

- Destination/activity search and date search call the backend. Search, categories, price, currency, duration, rating, cancellation, sort and pagination remain in the URL.
- Catalog-driven category labels/counts and per-currency price ranges. Multiple categories/durations use repeated query parameters.
- Three desktop columns, two tablet columns, one mobile column. Mobile filters use native `<dialog>` with modal focus handling and Escape-to-close.
- Removable filter chips, clear-all, pagination, skeletons, empty state and retryable errors.
- Details fetch by ID; inactive/missing records return 404. Metadata renders only when supplied, with honest missing-information copy.
- Reusable Next.js Back button on listings, details, destination pages, planner, booking/confirmation and dashboard pages including profile. It uses available navigation history and a contextual fallback.
- Existing navbar Experiences link now opens the new catalog. Non-landing navigation collapses before tablet controls clip.
- PostgreSQL psycopg URL normalization, supplied JWT environment-name aliases, and both JSON-array/CSV CORS parsing. Existing authentication remains in place.

## Files

All paths below are relative to **`D:/rohan_proj/voyager2.0/hackthon-main/`**.

Created:

```text
EXPERIENCES_IMPLEMENTATION.md
backend/check_experiences.py
frontend/.env.local.example
frontend/.impeccable/experiences.md
frontend/scripts/check-experiences.cjs
frontend/src/app/experiences/page.tsx
frontend/src/app/experiences/experiences.css
frontend/src/app/experience/[id]/page.tsx
frontend/src/components/experiences/experience-list.tsx
frontend/src/components/experiences/experience-card.tsx
frontend/src/components/experiences/experience-details.tsx
frontend/src/components/ui/back-button.tsx
```

Modified:

```text
backend/.env.example
backend/app/config.py
backend/app/routers/experiences.py
backend/app/schemas/experience.py
backend/app/seed.py
backend/requirements.txt
frontend/.gitignore
frontend/src/app/booking/page.tsx
frontend/src/app/booking/confirmation/page.tsx
frontend/src/app/dashboard/layout.tsx
frontend/src/app/destination/[slug]/page.tsx
frontend/src/app/planner/page.tsx
frontend/src/components/layout/navbar.tsx
frontend/src/components/copilot/super-trip-globe.tsx
frontend/src/lib/api.ts
```

The globe change removes an unsupported MapLibre constructor option and calls its supported `setProjection` method after load, resolving the pre-existing TypeScript build failure without changing the intended globe projection.

Review artifacts created:

```text
frontend/.impeccable/review/experiences/desktop.png
frontend/.impeccable/review/experiences/tablet.png
frontend/.impeccable/review/experiences/mobile.png
frontend/.impeccable/review/experiences/desktop-detail.png
frontend/.impeccable/review/experiences/tablet-detail.png
frontend/.impeccable/review/experiences/mobile-detail.png
```

Disposable verification dependencies and a copy of the local SQLite catalog live in the ignored workspace-root `tmp/` directory. Existing `.serena/` content and existing credential files were not changed.

## Backend endpoints

| Endpoint | Use |
| --- | --- |
| `GET /api/experiences` | Existing public catalog, extended filters/sorting/pagination. Response remains an array for existing callers. |
| `GET /api/experiences/facets` | New companion endpoint on the same router: categories/counts and price bounds per currency, scoped by `city`, `q`, `date`. |
| `GET /api/experiences/{id}` | Existing public detail endpoint, now hides inactive records. |
| `POST /api/providers/me/experiences` | Existing authenticated provider creation; unchanged route. |
| `PATCH /api/providers/me/experiences/{id}` | Existing authenticated provider editing; now validates numeric and boolean catalog metadata. |

Example search:

```http
GET /api/experiences?city=Paris&date=2026-10-05&category=OUTDOOR&category=CULTURE&minPrice=500&maxPrice=5000&currency=INR&duration=short&rating=4&freeCancellation=true&sort=price_asc&limit=24&offset=0
```

`q` searches title, description and city; optional `search` further searches title/description. Supported sorts: `popularity`, `price_asc`, `price_desc`, `rating`, `recommended`. Missing popularity/recommendation scores sort last, with stable title/ID tie-breaking. Price sorting groups currencies; no invented exchange rate is applied.

Durations use disjoint minute ranges: `short` [0,180), `half` [180,360), `full` [360,720), `day` [720,1440), `multi` [1440,infinity). Dates filter the existing weekly operating schedule; they do **not** prove live booking inventory. Records without hours have no schedule restriction.

## Data contract and sample data

No new database tables or migrations are required. Existing `attributes` JSON supplies optional details. A representative **sample** response item is:

```json
{
  "id": "sample-experience-id",
  "slug": "sample-river-walk",
  "provider_id": null,
  "title": "Sample river walk",
  "description": "Illustrative activity for a development catalog.",
  "category": "OUTDOOR",
  "base_cost": 1200,
  "currency": "INR",
  "duration_mins": 120,
  "lat": 48.8566,
  "lng": 2.3522,
  "city": "Paris",
  "country": "France",
  "address": null,
  "capacity_max": 100,
  "seats_available": 100,
  "attributes": { "is_sample": true },
  "interest_tags": ["photography"],
  "is_active": true,
  "hours": [],
  "created_at": "2026-09-27T00:00:00Z",
  "updated_at": "2026-09-27T00:00:00Z"
}
```

Optional supported attribute keys:

| Keys | Expected values |
| --- | --- |
| `image_url`, `gallery` | HTTPS image URL; array of HTTPS image URLs. Missing/failed images show a placeholder. |
| `rating`, `review_count`, `reviews` | Numeric 0–5 rating, nonnegative review count, array of written review strings. |
| `original_price` | Nonnegative number in the experience currency; savings render only above `base_cost`. |
| `free_cancellation`, `instant_confirmation` | Booleans; badges appear only for `true`. |
| `cancellation_policy`, `meeting_point` | Provider-supplied text. |
| `highlights`, `included`, `excluded` | Arrays of strings. |
| `available_dates`, `time_slots` | Arrays of date/time strings supplied by the provider. |
| `booking_url` | HTTPS provider booking link. User reconfirms selections on that site. |
| `popularity_score`, `recommendation_score`, `match_reasons` | Backend-supplied scores and reasons; recommendation score is 0–100. No random recommendation logic. |
| `is_sample` | Boolean. Shows sample labeling and disables provider booking. |

The repository already has a separate `app.seed` script. It now marks its inserted and matching existing sample records with `is_sample: true`; it never runs automatically. Run it only against a disposable/local database because it also creates demo users and other demonstration entities. Do not seed the supplied Neon database. Existing unmarked seed records acquire labels when that explicit local seed command is rerun.

Catalog images, descriptions, reviews and booking links were absent in the local records used for verification. No stock image was substituted for an actual activity, and no ratings, cancellation policies, discounts or match scores were fabricated.

## Environment

Backend reads `backend/.env`; frontend reads `frontend/.env.local`.

| Variable | Configuration |
| --- | --- |
| `DATABASE_URL` | Existing SQLite URL for local development, or `postgresql://USER:PASSWORD@HOST/neondb?sslmode=require&channel_binding=require`. Psycopg is installed by requirements. |
| `JWT_SECRET` / `SECRET_KEY` | A strong random secret for authenticated provider APIs. Replace placeholder values. |
| `JWT_ALGORITHM` / `ALGORITHM` | `HS256` for the existing application. |
| `JWT_EXPIRES_MINUTES` / `ACCESS_TOKEN_EXPIRE_MINUTES` | Positive integer; supplied value `400` is supported. |
| `CORS_ORIGINS` | CSV or JSON array. Include `http://localhost:3000` and `http://127.0.0.1:3000` for this Next.js app. |
| `NEXT_PUBLIC_API_URL` | Backend origin, e.g. `http://localhost:8000`, without `/api`. |

Canonical `JWT_*` variables take precedence over aliases. Public experience endpoints do not require authentication. The supplied RapidAPI and OpenTripMap keys belong to the separate reference architecture and are not used by this database-backed catalog; no unnecessary provider integrations or replacement authentication dependencies were introduced. Existing secret files were preserved and no credential values are included here.

## Run locally (PowerShell)

From the workspace root, create a working environment if needed:

```powershell
py -3.13 -m venv tmp/.venv
tmp/.venv/Scripts/python.exe -m pip install -r hackthon-main/backend/requirements.txt
cd hackthon-main/backend
# Keep the existing .env; use .env.example only when creating a new configuration.
../../tmp/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The checked-in folder's pre-existing `.venv` points to a missing Python 3.10 installation on this machine. Verification used a working Python 3.12 environment in `tmp/.venv` instead. The existing application initializes missing tables at startup; choose the intended database before starting it.

Frontend, in another terminal:

```powershell
cd D:/rohan_proj/voyager2.0/hackthon-main/frontend
npm.cmd install
# Set NEXT_PUBLIC_API_URL in .env.local if the default backend origin differs.
npm.cmd run dev
```

Open `http://localhost:3000/experiences`; backend API docs are at `http://127.0.0.1:8000/docs`.

For a fresh local demonstration database only:

```powershell
cd D:/rohan_proj/voyager2.0/hackthon-main/backend
$env:DATABASE_URL = 'sqlite:///./voyager-demo.db'
../../tmp/.venv/Scripts/python.exe -m app.seed
../../tmp/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Verification and complete flow

Backend check (isolated in-memory SQLite; never connects to Neon):

```powershell
cd D:/rohan_proj/voyager2.0/hackthon-main/backend
../../tmp/.venv/Scripts/python.exe check_experiences.py
```

Frontend production verification:

```powershell
cd D:/rohan_proj/voyager2.0/hackthon-main/frontend
npm.cmd run build
```

Browser check requires a local backend with the existing demo catalog, the frontend, installed Edge and Playwright. Install Playwright into a disposable workspace directory, not the application dependencies:

```powershell
cd D:/rohan_proj/voyager2.0
npm.cmd install --prefix tmp/browser-check --no-package-lock playwright
$env:PLAYWRIGHT_MODULE = 'D:/rohan_proj/voyager2.0/tmp/browser-check/node_modules/playwright'
cd hackthon-main/frontend
node scripts/check-experiences.cjs
```

Manual flow:

1. Open Experiences from Voyager navigation; search `Paris` and optionally a date.
2. Select one or more categories, price bounds, duration, minimum rating and cancellation. Missing rating/cancellation data correctly excludes an activity from those filters.
3. Change sort; remove chips individually and use Clear all. Reload the URL to verify state persists.
4. Open an activity. Verify title, price, duration and details match `/api/experiences/{id}`. Change traveler count to update the estimate. No reservation is created by this control.
5. Go Back; verify the listing's search/filters persist. Open the listing in a fresh tab and check the Discover fallback.
6. At mobile width, open Filters, navigate by keyboard, change a filter, close with Escape or Show results, and verify results.
7. Search an unknown destination for the empty state. Stop the backend for the error state, restart it and choose Retry. Open an invalid ID for the unavailable-detail state.

Results: backend checks pass; desktop/tablet/mobile browser flow checks pass; production build passes. Targeted lint for new experience files passes. Repository-wide lint still has 32 pre-existing errors in unrelated/previously existing code (including React effect patterns and old scripts); they are not suppressed. The independent screenshot reviewer scored the tablet-navigation correction resolved. The landing entry still loads in the browser check. No live Neon connection, remote database mutation, real provider booking or real payment was tested.

## Known integration limits

- Dates represent existing operating schedules, not date-specific inventory. The existing trip booking/payment flow is not an activity checkout; no fake reservation flow was added.
- Without `booking_url`, details explicitly show online booking unavailable. The external-provider CTA does not transmit traveler/date selections; its copy asks the user to reconfirm them.
- The recommendation engine can supply the documented score/reasons through the existing metadata contract; this page does not invent or run a second scoring model.
- No reference screenshot was attached, so composition follows the detailed written brief and existing Voyager identity.
