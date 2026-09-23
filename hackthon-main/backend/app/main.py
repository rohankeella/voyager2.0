from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.database import Base, engine
from app import models  # noqa: F401 — register mappers
from app.routers import (
    auth,
    capacity,
    experiences,
    expenses,
    graph,
    groups,
    itineraries,
    ledger,
    maps,
    providers,
    realtime,
    recommendations,
    stories,
    travel,
)


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Prisma-style "push schema" — safe for hackathon; for prod-shaped
    # deployments we'd flip on Alembic.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Voyager Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(experiences.router)
app.include_router(experiences.provider_router)
app.include_router(recommendations.router)
app.include_router(itineraries.router)
app.include_router(maps.router)
app.include_router(travel.router)
app.include_router(realtime.router)
# P2 — Activity-Based Group Trip Ledger
app.include_router(groups.router)
app.include_router(expenses.router)
app.include_router(ledger.router)
# P3 — Capacity & Crowd Command Center
app.include_router(capacity.router)
# P4 — Editorial & Narrative Discovery
app.include_router(stories.router)
# P5 — Dependency Graph & Recovery Engine
app.include_router(graph.router)
