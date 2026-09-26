"""P4 heuristics: narrative quality, feed ranking, adaptive updates.

F-22 acceptance criterion is the load-bearing one:
    "New listings with zero historical reviews can achieve high feed
     visibility if narrative quality scores and context tags match user
     profile constraints."

So the ranker MUST NOT read anything review-like. The formula intentionally
uses only:
  * narrative_quality_score (author-side signal)
  * preference match on context_tags  (reader-side signal)
  * freshness decay                    (temporal signal)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.models.editorial import StoryPost, StoryUpdate, StoryUpdateKind
from app.services.context_tags import parse_context_tags


# --- narrative quality ------------------------------------------------------


def narrative_quality_score(
    *, title: str, summary: str | None, body_md: str,
    cover_image_url: str | None, context_tags: list[str],
) -> float:
    """0..100 heuristic. Rewards presence of a summary, a cover image, a
    body of substantive length, and a handful of parseable context tags.
    Kept intentionally simple so authors can predict their score."""
    score = 0.0

    # Title: presence + not-too-short + not-too-long band
    tlen = len(title.strip()) if title else 0
    if tlen >= 20:
        score += 10
    elif tlen >= 8:
        score += 6

    # Summary: 60-300 chars is the sweet spot
    slen = len(summary.strip()) if summary else 0
    if 60 <= slen <= 300:
        score += 15
    elif slen > 0:
        score += 7

    # Body: reward length in bands; > 2500 chars caps at 40
    blen = len(body_md.strip()) if body_md else 0
    if blen >= 2500:
        score += 40
    elif blen >= 1200:
        score += 32
    elif blen >= 500:
        score += 22
    elif blen >= 150:
        score += 10

    # Cover image
    if cover_image_url:
        score += 10

    # Context tags: 2-5 tags is ideal, more starts to feel like spam
    n = len(context_tags)
    if 2 <= n <= 5:
        score += 20
    elif n == 1:
        score += 10
    elif n >= 6:
        score += 12

    # Formatting nudge: reward at least one markdown heading or bullet
    if body_md and any(marker in body_md for marker in ("\n#", "\n- ", "\n* ", "\n1.")):
        score += 5

    return round(min(100.0, score), 1)


# --- feed ranking (F-22) ----------------------------------------------------


DEFAULT_FEED_WEIGHTS = {"quality": 0.5, "match": 0.35, "freshness": 0.15}


@dataclass
class RankedStory:
    post: StoryPost
    score: float
    matched_tags: list[str]
    quality_component: float
    match_component: float
    freshness_component: float


def _freshness(published_at: datetime | None, now: datetime, halflife_days: float = 21.0) -> float:
    if published_at is None:
        return 0.0
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    days = max(0.0, (now - published_at).total_seconds() / 86400.0)
    # Exponential decay-ish: 1.0 at publish, ~0.5 at halflife_days, floors near 0.05
    return round(max(0.05, 2 ** (-days / halflife_days)), 4)


def rank_stories_for_reader(
    stories: list[StoryPost],
    *,
    preference_tags: list[str] | None = None,
    preference_activities: list[str] | None = None,
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
) -> list[RankedStory]:
    """Score + sort published stories for a reader profile. Note: no review
    count anywhere — F-22 demands that a zero-review new listing can rise
    to the top on quality + preference match alone."""
    now = now or datetime.now(timezone.utc)
    w = {**DEFAULT_FEED_WEIGHTS, **(weights or {})}
    pref_set = {t.lower() for t in (preference_tags or [])}
    activity_set = {a.lower() for a in (preference_activities or [])}

    ranked: list[RankedStory] = []
    for post in stories:
        if not post.published:
            continue
        story_tags = {t.lower() for t in (post.context_tags or [])}

        # Match component: how much of the reader's signal is served by
        # this post's tags.
        signal = pref_set | activity_set
        overlap = story_tags & signal
        match_component = (len(overlap) / len(signal)) if signal else 0.5

        quality_component = post.narrative_quality_score / 100.0
        freshness_component = _freshness(post.published_at, now)

        score = (
            w["quality"] * quality_component
            + w["match"] * match_component
            + w["freshness"] * freshness_component
        ) * 100.0

        ranked.append(RankedStory(
            post=post,
            score=round(score, 2),
            matched_tags=sorted(overlap),
            quality_component=round(quality_component, 3),
            match_component=round(match_component, 3),
            freshness_component=freshness_component,
        ))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


# --- F-24 adaptive updates --------------------------------------------------


@dataclass
class RuntimeContext:
    """What the client tells us about right-now conditions when rendering
    a story. Everything optional — an update whose condition references an
    unknown field is treated as not matching (fails closed)."""

    weather: str | None = None            # "rain", "clear", "snow", ...
    temperature_c: float | None = None
    hour_utc: int | None = None
    crowd_pct: float | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActiveUpdate:
    id: str
    kind: StoryUpdateKind
    message: str
    matched_condition: dict[str, Any]


def _condition_matches(condition: dict, ctx: RuntimeContext) -> bool:
    """Extend as new update types show up — each key handled defensively."""
    if not condition:
        return True

    if "weather" in condition:
        expected = str(condition["weather"]).lower()
        if not ctx.weather or ctx.weather.lower() != expected:
            return False

    if "weather_in" in condition:
        options = {str(x).lower() for x in condition["weather_in"]}
        if not ctx.weather or ctx.weather.lower() not in options:
            return False

    if "hour_between" in condition:
        try:
            lo, hi = condition["hour_between"]
        except (TypeError, ValueError):
            return False
        if ctx.hour_utc is None or not (int(lo) <= ctx.hour_utc <= int(hi)):
            return False

    if "crowd_gte" in condition:
        if ctx.crowd_pct is None or ctx.crowd_pct < float(condition["crowd_gte"]):
            return False

    if "crowd_lte" in condition:
        if ctx.crowd_pct is None or ctx.crowd_pct > float(condition["crowd_lte"]):
            return False

    if "temp_lte" in condition:
        if ctx.temperature_c is None or ctx.temperature_c > float(condition["temp_lte"]):
            return False

    if "temp_gte" in condition:
        if ctx.temperature_c is None or ctx.temperature_c < float(condition["temp_gte"]):
            return False

    return True


def resolve_active_updates(
    updates: list[StoryUpdate], ctx: RuntimeContext, now: datetime | None = None
) -> list[ActiveUpdate]:
    """Filter to updates that are (a) `is_active`, (b) not expired, and
    (c) whose condition matches `ctx`. Returns the resolved list in the
    order the client should render them — most-recent-first."""
    now = now or datetime.now(timezone.utc)
    resolved: list[ActiveUpdate] = []
    for u in updates:
        if not u.is_active:
            continue
        if u.expires_at is not None:
            exp = u.expires_at if u.expires_at.tzinfo else u.expires_at.replace(tzinfo=timezone.utc)
            if exp < now:
                continue
        if _condition_matches(u.condition or {}, ctx):
            resolved.append(ActiveUpdate(
                id=u.id, kind=u.kind, message=u.message,
                matched_condition=u.condition or {},
            ))
    return resolved


# --- convenience -----------------------------------------------------------


def recompute_post_metadata(post: StoryPost) -> StoryPost:
    """Re-parse tags out of body_md and recompute quality. Call on any
    create/update path so the two structured signals never drift from the
    editorial text."""
    tags_from_body = parse_context_tags(post.body_md or "")
    # If the author explicitly set context_tags, union with parsed tags.
    explicit = list(post.context_tags or [])
    merged: list[str] = []
    for t in explicit + tags_from_body:
        if t not in merged:
            merged.append(t)
    post.context_tags = merged
    post.narrative_quality_score = narrative_quality_score(
        title=post.title,
        summary=post.summary,
        body_md=post.body_md,
        cover_image_url=post.cover_image_url,
        context_tags=merged,
    )
    return post
