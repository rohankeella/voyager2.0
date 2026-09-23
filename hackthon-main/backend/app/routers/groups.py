"""Groups + membership CRUD. A group is the outer container for a trip
ledger. Only the group's organizer can mutate structure (add/remove
members, delete the group); any member can read within their scope
(F-13 RBAC).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.group import Group, GroupMember, GroupMemberRole
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupMemberIn,
    GroupMemberOut,
    GroupOut,
    GroupUpdate,
)
from app.services.events import event_bus


router = APIRouter(prefix="/api/groups", tags=["groups"])


def _load_group(db: Session, group_id: str) -> Group:
    grp = db.execute(
        select(Group).options(selectinload(Group.members)).where(Group.id == group_id)
    ).scalar_one_or_none()
    if not grp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="group not found")
    return grp


def _my_membership(group: Group, user: User) -> GroupMember | None:
    for m in group.members:
        if m.user_id == user.id:
            return m
    return None


def require_membership(group: Group, user: User) -> GroupMember:
    m = _my_membership(group, user)
    if m is None and group.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not a group member")
    if m is None:
        # Creator without an explicit member row — synthesise organizer.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="organizer row missing; recreate group")
    return m


def require_organizer(group: Group, user: User) -> GroupMember:
    m = require_membership(group, user)
    if m.role != GroupMemberRole.ORGANIZER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="organizer role required")
    return m


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupOut:
    group = Group(
        name=payload.name,
        trip_destination=payload.trip_destination,
        base_currency=payload.base_currency,
        itinerary_id=payload.itinerary_id,
        created_by=user.id,
    )
    # Creator is always an organizer, even if they weren't in the input list.
    seen_user_ids: set[str] = set()
    organizer_row = GroupMember(
        user_id=user.id,
        display_name=user.full_name,
        email=user.email,
        role=GroupMemberRole.ORGANIZER,
    )
    group.members.append(organizer_row)
    seen_user_ids.add(user.id)

    for m in payload.members:
        if m.user_id and m.user_id in seen_user_ids:
            continue
        group.members.append(
            GroupMember(
                user_id=m.user_id,
                display_name=m.display_name,
                email=m.email,
                role=m.role,
            )
        )
        if m.user_id:
            seen_user_ids.add(m.user_id)

    db.add(group)
    db.commit()
    db.refresh(group)

    event_bus.publish({"type": "group:changed", "action": "created", "group_id": group.id})
    return GroupOut.model_validate(group)


@router.get("", response_model=list[GroupOut])
def list_my_groups(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GroupOut]:
    # Every group where I'm a member OR I created it.
    rows = (
        db.execute(
            select(Group)
            .options(selectinload(Group.members))
            .join(GroupMember, GroupMember.group_id == Group.id, isouter=True)
            .where((GroupMember.user_id == user.id) | (Group.created_by == user.id))
            .order_by(Group.created_at.desc())
            .distinct()
        )
        .scalars()
        .unique()
        .all()
    )
    return [GroupOut.model_validate(g) for g in rows]


@router.get("/{group_id}", response_model=GroupOut)
def get_group(
    group_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupOut:
    group = _load_group(db, group_id)
    require_membership(group, user)
    return GroupOut.model_validate(group)


@router.patch("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: str,
    payload: GroupUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupOut:
    group = _load_group(db, group_id)
    require_organizer(group, user)
    for f, v in payload.model_dump(exclude_unset=True).items():
        setattr(group, f, v)
    db.commit()
    db.refresh(group)
    event_bus.publish({"type": "group:changed", "action": "updated", "group_id": group.id})
    return GroupOut.model_validate(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    group = _load_group(db, group_id)
    require_organizer(group, user)
    db.delete(group)
    db.commit()
    event_bus.publish({"type": "group:changed", "action": "deleted", "group_id": group_id})


# ---- members ---------------------------------------------------------------


@router.post("/{group_id}/members", response_model=GroupMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    group_id: str,
    payload: GroupMemberIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupMemberOut:
    group = _load_group(db, group_id)
    require_organizer(group, user)

    if payload.user_id and any(m.user_id == payload.user_id for m in group.members):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user already in group")

    member = GroupMember(
        group_id=group.id,
        user_id=payload.user_id,
        display_name=payload.display_name,
        email=payload.email,
        role=payload.role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    event_bus.publish({"type": "group:changed", "action": "member_added", "group_id": group.id})
    return GroupMemberOut.model_validate(member)


@router.delete("/{group_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    group_id: str,
    member_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    group = _load_group(db, group_id)
    require_organizer(group, user)
    member = next((m for m in group.members if m.id == member_id), None)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")
    if member.role == GroupMemberRole.ORGANIZER and sum(1 for m in group.members if m.role == GroupMemberRole.ORGANIZER) == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot remove the sole organizer")
    db.delete(member)
    db.commit()
    event_bus.publish({"type": "group:changed", "action": "member_removed", "group_id": group.id})
