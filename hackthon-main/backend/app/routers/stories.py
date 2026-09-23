"""P4 endpoints — Editorial & Narrative Discovery.

Public reads:
  GET  /api/context-tags                   registry — F-23
  GET  /api/stories                        feed (F-22), optional ?tag= filter
  GET  /api/stories/{slug}                 read with F-24 active updates resolved

Provider writes:
  POST   /api/stories                      draft
  PATCH  /api/stories/{id}
  POST   /api/stories/{id}/publish
  DELETE /api/stories/{id}
  POST   /api/stories/{id}/updates         attach an in-post banner (F-24)

Every write recomputes `context_tags` from the body_md + explicit list, and
recomputes `narrative_quality_score`, so the two structured signals never
drift from the editorial text.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, require_provider
from app.models.editorial import StoryPost, StoryUpdate
from app.models.provider import Provider
from app.models.user import User
from app.schemas.editorial import (
    ActiveUpdateOut,
    ContextTagOut,
    FeedResponse,
    RankedStoryOut,
    StoryPostCreate,
    StoryPostOut,
    StoryPostUpdate,
    StoryReadResponse,
    StoryUpdateIn,
    StoryUpdateOut,
)
from app.services.context_tags import BY_KEY, REGISTRY
from app.services.editorial import (
    RuntimeContext,
    rank_stories_for_reader,
    recompute_post_metadata,
    resolve_active_updates,
)
from app.services.events import event_bus
from app.services.slug import slugify


router = APIRouter(prefix="/api", tags=["editorial"])


# --- context tags -----------------------------------------------------------


@router.get("/context-tags", response_model=list[ContextTagOut])
def list_context_tags() -> list[ContextTagOut]:
    return [
        ContextTagOut(
            key=t.key,
            display=t.display,
            description=t.description,
            experience_filter_summary=t.experience_filter_summary,
        )
        for t in REGISTRY
    ]


# --- helpers ----------------------------------------------------------------


def _load_provider_for(user: User, db: Session) -> Provider:
    prov = db.execute(select(Provider).where(Provider.user_id == user.id)).scalar_one_or_none()
    if not prov:
        raise HTTPException(status_code=403, detail="provider profile required")
    return prov


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    i = 2
    while db.execute(select(StoryPost).where(StoryPost.slug == slug)).scalar_one_or_none():
        slug = f"{base}-{i}"
        i += 1
    return slug


def _load_post(db: Session, post_id: str) -> StoryPost:
    post = db.execute(
        select(StoryPost).options(selectinload(StoryPost.updates)).where(StoryPost.id == post_id)
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="story not found")
    return post


# --- feed (F-22) ------------------------------------------------------------


@router.get("/stories", response_model=FeedResponse)
def feed(
    db: Session = Depends(get_db),
    tag: Optional[str] = Query(default=None, description="Filter by a #Tag key or display form"),
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    stmt = select(StoryPost).where(StoryPost.published == True)  # noqa: E712
    if city:
        stmt = stmt.where(StoryPost.city.ilike(f"%{city}%"))
    all_stories = list(db.execute(stmt).scalars().all())

    applied_tag_key: str | None = None
    filtered = all_stories
    if tag:
        # accept either "#RainyDayFriendly", "RainyDayFriendly", or "rainydayfriendly"
        norm = tag.lstrip("#").lower()
        tag_obj = BY_KEY.get(norm)
        # also try matching against display forms
        if tag_obj is None:
            for t in REGISTRY:
                if t.display.lower() == norm:
                    tag_obj = t
                    break
        if tag_obj is not None:
            applied_tag_key = tag_obj.key
            filtered = [s for s in all_stories if tag_obj.key in (s.context_tags or [])]

    ranked = rank_stories_for_reader(filtered)
    return FeedResponse(
        stories=[
            RankedStoryOut(
                post=StoryPostOut.model_validate(r.post),
                score=r.score,
                matched_tags=r.matched_tags,
                quality_component=r.quality_component,
                match_component=r.match_component,
                freshness_component=r.freshness_component,
            )
            for r in ranked[:limit]
        ],
        considered=len(filtered),
        applied_tag=applied_tag_key,
    )


@router.get("/stories/for-me", response_model=FeedResponse)
def feed_for_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    tag: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    """Same as /stories but scored against the caller's onboarding
    preferences (activities + priorities). Demonstrates F-22 acceptance:
    a brand-new post can rank above older ones if its tags match."""
    prefs = user.preferences or {}
    activities = [str(a) for a in prefs.get("activities", [])]
    priorities = [str(p) for p in prefs.get("priorities", [])]

    stmt = select(StoryPost).where(StoryPost.published == True)  # noqa: E712
    if city:
        stmt = stmt.where(StoryPost.city.ilike(f"%{city}%"))
    all_stories = list(db.execute(stmt).scalars().all())

    applied_tag_key: str | None = None
    filtered = all_stories
    if tag:
        norm = tag.lstrip("#").lower()
        tag_obj = BY_KEY.get(norm)
        if tag_obj is not None:
            applied_tag_key = tag_obj.key
            filtered = [s for s in all_stories if tag_obj.key in (s.context_tags or [])]

    ranked = rank_stories_for_reader(
        filtered,
        preference_activities=activities,
        preference_tags=priorities,
    )
    return FeedResponse(
        stories=[
            RankedStoryOut(
                post=StoryPostOut.model_validate(r.post),
                score=r.score,
                matched_tags=r.matched_tags,
                quality_component=r.quality_component,
                match_component=r.match_component,
                freshness_component=r.freshness_component,
            )
            for r in ranked[:limit]
        ],
        considered=len(filtered),
        applied_tag=applied_tag_key,
    )


# --- individual read with F-24 --------------------------------------------


@router.get("/stories/{slug}", response_model=StoryReadResponse)
def read_story(
    slug: str,
    db: Session = Depends(get_db),
    weather: Optional[str] = Query(default=None, description="e.g. rain, clear, snow"),
    temperature_c: Optional[float] = Query(default=None),
    hour_utc: Optional[int] = Query(default=None, ge=0, le=23),
    crowd_pct: Optional[float] = Query(default=None, ge=0, le=200),
) -> StoryReadResponse:
    post = db.execute(
        select(StoryPost).options(selectinload(StoryPost.updates)).where(StoryPost.slug == slug)
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="story not found")
    if not post.published:
        raise HTTPException(status_code=404, detail="story not published")

    ctx = RuntimeContext(
        weather=weather,
        temperature_c=temperature_c,
        hour_utc=hour_utc,
        crowd_pct=crowd_pct,
    )
    resolved = resolve_active_updates(list(post.updates), ctx)
    return StoryReadResponse(
        post=StoryPostOut.model_validate(post),
        active_updates=[
            ActiveUpdateOut(
                id=r.id, kind=r.kind, message=r.message, matched_condition=r.matched_condition
            )
            for r in resolved
        ],
    )


# --- provider CRUD ----------------------------------------------------------


@router.post("/stories", response_model=StoryPostOut, status_code=status.HTTP_201_CREATED)
def create_story(
    payload: StoryPostCreate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> StoryPostOut:
    provider = _load_provider_for(user, db)
    post = StoryPost(
        author_id=user.id,
        provider_id=provider.id,
        experience_id=payload.experience_id,
        title=payload.title,
        slug=_unique_slug(db, slugify(payload.title)),
        summary=payload.summary,
        body_md=payload.body_md,
        cover_image_url=payload.cover_image_url,
        city=payload.city,
        location_hint=payload.location_hint,
        context_tags=payload.context_tags,
    )
    recompute_post_metadata(post)
    db.add(post)
    db.commit()
    db.refresh(post)
    event_bus.publish({"type": "story:changed", "action": "created", "story_id": post.id})
    return StoryPostOut.model_validate(post)


@router.patch("/stories/{story_id}", response_model=StoryPostOut)
def update_story(
    story_id: str,
    payload: StoryPostUpdate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> StoryPostOut:
    post = _load_post(db, story_id)
    if post.author_id != user.id:
        raise HTTPException(status_code=403, detail="not your story")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(post, k, v)
    recompute_post_metadata(post)

    db.commit()
    db.refresh(post)
    event_bus.publish({"type": "story:changed", "action": "updated", "story_id": post.id})
    return StoryPostOut.model_validate(post)


@router.post("/stories/{story_id}/publish", response_model=StoryPostOut)
def publish_story(
    story_id: str,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> StoryPostOut:
    post = _load_post(db, story_id)
    if post.author_id != user.id:
        raise HTTPException(status_code=403, detail="not your story")
    if not post.published:
        post.published = True
        post.published_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(post)
        event_bus.publish({"type": "story:changed", "action": "published", "story_id": post.id})
    return StoryPostOut.model_validate(post)


@router.delete("/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(
    story_id: str,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> None:
    post = _load_post(db, story_id)
    if post.author_id != user.id:
        raise HTTPException(status_code=403, detail="not your story")
    db.delete(post)
    db.commit()
    event_bus.publish({"type": "story:changed", "action": "deleted", "story_id": story_id})


# --- adaptive updates (F-24) -----------------------------------------------


@router.post("/stories/{story_id}/updates", response_model=StoryUpdateOut, status_code=status.HTTP_201_CREATED)
def add_update(
    story_id: str,
    payload: StoryUpdateIn,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> StoryUpdateOut:
    post = _load_post(db, story_id)
    if post.author_id != user.id:
        raise HTTPException(status_code=403, detail="not your story")
    row = StoryUpdate(
        post_id=post.id,
        kind=payload.kind,
        message=payload.message,
        condition=payload.condition,
        expires_at=payload.expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    event_bus.publish({"type": "story:changed", "action": "update_added", "story_id": post.id})
    return StoryUpdateOut.model_validate(row)


@router.delete("/stories/{story_id}/updates/{update_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_update(
    story_id: str,
    update_id: str,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> None:
    post = _load_post(db, story_id)
    if post.author_id != user.id:
        raise HTTPException(status_code=403, detail="not your story")
    row = db.execute(
        select(StoryUpdate).where(StoryUpdate.id == update_id, StoryUpdate.post_id == story_id)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="update not found")
    db.delete(row)
    db.commit()
