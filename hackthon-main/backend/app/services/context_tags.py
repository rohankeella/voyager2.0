"""F-23 · Natural-Language Context Tags.

The registry maps a user-facing `#Tag` to a structured predicate that either:
  * filters `Experience` rows in SQL, or
  * filters `StoryPost` rows (feed).

The parser pulls `#Tag` mentions out of markdown so authors don't have to
maintain a separate metadata block — the same word appears in the story
text AND as a queryable filter (F-21 spec: "displays full editorial text
while maintaining standard JSON metadata fields for background filtering").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import ColumnElement, or_

from app.models.experience import Experience, ExperienceCategory


TAG_RE = re.compile(r"#([A-Za-z][A-Za-z0-9]{1,40})")


@dataclass(frozen=True)
class ContextTag:
    key: str                    # canonical form, lower-case
    display: str                # camel-case, matches the # in prose
    description: str
    experience_filter_summary: str

    # Built at import time — returns a SQLAlchemy WHERE expression.
    build_experience_filter: Callable[[], ColumnElement | None]


# --- filter builders --------------------------------------------------------


def _rainy_day_filter() -> ColumnElement:
    # Indoor-ish categories: workshops, culture (temples/museums), food halls.
    return Experience.category.in_(
        [
            ExperienceCategory.WORKSHOP,
            ExperienceCategory.CULTURE,
            ExperienceCategory.FOOD,
        ]
    )


def _budget_filter() -> ColumnElement:
    return Experience.base_cost <= 1000  # INR — matches backpacker/budget bands


def _date_night_filter() -> ColumnElement:
    return Experience.category.in_(
        [ExperienceCategory.FOOD, ExperienceCategory.NIGHTLIFE, ExperienceCategory.CULTURE]
    )


def _off_the_beaten_filter() -> ColumnElement:
    # High seats_available/capacity_max ratio → less crowded.
    return Experience.seats_available >= (Experience.capacity_max * 0.7)


def _family_friendly_filter() -> ColumnElement:
    # attributes is JSON with a `good_for` array; SQLite JSON lookups vary,
    # so fall back to substring match on the raw JSON text — good enough for
    # the demo dataset.
    from sqlalchemy import cast, String as SqlString
    return cast(Experience.attributes, SqlString).ilike('%"family"%')


def _solo_friendly_filter() -> ColumnElement:
    from sqlalchemy import cast, String as SqlString
    return cast(Experience.attributes, SqlString).ilike('%"solo"%')


def _foodie_filter() -> ColumnElement:
    return Experience.category == ExperienceCategory.FOOD


def _outdoors_filter() -> ColumnElement:
    return Experience.category == ExperienceCategory.OUTDOOR


def _hidden_gem_filter() -> ColumnElement:
    # Combines low crowd with a legacy `attributes.hidden_gem` flag if
    # anyone chooses to tag it that way in the future.
    from sqlalchemy import cast, String as SqlString
    return or_(
        Experience.seats_available >= (Experience.capacity_max * 0.8),
        cast(Experience.attributes, SqlString).ilike('%"hidden_gem": true%'),
    )


# --- registry ---------------------------------------------------------------


REGISTRY: list[ContextTag] = [
    ContextTag("rainydayfriendly", "RainyDayFriendly",
               "Indoor-first spots that stay pleasant in wet weather.",
               "category ∈ {WORKSHOP, CULTURE, FOOD}",
               _rainy_day_filter),
    ContextTag("budget", "Budget",
               "Under ₹1,000 per person.",
               "base_cost ≤ 1000 INR",
               _budget_filter),
    ContextTag("datenight", "DateNight",
               "Food, nightlife, or cultural picks that work for two.",
               "category ∈ {FOOD, NIGHTLIFE, CULTURE}",
               _date_night_filter),
    ContextTag("offthebeatenpath", "OffTheBeatenPath",
               "Quieter spots most tourists miss.",
               "seats_available ≥ 0.7 × capacity_max",
               _off_the_beaten_filter),
    ContextTag("familyfriendly", "FamilyFriendly",
               "Good for travellers with kids.",
               'attributes.good_for ⊇ "family"',
               _family_friendly_filter),
    ContextTag("solofriendly", "SoloFriendly",
               "Comfortable for solo travellers.",
               'attributes.good_for ⊇ "solo"',
               _solo_friendly_filter),
    ContextTag("foodie", "Foodie",
               "Local food-focussed listings.",
               "category = FOOD",
               _foodie_filter),
    ContextTag("outdoors", "Outdoors",
               "Trails, cycling, water — anything outside.",
               "category = OUTDOOR",
               _outdoors_filter),
    ContextTag("hiddengem", "HiddenGem",
               "Under-the-radar picks with room to breathe.",
               "seats_available ≥ 0.8 × capacity_max OR attributes.hidden_gem = true",
               _hidden_gem_filter),
]

BY_KEY: dict[str, ContextTag] = {t.key: t for t in REGISTRY}
BY_DISPLAY: dict[str, ContextTag] = {t.display.lower(): t for t in REGISTRY}


# --- parser -----------------------------------------------------------------


def parse_context_tags(text: str) -> list[str]:
    """Extract canonical tag keys from any string containing `#Tag` mentions.

    Order preserved, duplicates removed. Unknown tags are dropped silently
    so authors can experiment without corrupting the registry."""
    if not text:
        return []
    seen: dict[str, None] = {}
    for raw in TAG_RE.findall(text):
        key = raw.lower()
        tag = BY_KEY.get(key) or BY_DISPLAY.get(key)
        if tag is not None and tag.key not in seen:
            seen[tag.key] = None
    return list(seen.keys())


def experience_filter_for(tag_key: str) -> ColumnElement | None:
    tag = BY_KEY.get(tag_key.lower())
    if tag is None:
        return None
    return tag.build_experience_filter()
