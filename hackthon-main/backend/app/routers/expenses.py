"""Expenses + reimbursements CRUD (P2 - F-08 / F-09 / F-10 / F-11).

Every create/update path runs `compute_splits` and stores the results as
ExpenseParticipant.computed_amount_base — that's F-10 (reactive recalc)
implemented as "always recompute on write" instead of a separate event
loop. Simpler, and the guarantee is stronger: any successful write leaves
the ledger consistent."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.group import Group, GroupMember
from app.models.ledger import Expense, ExpenseParticipant, PeerReimbursement
from app.models.user import User
from app.routers.groups import _load_group, require_membership
from app.schemas.ledger import (
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    ReimbursementCreate,
    ReimbursementOut,
)
from app.services.events import event_bus
from app.services.ledger import ParticipantSplitInput, compute_splits


router = APIRouter(prefix="/api/groups/{group_id}", tags=["ledger"])


def _member_ids(group: Group) -> set[str]:
    return {m.id for m in group.members}


def _validate_members(group: Group, member_ids: list[str]) -> None:
    ids = _member_ids(group)
    unknown = [mid for mid in member_ids if mid not in ids]
    if unknown:
        raise HTTPException(status_code=400, detail=f"member ids not in this group: {unknown}")


def _apply_splits_to_orm(expense: Expense, participants_in: list, computed: list) -> None:
    """Rebuild the expense.participants collection so `share_value` +
    `computed_amount_base` are always in sync with the strategy."""
    by_member = {p.member_id: p for p in computed}
    expense.participants.clear()
    for p_in in participants_in:
        c = by_member[p_in.member_id]
        expense.participants.append(
            ExpenseParticipant(
                member_id=p_in.member_id,
                share_value=p_in.share_value,
                computed_amount_base=c.computed_amount_base,
            )
        )


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    group_id: str,
    payload: ExpenseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpenseOut:
    group = _load_group(db, group_id)
    require_membership(group, user)

    _validate_members(group, [payload.payer_member_id] + [p.member_id for p in payload.participants])

    try:
        computed = compute_splits(
            total_amount=payload.amount,
            strategy=payload.split_strategy,
            participants=[ParticipantSplitInput(p.member_id, p.share_value) for p in payload.participants],
            payer_member_id=payload.payer_member_id,
            fx_rate_to_base=payload.fx_rate_to_base,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    expense = Expense(
        group_id=group.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        amount=payload.amount,
        currency=payload.currency,
        fx_rate_to_base=payload.fx_rate_to_base,
        payer_member_id=payload.payer_member_id,
        split_strategy=payload.split_strategy,
        incurred_at=payload.incurred_at,
    )
    _apply_splits_to_orm(expense, payload.participants, computed)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    event_bus.publish({"type": "ledger:changed", "action": "expense_created", "group_id": group.id})
    return ExpenseOut.model_validate(expense)


@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    group_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExpenseOut]:
    group = _load_group(db, group_id)
    require_membership(group, user)
    rows = (
        db.execute(
            select(Expense)
            .options(selectinload(Expense.participants))
            .where(Expense.group_id == group.id)
            .order_by(Expense.incurred_at.desc())
        )
        .scalars()
        .all()
    )
    return [ExpenseOut.model_validate(r) for r in rows]


@router.patch("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(
    group_id: str,
    expense_id: str,
    payload: ExpenseUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpenseOut:
    group = _load_group(db, group_id)
    require_membership(group, user)
    expense = db.execute(
        select(Expense)
        .options(selectinload(Expense.participants))
        .where(Expense.id == expense_id, Expense.group_id == group.id)
    ).scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="expense not found")

    for f in ("title", "description", "category", "currency", "incurred_at"):
        v = getattr(payload, f)
        if v is not None:
            setattr(expense, f, v)
    if payload.amount is not None:
        expense.amount = payload.amount
    if payload.fx_rate_to_base is not None:
        expense.fx_rate_to_base = payload.fx_rate_to_base
    if payload.payer_member_id is not None:
        _validate_members(group, [payload.payer_member_id])
        expense.payer_member_id = payload.payer_member_id
    if payload.split_strategy is not None:
        expense.split_strategy = payload.split_strategy

    # Recompute splits if anything touching them changed OR the caller
    # explicitly passed a new participant list.
    participants_in = payload.participants
    if participants_in is None:
        participants_in = [
            type("P", (), {"member_id": p.member_id, "share_value": p.share_value})()  # type: ignore[misc]
            for p in expense.participants
        ]
    _validate_members(group, [p.member_id for p in participants_in])
    try:
        computed = compute_splits(
            total_amount=float(expense.amount),
            strategy=expense.split_strategy,
            participants=[ParticipantSplitInput(p.member_id, p.share_value) for p in participants_in],
            payer_member_id=expense.payer_member_id,
            fx_rate_to_base=float(expense.fx_rate_to_base),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _apply_splits_to_orm(expense, participants_in, computed)

    db.commit()
    db.refresh(expense)
    event_bus.publish({"type": "ledger:changed", "action": "expense_updated", "group_id": group.id})
    return ExpenseOut.model_validate(expense)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    group_id: str,
    expense_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    group = _load_group(db, group_id)
    require_membership(group, user)
    expense = db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.group_id == group.id)
    ).scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="expense not found")
    db.delete(expense)
    db.commit()
    event_bus.publish({"type": "ledger:changed", "action": "expense_deleted", "group_id": group.id})


# ---- reimbursements --------------------------------------------------------


@router.post("/reimbursements", response_model=ReimbursementOut, status_code=status.HTTP_201_CREATED)
def create_reimbursement(
    group_id: str,
    payload: ReimbursementCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReimbursementOut:
    group = _load_group(db, group_id)
    require_membership(group, user)
    if payload.from_member_id == payload.to_member_id:
        raise HTTPException(status_code=400, detail="from and to must be different members")
    _validate_members(group, [payload.from_member_id, payload.to_member_id])

    row = PeerReimbursement(
        group_id=group.id,
        from_member_id=payload.from_member_id,
        to_member_id=payload.to_member_id,
        amount_base=payload.amount_base,
        note=payload.note,
        settled_at=payload.settled_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    event_bus.publish({"type": "ledger:changed", "action": "reimbursement_created", "group_id": group.id})
    return ReimbursementOut.model_validate(row)


@router.get("/reimbursements", response_model=list[ReimbursementOut])
def list_reimbursements(
    group_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReimbursementOut]:
    group = _load_group(db, group_id)
    require_membership(group, user)
    rows = (
        db.execute(
            select(PeerReimbursement)
            .where(PeerReimbursement.group_id == group.id)
            .order_by(PeerReimbursement.settled_at.desc())
        )
        .scalars()
        .all()
    )
    return [ReimbursementOut.model_validate(r) for r in rows]


@router.delete("/reimbursements/{reimbursement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reimbursement(
    group_id: str,
    reimbursement_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    group = _load_group(db, group_id)
    require_membership(group, user)
    row = db.execute(
        select(PeerReimbursement).where(
            PeerReimbursement.id == reimbursement_id, PeerReimbursement.group_id == group.id
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="reimbursement not found")
    db.delete(row)
    db.commit()
    event_bus.publish({"type": "ledger:changed", "action": "reimbursement_deleted", "group_id": group.id})
