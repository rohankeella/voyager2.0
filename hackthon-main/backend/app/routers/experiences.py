"""F-02: Unified Data Catalog + F-07 provider-side CRUD.

Public endpoints (list/detail) power the traveler-facing discover pages;
provider-scoped endpoints power the operator console. Any change here fires
a `catalog:changed` event on the SSE bus (F-06) so open recommendation feeds
refresh within seconds.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import require_provider
from app.models.experience import Experience, ExperienceCategory, OperatingHour
from app.models.provider import Provider
from app.models.user import User
from app.schemas.experience import ExperienceCreate, ExperienceOut, ExperienceUpdate
from app.services.events import event_bus
from app.services.slug import slugify


router = APIRouter(prefix="/api/experiences", tags=["experiences"])
provider_router = APIRouter(prefix="/api/providers/me/experiences", tags=["providers"])


def _load(db: Session, experience_id: str) -> Experience:
    exp = db.execute(
        select(Experience)
        .options(selectinload(Experience.hours))
        .where(Experience.id == experience_id)
    ).scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="experience not found")
    return exp


def _resolve_provider(db: Session, user: User) -> Provider:
    provider = db.execute(select(Provider).where(Provider.user_id == user.id)).scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="provider profile required")
    return provider


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    i = 2
    while db.execute(select(Experience).where(Experience.slug == slug)).scalar_one_or_none():
        slug = f"{base}-{i}"
        i += 1
    return slug


# --------------------------- public catalog --------------------------------


@router.get("", response_model=list[ExperienceOut])
def list_experiences(
    db: Session = Depends(get_db),
    city: Optional[str] = Query(default=None),
    category: Optional[ExperienceCategory] = Query(default=None),
    q: Optional[str] = Query(default=None, description="title/description search"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ExperienceOut]:
    stmt = select(Experience).options(selectinload(Experience.hours)).where(Experience.is_active == True)  # noqa: E712
    if city:
        stmt = stmt.where(Experience.city.ilike(f"%{city}%"))
    if category:
        stmt = stmt.where(Experience.category == category)
    if q:
        stmt = stmt.where(Experience.title.ilike(f"%{q}%"))
    stmt = stmt.limit(limit).offset(offset).order_by(Experience.title.asc())
    rows = db.execute(stmt).scalars().all()
    return [ExperienceOut.model_validate(r) for r in rows]


@router.get("/{experience_id}", response_model=ExperienceOut)
def get_experience(experience_id: str, db: Session = Depends(get_db)) -> ExperienceOut:
    return ExperienceOut.model_validate(_load(db, experience_id))


# --------------------------- provider CRUD ---------------------------------


@provider_router.post("", response_model=ExperienceOut, status_code=status.HTTP_201_CREATED)
def create_experience(
    payload: ExperienceCreate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> ExperienceOut:
    provider = _resolve_provider(db, user)

    exp = Experience(
        provider_id=provider.id,
        title=payload.title,
        slug=_unique_slug(db, slugify(payload.title)),
        description=payload.description,
        category=payload.category,
        base_cost=payload.base_cost,
        currency=payload.currency,
        duration_mins=payload.duration_mins,
        lat=payload.lat,
        lng=payload.lng,
        city=payload.city,
        country=payload.country,
        address=payload.address,
        capacity_max=payload.capacity_max,
        seats_available=payload.seats_available,
        attributes=payload.attributes,
        interest_tags=payload.interest_tags,
    )
    for h in payload.hours:
        exp.hours.append(OperatingHour(day_of_week=h.day_of_week, open_time=h.open_time, close_time=h.close_time))

    db.add(exp)
    db.commit()
    db.refresh(exp)

    event_bus.publish({"type": "catalog:changed", "action": "created", "experience_id": exp.id, "city": exp.city})
    return ExperienceOut.model_validate(exp)


@provider_router.get("", response_model=list[ExperienceOut])
def list_my_experiences(
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> list[ExperienceOut]:
    provider = _resolve_provider(db, user)
    rows = (
        db.execute(
            select(Experience)
            .options(selectinload(Experience.hours))
            .where(Experience.provider_id == provider.id)
            .order_by(Experience.updated_at.desc())
        )
        .scalars()
        .all()
    )
    return [ExperienceOut.model_validate(r) for r in rows]


@provider_router.patch("/{experience_id}", response_model=ExperienceOut)
def update_experience(
    experience_id: str,
    payload: ExperienceUpdate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> ExperienceOut:
    provider = _resolve_provider(db, user)
    exp = _load(db, experience_id)
    if exp.provider_id != provider.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your experience")

    for field, value in payload.model_dump(exclude_unset=True, exclude={"hours"}).items():
        setattr(exp, field, value)

    if payload.hours is not None:
        exp.hours.clear()
        for h in payload.hours:
            exp.hours.append(OperatingHour(day_of_week=h.day_of_week, open_time=h.open_time, close_time=h.close_time))

    db.commit()
    db.refresh(exp)

    event_bus.publish({"type": "catalog:changed", "action": "updated", "experience_id": exp.id, "city": exp.city})
    return ExperienceOut.model_validate(exp)


@provider_router.delete("/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(
    experience_id: str,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> None:
    provider = _resolve_provider(db, user)
    exp = _load(db, experience_id)
    if exp.provider_id != provider.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your experience")
    db.delete(exp)
    db.commit()
    event_bus.publish({"type": "catalog:changed", "action": "deleted", "experience_id": experience_id})
