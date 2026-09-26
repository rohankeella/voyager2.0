from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.editorial import StoryUpdateKind


# ---- context tags (F-23) ---------------------------------------------------


class ContextTagOut(BaseModel):
    key: str
    display: str
    description: str
    experience_filter_summary: str


# ---- story updates (F-24) -------------------------------------------------


class StoryUpdateIn(BaseModel):
    kind: StoryUpdateKind
    message: str = Field(min_length=1, max_length=400)
    condition: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class StoryUpdateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    post_id: str
    kind: StoryUpdateKind
    message: str
    condition: dict[str, Any]
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class ActiveUpdateOut(BaseModel):
    id: str
    kind: StoryUpdateKind
    message: str
    matched_condition: dict[str, Any]


# ---- stories --------------------------------------------------------------


class StoryPostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=400)
    body_md: str = Field(min_length=1, max_length=20000)
    cover_image_url: str | None = None
    city: str | None = None
    location_hint: dict[str, Any] | None = None
    experience_id: str | None = None
    # Author-supplied explicit tags — parsed tags from body_md are unioned in.
    context_tags: list[str] = Field(default_factory=list)


class StoryPostUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    body_md: str | None = None
    cover_image_url: str | None = None
    city: str | None = None
    location_hint: dict[str, Any] | None = None
    experience_id: str | None = None
    context_tags: list[str] | None = None


class StoryPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    provider_id: str | None
    experience_id: str | None
    title: str
    slug: str
    summary: str | None
    body_md: str
    cover_image_url: str | None
    city: str | None
    location_hint: dict[str, Any] | None
    context_tags: list[str]
    narrative_quality_score: float
    published: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StoryReadResponse(BaseModel):
    """Public read — includes any adaptive banners the client should surface
    at the top of the post (F-24)."""

    post: StoryPostOut
    active_updates: list[ActiveUpdateOut]


class RankedStoryOut(BaseModel):
    post: StoryPostOut
    score: float
    matched_tags: list[str]
    quality_component: float
    match_component: float
    freshness_component: float


class FeedResponse(BaseModel):
    stories: list[RankedStoryOut]
    considered: int
    applied_tag: str | None
