"""Itinerary CRUD. Slots are what the gap-filler (F-05) reads to detect
unallocated time, and what the map view renders as fixed anchors."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.itinerary import Itinerary, ItinerarySlot
from app.models.user import User
from app.schemas.itinerary import (
    ItineraryCreate,
    ItineraryOut,
    ItinerarySlotIn,
    ItinerarySlotOut,
    ItineraryUpdate,
)
from app.services.events import event_bus


router = APIRouter(prefix="/api/itineraries", tags=["itineraries"])


def _load(db: Session, itinerary_id: str, user: User) -> Itinerary:
    itinerary = db.execute(
        select(Itinerary).options(selectinload(Itinerary.slots)).where(Itinerary.id == itinerary_id)
    ).scalar_one_or_none()
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="itinerary not found")
    if itinerary.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your itinerary")
    return itinerary


@router.get("", response_model=list[ItineraryOut])
def list_itineraries(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ItineraryOut]:
    rows = (
        db.execute(
            select(Itinerary)
            .options(selectinload(Itinerary.slots))
            .where(Itinerary.owner_id == user.id)
            .order_by(Itinerary.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [ItineraryOut.model_validate(r) for r in rows]


@router.post("", response_model=ItineraryOut, status_code=status.HTTP_201_CREATED)
def create_itinerary(
    payload: ItineraryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItineraryOut:
    itinerary = Itinerary(
        owner_id=user.id,
        title=payload.title,
        destination_city=payload.destination_city,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    for s in payload.slots:
        itinerary.slots.append(ItinerarySlot(**s.model_dump()))
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)

    event_bus.publish({"type": "itinerary:changed", "action": "created", "itinerary_id": itinerary.id, "owner_id": user.id})
    return ItineraryOut.model_validate(itinerary)


@router.get("/{itinerary_id}", response_model=ItineraryOut)
def get_itinerary(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItineraryOut:
    return ItineraryOut.model_validate(_load(db, itinerary_id, user))


@router.patch("/{itinerary_id}", response_model=ItineraryOut)
def update_itinerary(
    itinerary_id: str,
    payload: ItineraryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItineraryOut:
    itinerary = _load(db, itinerary_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(itinerary, field, value)
    db.commit()
    db.refresh(itinerary)
    event_bus.publish({"type": "itinerary:changed", "action": "updated", "itinerary_id": itinerary.id, "owner_id": user.id})
    return ItineraryOut.model_validate(itinerary)


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    itinerary = _load(db, itinerary_id, user)
    db.delete(itinerary)
    db.commit()
    event_bus.publish({"type": "itinerary:changed", "action": "deleted", "itinerary_id": itinerary_id, "owner_id": user.id})


# ---- slot management --------------------------------------------------------


@router.post("/{itinerary_id}/slots", response_model=ItinerarySlotOut, status_code=status.HTTP_201_CREATED)
def add_slot(
    itinerary_id: str,
    payload: ItinerarySlotIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItinerarySlotOut:
    itinerary = _load(db, itinerary_id, user)
    slot = ItinerarySlot(itinerary_id=itinerary.id, **payload.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    event_bus.publish({"type": "itinerary:changed", "action": "slot_added", "itinerary_id": itinerary.id, "owner_id": user.id})
    return ItinerarySlotOut.model_validate(slot)


@router.delete("/{itinerary_id}/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot(
    itinerary_id: str,
    slot_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    itinerary = _load(db, itinerary_id, user)
    slot = next((s for s in itinerary.slots if s.id == slot_id), None)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="slot not found")
    db.delete(slot)
    db.commit()
    event_bus.publish({"type": "itinerary:changed", "action": "slot_deleted", "itinerary_id": itinerary.id, "owner_id": user.id})
