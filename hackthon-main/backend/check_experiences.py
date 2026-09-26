"""Run: python check_experiences.py. Uses only an isolated in-memory database."""
import os

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.config import Settings
from app.database import Base, get_db
from app.models.experience import Experience, ExperienceCategory, OperatingHour
from app.routers.experiences import router
from app.schemas.experience import ExperienceUpdate
from pydantic import ValidationError


def check():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for i, (name, cost, duration, category, attrs) in enumerate([
            ("River walk", 100, 120, "OUTDOOR", {"rating": 4.8, "free_cancellation": True, "popularity_score": 80}),
            ("Museum", 300, 180, "CULTURE", {"rating": 3.5, "popularity_score": 90}),
            ("Cooking", 200, 360, "FOOD", {"recommendation_score": 92}),
            ("Full day", 400, 720, "OUTDOOR", {}),
            ("Two days", 600, 1440, "OUTDOOR", {}),
        ]):
            exp = Experience(id=str(i), slug=name.lower().replace(" ", "-"), title=name,
                city="Paris", category=ExperienceCategory(category), base_cost=cost,
                duration_mins=duration, lat=48.8, lng=2.3, attributes=attrs,
                description="A local experience")
            exp.hours = [OperatingHour(day_of_week=0, open_time="09:00", close_time="18:00")]
            db.add(exp)
        db.add(Experience(id="inactive", slug="inactive", title="Hidden", is_active=False,
                          city="Paris", category=ExperienceCategory.CULTURE, lat=0, lng=0))
        db.commit()

    def session():
        with Session(engine) as db:
            yield db

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = session
    with TestClient(app) as client:
        def rows(query=""):
            response = client.get("/api/experiences" + query)
            assert response.status_code == 200, response.text
            return response.json()

        assert len(rows()) == 5
        assert rows()[0]["id"] == "1"  # supplied popularity, missing scores last
        assert rows("?sort=recommended")[0]["id"] == "2"
        assert [e["base_cost"] for e in rows("?sort=price_asc")] == [100, 200, 300, 400, 600]
        assert rows("?q=Paris&search=river&freeCancellation=true&rating=4")[0]["id"] == "0"
        assert len(rows("?category=OUTDOOR&category=CULTURE")) == 4
        assert rows("?minPrice=150&maxPrice=250")[0]["id"] == "2"
        assert len(rows("?date=2026-10-05")) == 5
        assert rows("?date=2026-10-06") == []
        for duration, expected in [("short", "0"), ("half", "1"), ("full", "2"), ("day", "3"), ("multi", "4")]:
            assert rows(f"?duration={duration}")[0]["id"] == expected
        assert rows("?city=Unknown") == []
        assert len(rows("?offset=4&limit=2")) == 1
        assert client.get("/api/experiences?minPrice=200&maxPrice=100").status_code == 422
        assert client.get("/api/experiences?limit=-1").status_code == 422
        assert client.get("/api/experiences?date=bad").status_code == 422
        assert client.get("/api/experiences?sort=bad").status_code == 422
        assert client.get("/api/experiences/inactive").status_code == 404
        assert client.get("/api/experiences/missing").status_code == 404
        assert client.get("/api/experiences/0").json()["title"] == "River walk"
        facets = client.get("/api/experiences/facets?city=Paris").json()
        assert facets["prices"] == [{"currency": "INR", "min": 100.0, "max": 600.0}]
        assert sum(c["count"] for c in facets["categories"]) == 5
        assert client.get("/api/experiences/facets?city=Missing").json()["prices"] == []

    settings = Settings(_env_file=None, SECRET_KEY="test-secret", ALGORITHM="HS256",
                        ACCESS_TOKEN_EXPIRE_MINUTES=400, cors_origins='["http://localhost:3000"]')
    assert settings.jwt_secret == "test-secret" and settings.jwt_expires_minutes == 400
    assert settings.cors_origins == ["http://localhost:3000"]
    assert Settings(_env_file=None, cors_origins="http://localhost:3000,http://localhost:5173").cors_origins == ["http://localhost:3000", "http://localhost:5173"]
    assert Settings._postgres_driver("postgresql://user:password@localhost/db").startswith("postgresql+psycopg://")
    for attrs in ({"rating": "4.5"}, {"rating": 8}, {"free_cancellation": "false"}):
        try:
            ExperienceUpdate(attributes=attrs)
        except ValidationError:
            pass
        else:
            raise AssertionError("Invalid catalog metadata was accepted")
    print("PASS: catalog filters, date schedules, sorting, pagination, facets, detail visibility and environment aliases")


if __name__ == "__main__":
    check()
