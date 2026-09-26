"""F-02: Unified Data Catalog + F-07 provider-side CRUD.

Public endpoints (list/detail) power the traveler-facing discover pages;
provider-scoped endpoints power the operator console. Any change here fires
a `catalog:changed` event on the SSE bus (F-06) so open recommendation feeds
refresh within seconds.
"""

from datetime import date as Date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, func
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

CATEGORY_LABELS = {
    "CULTURE": "Attractions & culture", "OUTDOOR": "Nature & adventure",
    "FOOD": "Food & drink", "WORKSHOP": "Workshops", "FESTIVAL": "Festivals",
    "NIGHTLIFE": "Nightlife & shows",
}


def _catalog(city=None, q=None, date=None):
    stmt = select(Experience).where(Experience.is_active.is_(True))
    if city:
        stmt = stmt.where(Experience.city.ilike(f"%{city}%"))
    if q:
        stmt = stmt.where(or_(Experience.title.ilike(f"%{q}%"),
                             Experience.description.ilike(f"%{q}%"),
                             Experience.city.ilike(f"%{q}%")))
    if date:
        # Operating days are a schedule, not a claim of live booking inventory.
        stmt = stmt.where(or_(~Experience.hours.any(), Experience.hours.any(
            OperatingHour.day_of_week == date.weekday())))
    return stmt


@router.get("/facets")
def experience_facets(db: Session = Depends(get_db), city: str | None = None,
                      q: str | None = None, date: Date | None = None):
    base = _catalog(city, q, date).subquery()
    prices = db.execute(select(base.c.currency, func.min(base.c.base_cost),
                               func.max(base.c.base_cost)).group_by(base.c.currency)).all()
    counts = dict(db.execute(select(base.c.category, func.count()).group_by(base.c.category)).all())
    return {"categories": [{"id": key, "name": name, "count": counts.get(key, 0)}
                           for key, name in CATEGORY_LABELS.items()],
            "prices": [{"currency": c, "min": float(lo), "max": float(hi)} for c, lo, hi in prices]}


@router.get("", response_model=list[ExperienceOut])
def list_experiences(
    db: Session = Depends(get_db),
    city: Optional[str] = Query(default=None),
    category: list[ExperienceCategory] = Query(default=[]),
    q: Optional[str] = Query(default=None, description="title/description search"),
    search: str | None = None,
    date: Date | None = None,
    minPrice: float | None = Query(default=None, ge=0),
    maxPrice: float | None = Query(default=None, ge=0),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    duration: list[Literal["short", "half", "full", "day", "multi"]] = Query(default=[]),
    rating: float | None = Query(default=None, ge=0, le=5),
    freeCancellation: bool = False,
    sort: Literal["popularity", "price_asc", "price_desc", "rating", "recommended"] = "popularity",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ExperienceOut]:
    if minPrice is not None and maxPrice is not None and minPrice > maxPrice:
        raise HTTPException(422, "minPrice must not exceed maxPrice")
    stmt = _catalog(city, q, date).options(selectinload(Experience.hours))
    if search:
        stmt = stmt.where(or_(Experience.title.ilike(f"%{search}%"), Experience.description.ilike(f"%{search}%")))
    if category:
        stmt = stmt.where(Experience.category.in_(category))
    if minPrice is not None:
        stmt = stmt.where(Experience.base_cost >= minPrice)
    if maxPrice is not None:
        stmt = stmt.where(Experience.base_cost <= maxPrice)
    if currency:
        stmt = stmt.where(Experience.currency == currency)
    if rating is not None:
        stmt = stmt.where(Experience.attributes["rating"].as_float() >= rating)
    if freeCancellation:
        stmt = stmt.where(Experience.attributes["free_cancellation"].as_boolean().is_(True))
    if duration:
        ranges = {"short": (0, 180), "half": (180, 360), "full": (360, 720),
                  "day": (720, 1440), "multi": (1440, None)}
        conditions = []
        for key in duration:
            lo, hi = ranges[key]
            condition = Experience.duration_mins >= lo
            if hi is not None:
                condition &= Experience.duration_mins < hi
            conditions.append(condition)
        stmt = stmt.where(or_(*conditions))
    orders = {
        "price_asc": Experience.base_cost.asc(), "price_desc": Experience.base_cost.desc(),
        "rating": Experience.attributes["rating"].as_float().desc().nullslast(),
        "popularity": Experience.attributes["popularity_score"].as_float().desc().nullslast(),
        "recommended": Experience.attributes["recommendation_score"].as_float().desc().nullslast(),
    }
    # Currency grouping avoids implying an exchange rate when no conversion exists.
    if sort.startswith("price"):
        stmt = stmt.order_by(Experience.currency)
    stmt = stmt.order_by(orders[sort], Experience.title, Experience.id).limit(limit).offset(offset)
    rows = db.execute(stmt).scalars().all()
    return [ExperienceOut.model_validate(r) for r in rows]


@router.get("/{experience_id}", response_model=ExperienceOut)
def get_experience(experience_id: str, db: Session = Depends(get_db)) -> ExperienceOut:
    exp = _load(db, experience_id)
    if not exp.is_active:
        raise HTTPException(404, "experience not found")
    return ExperienceOut.model_validate(exp)


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
