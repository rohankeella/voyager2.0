"""Multi-Factor Matching Engine (F-01).

Implements the PRD scoring formula:

    Score = w1 * S_interest + w2 * S_logistics + w3 * S_budget + w4 * S_fit

Where S_logistics collapses to 0 if transit + duration exceeds the window,
which is what makes the gatekeeper (F-04) a hard filter rather than a soft
penalty. That behaviour is exercised by the acceptance criteria on F-01:
"Given a 90-minute free window, the engine returns zero experiences whose
total time (transit + duration) exceeds 90 minutes."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from app.models.experience import Experience
from app.services.logistics import (
    TravelMode,
    estimated_travel_mins,
    haversine_km,
    window_overlaps_hours,
)


DEFAULT_WEIGHTS = {"interest": 0.40, "logistics": 0.25, "budget": 0.20, "fit": 0.15}


# The frontend Priority enum -> which experience tags/categories should be
# lifted. This keeps priority handling declarative rather than sprinkled
# through the scorer.
PRIORITY_BONUS: dict[str, dict[str, list[str]]] = {
    "food":       {"tags": ["food-tours"],       "categories": ["FOOD"]},
    "nature":     {"tags": ["hiking", "wildlife", "camping"], "categories": ["OUTDOOR"]},
    "adventure":  {"tags": ["hiking", "trekking", "skiing", "water-sports"], "categories": ["OUTDOOR"]},
    "culture":    {"tags": ["museums", "historical-places"], "categories": ["CULTURE"]},
    "nightlife":  {"tags": ["nightlife"], "categories": ["NIGHTLIFE"]},
    "luxury":     {"tags": [], "categories": []},
}


@dataclass
class MatchContext:
    lat: float
    lng: float
    at: datetime
    window_end: datetime
    interests: list[str]
    priorities: list[str]
    budget_max: float | None
    group_type: str | None
    accessibility_flags: list[str]
    travel_mode: TravelMode

    @property
    def window_mins(self) -> int:
        return max(0, int((self.window_end - self.at).total_seconds() // 60))


@dataclass
class ScoredExperience:
    experience: Experience
    score: float
    breakdown: dict[str, float]
    transit_mins: int
    distance_km: float
    reasons: list[str]


def _interest_score(exp: Experience, interests: list[str], priorities: list[str]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    if not interests and not priorities:
        return 0.5, ["no interest signal — neutral score"]

    tags = set(exp.interest_tags or [])
    overlap = tags.intersection(interests)
    base = len(overlap) / len(interests) if interests else 0.0
    if overlap:
        reasons.append(f"matches interests: {', '.join(sorted(overlap))}")

    # Top-priority bump — 20% lift if the experience's category or a tag
    # aligns with the user's #1 priority.
    if priorities:
        top = priorities[0]
        bonus = PRIORITY_BONUS.get(top)
        if bonus:
            if exp.category.value in bonus["categories"] or tags.intersection(bonus["tags"]):
                base = min(1.0, base + 0.2)
                reasons.append(f"aligns with priority: {top}")

    return max(0.0, min(1.0, base)), reasons


def _logistics_score(
    exp: Experience, ctx: MatchContext
) -> tuple[float, int, float, list[str]]:
    dist_km = haversine_km(ctx.lat, ctx.lng, exp.lat, exp.lng)
    transit = estimated_travel_mins(ctx.lat, ctx.lng, exp.lat, exp.lng, ctx.travel_mode)
    total_needed = transit + exp.duration_mins

    reasons: list[str] = []
    if ctx.window_mins <= 0:
        return 0.0, transit, dist_km, ["no time window available"]

    if total_needed > ctx.window_mins:
        reasons.append(
            f"needs {total_needed}m (transit {transit}m + activity {exp.duration_mins}m) "
            f"but only {ctx.window_mins}m free — hard filtered"
        )
        return 0.0, transit, dist_km, reasons

    slack = ctx.window_mins - total_needed
    # Reward efficient fits: 1.0 when we consume almost the whole window,
    # decaying toward 0.4 for very short activities in a large window.
    utilization = 1.0 - (slack / ctx.window_mins)
    score = 0.4 + 0.6 * utilization
    reasons.append(f"fits window with {slack}m to spare ({transit}m transit)")
    return score, transit, dist_km, reasons


def _budget_score(exp: Experience, budget_max: float | None) -> tuple[float, list[str]]:
    if budget_max is None or budget_max <= 0:
        return 0.6, []
    cost = float(exp.base_cost or 0)
    if cost <= 0:
        return 1.0, ["free"]
    ratio = cost / budget_max
    if ratio <= 0.5:
        return 1.0, [f"well under budget (₹{cost:.0f} of ₹{budget_max:.0f})"]
    if ratio <= 1.0:
        # 1.0 -> 0.5 as cost climbs from 50% to 100% of budget.
        return 1.0 - (ratio - 0.5), [f"within budget (₹{cost:.0f} of ₹{budget_max:.0f})"]
    if ratio <= 1.25:
        return 0.2, [f"slightly over budget (₹{cost:.0f} vs ₹{budget_max:.0f})"]
    return 0.0, [f"over budget (₹{cost:.0f} vs ₹{budget_max:.0f})"]


def _fit_score(exp: Experience, ctx: MatchContext) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.5

    attrs = exp.attributes or {}
    # Group fit
    good_for: list[str] = attrs.get("good_for", []) if isinstance(attrs, dict) else []
    if ctx.group_type and good_for and ctx.group_type.lower() in {g.lower() for g in good_for}:
        score += 0.25
        reasons.append(f"good for {ctx.group_type}")

    # Accessibility
    if ctx.accessibility_flags:
        supports: list[str] = attrs.get("accessibility", []) if isinstance(attrs, dict) else []
        needed = set(ctx.accessibility_flags)
        met = needed.intersection(supports)
        if met:
            score += 0.15
            reasons.append(f"accessibility: {', '.join(sorted(met))}")
        missing = needed - set(supports)
        if missing:
            score -= 0.2
            reasons.append(f"missing accessibility: {', '.join(sorted(missing))}")

    if exp.seats_available <= 0:
        score = 0.0
        reasons.append("sold out")

    return max(0.0, min(1.0, score)), reasons


def score_experience(
    exp: Experience,
    ctx: MatchContext,
    weights: dict[str, float] | None = None,
) -> ScoredExperience:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    interest, i_reasons = _interest_score(exp, ctx.interests, ctx.priorities)
    logistics, transit_mins, dist_km, l_reasons = _logistics_score(exp, ctx)
    budget, b_reasons = _budget_score(exp, ctx.budget_max)
    fit, f_reasons = _fit_score(exp, ctx)

    raw = (
        w["interest"] * interest
        + w["logistics"] * logistics
        + w["budget"] * budget
        + w["fit"] * fit
    )
    # Present score on a 0-100 scale for the UI.
    final = round(raw * 100, 1)

    breakdown = {
        "interest": round(interest, 3),
        "logistics": round(logistics, 3),
        "budget": round(budget, 3),
        "fit": round(fit, 3),
        "weights": w,
    }
    reasons = i_reasons + l_reasons + b_reasons + f_reasons
    return ScoredExperience(
        experience=exp,
        score=final,
        breakdown=breakdown,
        transit_mins=transit_mins,
        distance_km=round(dist_km, 2),
        reasons=reasons,
    )


def apply_gatekeeper(
    experiences: list[Experience], ctx: MatchContext
) -> list[Experience]:
    """F-04: Time & Logistics Gatekeeper. Hard-filters experiences that can't
    possibly fit the window or that are closed."""
    keep: list[Experience] = []
    depart_by = ctx.window_end
    for exp in experiences:
        if not exp.is_active:
            continue
        transit = estimated_travel_mins(ctx.lat, ctx.lng, exp.lat, exp.lng, ctx.travel_mode)
        arrive = ctx.at + timedelta(minutes=transit)
        finish = arrive + timedelta(minutes=exp.duration_mins)
        if finish > depart_by:
            continue
        if not window_overlaps_hours(exp.hours, arrive, finish):
            continue
        keep.append(exp)
    return keep


def rank_experiences(
    experiences: list[Experience],
    ctx: MatchContext,
    limit: int = 20,
    weights: dict[str, float] | None = None,
) -> list[ScoredExperience]:
    filtered = apply_gatekeeper(experiences, ctx)
    scored = [score_experience(e, ctx, weights) for e in filtered]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:limit]
