"""Ledger projection views (F-13).

Two views over identical underlying data:
  GET /api/groups/{id}/ledger       — organizer only, full audit matrix
  GET /api/groups/{id}/ledger/me    — participant scope, personal action items

Both enforce RBAC via `require_membership` / `require_organizer` so a
non-organizer who guesses the organizer URL gets a 403 (matches the F-13
acceptance criterion).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.group import Group, GroupMember
from app.models.ledger import Expense, PeerReimbursement
from app.models.user import User
from app.routers.groups import _load_group, require_membership, require_organizer
from app.schemas.ledger import (
    ExpenseLineForMe,
    ExpenseOut,
    MemberBalanceOut,
    OrganizerLedgerView,
    ParticipantLedgerView,
    ParticipantOwesReceives,
    ReimbursementOut,
    SettlementTransferOut,
)
from app.services.ledger import (
    compute_balances,
    min_cashflow_settlements,
)


router = APIRouter(prefix="/api/groups/{group_id}/ledger", tags=["ledger"])


def _load_full(db: Session, group: Group) -> tuple[list, list]:
    expenses = list(
        db.execute(
            select(Expense)
            .options(selectinload(Expense.participants))
            .where(Expense.group_id == group.id)
        )
        .scalars()
        .all()
    )
    reimbursements = list(
        db.execute(
            select(PeerReimbursement).where(PeerReimbursement.group_id == group.id)
        )
        .scalars()
        .all()
    )
    return expenses, reimbursements


@router.get("", response_model=OrganizerLedgerView)
def organizer_view(
    group_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizerLedgerView:
    group = _load_group(db, group_id)
    require_organizer(group, user)

    expenses, reimbursements = _load_full(db, group)
    snapshot = compute_balances(group.members, expenses, reimbursements)
    settlements = min_cashflow_settlements(snapshot)

    return OrganizerLedgerView(
        group_id=group.id,
        base_currency=group.base_currency,
        total_spend_base=snapshot.total_spend_base,
        total_reimbursed_base=snapshot.total_reimbursed_base,
        balances=[MemberBalanceOut(**b.__dict__, total_paid_out=b.total_paid_out, net_balance=b.net_balance) for b in snapshot.balances],
        settlements=[SettlementTransferOut(**s.__dict__) for s in settlements],
        expenses=[ExpenseOut.model_validate(e) for e in expenses],
        reimbursements=[ReimbursementOut.model_validate(r) for r in reimbursements],
    )


@router.get("/me", response_model=ParticipantLedgerView)
def participant_view(
    group_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ParticipantLedgerView:
    group = _load_group(db, group_id)
    me = require_membership(group, user)

    expenses, reimbursements = _load_full(db, group)
    snapshot = compute_balances(group.members, expenses, reimbursements)
    settlements = min_cashflow_settlements(snapshot)

    my_balance = next(b for b in snapshot.balances if b.member_id == me.id)
    display_by_id = {m.id: m.display_name for m in group.members}

    action_items: list[ParticipantOwesReceives] = []
    for s in settlements:
        if s.from_member_id == me.id:
            action_items.append(
                ParticipantOwesReceives(
                    counterpart_member_id=s.to_member_id,
                    counterpart_display_name=display_by_id.get(s.to_member_id, s.to_display_name),
                    amount_base=s.amount_base,
                    direction="owe",
                )
            )
        elif s.to_member_id == me.id:
            action_items.append(
                ParticipantOwesReceives(
                    counterpart_member_id=s.from_member_id,
                    counterpart_display_name=display_by_id.get(s.from_member_id, s.from_display_name),
                    amount_base=s.amount_base,
                    direction="receive",
                )
            )

    my_expenses: list[ExpenseLineForMe] = []
    for exp in expenses:
        my_line = next((p for p in exp.participants if p.member_id == me.id), None)
        paid_by_me = exp.payer_member_id == me.id
        if my_line is None and not paid_by_me:
            continue
        my_expenses.append(
            ExpenseLineForMe(
                expense_id=exp.id,
                title=exp.title,
                amount=float(exp.amount),
                currency=exp.currency,
                my_share_base=float(my_line.computed_amount_base) if my_line else 0.0,
                paid_by_me=paid_by_me,
                incurred_at=exp.incurred_at,
            )
        )
    my_expenses.sort(key=lambda x: x.incurred_at, reverse=True)

    return ParticipantLedgerView(
        group_id=group.id,
        base_currency=group.base_currency,
        me_member_id=me.id,
        my_balance=MemberBalanceOut(
            **my_balance.__dict__,
            total_paid_out=my_balance.total_paid_out,
            net_balance=my_balance.net_balance,
        ),
        action_items=action_items,
        my_expenses=my_expenses,
    )
