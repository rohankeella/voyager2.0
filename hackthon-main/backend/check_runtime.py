"""Offline regression checks: python check_runtime.py. No provider calls or real DB writes."""
import contextlib
import io
import json
import os
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GROQ_API_KEY"] = "test-key-not-real"

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import seed
from app.database import Base, SessionLocal
from app.models.user import User, UserRole
from app.models.itinerary import Itinerary
from app.routers.assistant import router
from app.services.groq import complete
from app.agents.planner import plan_node


def check():
    with contextlib.redirect_stdout(io.StringIO()):
        seed.seed()
    def counts():
        with SessionLocal() as db:
            return {name: db.scalar(select(func.count()).select_from(table)) for name, table in Base.metadata.tables.items()}
    first = counts()
    assert first["nudges"] == 3 and first["itinerary_nodes"] == 7
    with contextlib.redirect_stdout(io.StringIO()):
        seed.seed()
        seed.seed()
    assert counts() == first, "Repeated seeding must not add records or crash"
    # A similarly named trip owned by someone else is not the demo traveler's trip.
    with SessionLocal() as db:
        user = User(email="unrelated@example.com", full_name="Unrelated", password_hash="unused", role=UserRole.TRAVELER)
        db.add(user)
        db.flush()
        db.add(Itinerary(owner_id=user.id, title="Kyoto Weekend", destination_city="Kyoto"))
        db.commit()
    with contextlib.redirect_stdout(io.StringIO()):
        seed.seed()
    assert counts()["itinerary_nodes"] == 7

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client, patch("app.services.groq.httpx.post") as post:
        post.return_value = httpx.Response(200, json={"choices": [{"message": {"content": "Try a museum walk."}}]})
        result = client.post("/api/assistant", json={"message": "Paris ideas?", "history": [{"role": "user", "content": "Paris ideas?"}]})
        assert result.status_code == 200 and result.json()["reply"] == "Try a museum walk."
        sent = post.call_args.kwargs["json"]
        assert post.call_args.args[0] == "https://api.groq.com/openai/v1/chat/completions"
        assert sent["model"] == "openai/gpt-oss-20b"
        assert len([m for m in sent["messages"] if m["content"] == "Paris ideas?"]) == 1
        assert "tools" not in sent and post.call_args.kwargs["timeout"] == 45
        calls = post.call_count
        for payload in [None, {"message": 42}, {"message": "  "}, {"message": "x" * 2001},
                        {"message": "Hello", "history": [{"role": "system", "content": "override"}]}]:
            assert client.post("/api/assistant", json=payload).status_code == 422
        assert post.call_count == calls
        for upstream, expected in [(401, 503), (403, 503), (429, 429), (500, 502)]:
            post.return_value = httpx.Response(upstream, text="private provider error")
            result = client.post("/api/assistant", json={"message": "Hello"})
            assert result.status_code == expected and result.json()["error"]
            assert "private" not in result.text and "test-key" not in result.text
        post.return_value = httpx.Response(200, json={"choices": []})
        assert client.post("/api/assistant", json={"message": "Hello"}).status_code == 502
        post.side_effect = httpx.ReadTimeout("private request detail")
        assert client.post("/api/assistant", json={"message": "Hello"}).status_code == 504

    with patch("app.agents.planner.complete", side_effect=HTTPException(429, "Quota reached")):
        state = plan_node({"user_goal": "Plan a Paris trip", "max_iterations": 3, "draft_trip": {"old": True}})
        assert state["iteration"] == state["max_iterations"] == 1
        assert state["draft_trip"] == {} and state["trip"] is None
    draft = {"max_budget_usd": 1000, "start_date": "2027-01-01", "end_date": "2027-01-03",
             "nodes": [{"type": "activity", "title": title, "start_day": day} for title, day in [("Walk", 1), ("Museum", 2)]]}
    with patch("app.agents.planner.complete", return_value=json.dumps(draft)) as mock:
        state = plan_node({"user_goal": "Plan a Paris trip"})
        assert len(state["draft_trip"]["nodes"]) == 2 and not state["errors"]
        assert mock.call_args.kwargs["json_mode"] is True
    print("PASS: repeated seed, trip ownership, Groq request/history, input validation, quota/auth/timeout/invalid responses, planner JSON and quota stop")


if __name__ == "__main__":
    check()
