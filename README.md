# Voyager 2.0

The maintained application is `hackthon-main/frontend` (Next.js) and `hackthon-main/backend` (FastAPI). Root npm commands delegate to that frontend; the historical root `src/` copy is not the development entry point.

## Windows setup

From `D:\rohan_proj\voyager2.0`, use one Python environment throughout. Activation and a PowerShell execution-policy change are not required:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix hackthon-main/frontend install
```

If `.venv` points to a removed Python installation, create a new environment with an installed Python instead of activating the broken one. The verified environment on this workspace is `tmp/.venv`; substitute `tmp\.venv\Scripts\python.exe` in the commands below to use it.

`requirements.txt` now works from the repository root, `hackthon-main`, or the backend folder. Always use `python -m pip` with the same interpreter that starts the backend.

## Configuration

Keep existing secret files. For a new checkout, copy `hackthon-main/backend/.env.example` to `.env` in that same backend folder and `hackthon-main/frontend/.env.local.example` to `.env.local` in that frontend folder.

- Backend: `GROQ_API_KEY` and `GROQ_MODEL=openai/gpt-oss-20b`.
- Frontend: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`. Optional server-only `BACKEND_API_URL` overrides the chatbot proxy's backend origin.
- Local database: `DATABASE_URL=sqlite:///./voyager.db` requires no hosted subscription.
- CORS must include `http://localhost:3000` and `http://127.0.0.1:3000`.

The Groq key belongs only in the backend environment, never a `NEXT_PUBLIC_*` variable. The dashboard chat and co-pilot use the same backend client; Gemini/Claude/xAI are not fallback providers.

## Start

Terminal 1, from the repository root:

```powershell
.venv\Scripts\python.exe scripts/run-backend.py --reload
```

Terminal 2, from the repository root:

```powershell
npm.cmd run dev
```

Open `http://localhost:3000/dashboard/assistant` for chat, `/copilot` for the trip planner, or `/experiences` for the catalog. API docs: `http://127.0.0.1:8000/docs`.

The launcher changes to the backend directory so its environment and SQLite paths resolve consistently. Start only one backend per port. If port 8000 is occupied or Windows-reserved, the launcher explains the issue before starting:

```powershell
.venv\Scripts\python.exe scripts/run-backend.py --port 8001 --reload
```

Then set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8001` in `hackthon-main/frontend/.env.local` and restart the frontend. Do not kill an unknown process to free a port. Stop a server you started with Ctrl+C before restarting it.

## Free usage

The default model is listed in [Groq's Free Plan limits](https://console.groq.com/docs/rate-limits). Keep the Groq organization on **Free**. API keys do not encode billing tier, and the application cannot turn paid-plan usage into free usage. It never upgrades accounts, calls paid fallback providers, uses built-in paid tools, or retries provider quota failures automatically. A 429 response asks the traveler to wait.

No new subscription, SDK or hosted database is required. Leave optional Google Maps and Amadeus credentials blank for local fallback behavior; existing travel offers are then explicitly demonstrations rather than real bookings. Actual travel purchases are not made by chat.

## Seed and checks

Only seed a disposable/local database, not production:

```powershell
cd hackthon-main/backend
..\..\.venv\Scripts\python.exe -m app.seed
..\..\.venv\Scripts\python.exe check_runtime.py
..\..\.venv\Scripts\python.exe check_experiences.py
```

Repeated seeding now handles multiple existing capacity metrics, nudges and itinerary nodes. The checks use in-memory SQLite and mocked Groq responses, not billable inference or production database writes.

```powershell
# From repository root
npm.cmd run build
```

Details of the catalog implementation: [experience handoff](hackthon-main/EXPERIENCES_IMPLEMENTATION.md).

## Verified fixes

- Seed runs three times without duplicate records or `MultipleResultsFound`; demo trip lookup is scoped to its owner.
- Root/frontend production build and targeted chatbot lint pass.
- Offline checks cover malformed input, duplicate-message prevention, authentication errors, quota errors, timeouts, invalid provider responses, and stopping planner retries after a provider failure.
- The supplied Groq key was verified without exposing it. After Free-plan confirmation, one real browser chat reply and one five-node planner draft succeeded. The browser receives no API key.
- Windows startup preflight was checked with both a free and occupied port. Temporary verification servers were stopped afterward so ports 3000 and 8000 are available for your own launch.

Optional browser regression check (backend/frontend running, Playwright already installed in the workspace's temporary test folder):

```powershell
$env:PLAYWRIGHT_MODULE = 'D:/rohan_proj/voyager2.0/tmp/browser-check/node_modules/playwright'
cd hackthon-main/frontend
node scripts/check-assistant.cjs
```

This mocks inference by default. Set `LIVE_GROQ=1` only when intentionally testing against your Groq Free-plan quota.
