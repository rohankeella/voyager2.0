"""F-01 (matching) + F-04 (gatekeeper) + F-05 (gap-filler) endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.experience import Experience
from app.models.itinerary import Itinerary, ItinerarySlot
from app.models.user import User
from app.schemas.experience import ExperienceOut
from app.schemas.recommendation import (
    GapFillQuery,
    GapFillResponse,
    GapSuggestion,
    GapWindow,
    RecommendationQuery,
    RecommendationsResponse,
    ScoredExperienceOut,
)
from app.services.matching import MatchContext, rank_experiences


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _candidate_experiences(db: Session, city: str | None) -> list[Experience]:
    stmt = select(Experience).options(selectinload(Experience.hours)).where(Experience.is_active == True)  # noqa: E712
    if city:
        stmt = stmt.where(Experience.city.ilike(f"%{city}%"))
    return list(db.execute(stmt).scalars().all())


def _serialize(scored) -> ScoredExperienceOut:
    return ScoredExperienceOut(
        experience=ExperienceOut.model_validate(scored.experience),
        score=scored.score,
        breakdown=scored.breakdown,
        transit_mins=scored.transit_mins,
        distance_km=scored.distance_km,
        reasons=scored.reasons,
    )


@router.post("/match", response_model=RecommendationsResponse)
def match(
    query: RecommendationQuery,
    db: Session = Depends(get_db),
) -> RecommendationsResponse:
    if query.window_end <= query.at:
        raise HTTPException(status_code=400, detail="window_end must be after at")

    ctx = MatchContext(
        lat=query.lat,
        lng=query.lng,
        at=query.at,
        window_end=query.window_end,
        interests=query.interests,
        priorities=query.priorities,
        budget_max=query.budget_max,
        group_type=query.group_type,
        accessibility_flags=query.accessibility_flags,
        travel_mode=query.travel_mode,
    )
    candidates = _candidate_experiences(db, query.city)
    scored = rank_experiences(candidates, ctx, limit=query.limit)
    return RecommendationsResponse(
        query_window_mins=ctx.window_mins,
        candidates_scanned=len(candidates),
        results=[_serialize(s) for s in scored],
    )


@router.post("/for-me", response_model=RecommendationsResponse)
def match_for_me(
    query: RecommendationQuery,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationsResponse:
    """Same as /match but merges the caller's stored onboarding preferences
    with anything they passed inline (inline wins)."""
    prefs = user.preferences or {}
    merged = query.model_copy(update={
        "interests": query.interests or prefs.get("activities", []),
        "priorities": query.priorities or prefs.get("priorities", []),
        "budget_max": query.budget_max if query.budget_max is not None else prefs.get("customDailyBudget") or None,
        "group_type": query.group_type or (prefs.get("tripStyle") or None),
    })
    return match(merged, db)


def _extract_gaps(slots: list[ItinerarySlot], min_gap_mins: int) -> list[GapWindow]:
    """Given a sorted list of itinerary slots, yield the idle windows between
    them (F-05 acceptance criterion)."""
    if not slots:
        return []
    gaps: list[GapWindow] = []
    for prev, nxt in zip(slots, slots[1:]):
        # Respect the buffer the user configured on each slot — those are the
        # cushions they don't want touched (transit padding, meal breaks…).
        start = prev.end_at + timedelta(minutes=prev.buffer_after_mins)
        end = nxt.start_at - timedelta(minutes=nxt.buffer_before_mins)
        duration = int((end - start).total_seconds() // 60)
        if duration >= min_gap_mins:
            gaps.append(
                GapWindow(
                    start_at=start,
                    end_at=end,
                    duration_mins=duration,
                    anchor_before=prev.title,
                    anchor_after=nxt.title,
                    lat=prev.lat if prev.lat is not None else nxt.lat,
                    lng=prev.lng if prev.lng is not None else nxt.lng,
                )
            )
    return gaps


@router.post("/gap-fill", response_model=GapFillResponse)
def gap_fill(
    query: GapFillQuery,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GapFillResponse:
    itinerary = db.execute(
        select(Itinerary)
        .options(selectinload(Itinerary.slots))
        .where(Itinerary.id == query.itinerary_id)
    ).scalar_one_or_none()

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="itinerary not found")
    if itinerary.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your itinerary")

    gaps = _extract_gaps(list(itinerary.slots), query.min_gap_mins)
    if not gaps:
        return GapFillResponse(itinerary_id=itinerary.id, gaps=[])

    candidates = _candidate_experiences(db, itinerary.destination_city)

    suggestions: list[GapSuggestion] = []
    for gap in gaps:
        if gap.lat is None or gap.lng is None:
            continue
        ctx = MatchContext(
            lat=gap.lat,
            lng=gap.lng,
            at=gap.start_at,
            window_end=gap.end_at,
            interests=query.interests,
            priorities=query.priorities,
            budget_max=query.budget_max,
            group_type=query.group_type,
            accessibility_flags=query.accessibility_flags,
            travel_mode=query.travel_mode,
        )
        scored = rank_experiences(candidates, ctx, limit=query.per_gap_limit)
        suggestions.append(GapSuggestion(gap=gap, suggestions=[_serialize(s) for s in scored]))

    return GapFillResponse(itinerary_id=itinerary.id, gaps=suggestions)
