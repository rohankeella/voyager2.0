"""DTO-P3 Phase 1 — multi-agent orchestration.

Agent layer sits above the existing services (Amadeus proxy, recommendations,
graph engine) and turns natural-language user goals into a validated SuperTrip
DAG. LangGraph coordinates the Planner → Executor → Supervisor loop; Gemini
provides the reasoning; existing FastAPI services provide the actual travel
data (via `tools.py`).
"""

from app.agents.orchestrator import plan_trip

__all__ = ["plan_trip"]
