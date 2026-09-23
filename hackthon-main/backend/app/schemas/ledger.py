from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ledger import SplitStrategy


class ExpenseParticipantIn(BaseModel):
    member_id: str
    share_value: float | None = None


class ExpenseParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    member_id: str
    share_value: float | None
    computed_amount_base: float


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    fx_rate_to_base: float = Field(default=1.0, gt=0)
    payer_member_id: str
    split_strategy: SplitStrategy = SplitStrategy.EQUAL
    participants: list[ExpenseParticipantIn]
    incurred_at: datetime | None = None


class ExpenseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    amount: float | None = None
    currency: str | None = None
    fx_rate_to_base: float | None = None
    payer_member_id: str | None = None
    split_strategy: SplitStrategy | None = None
    participants: list[ExpenseParticipantIn] | None = None
    incurred_at: datetime | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_id: str
    title: str
    description: str | None
    category: str | None
    amount: float
    currency: str
    fx_rate_to_base: float
    payer_member_id: str
    split_strategy: SplitStrategy
    incurred_at: datetime
    created_at: datetime
    participants: list[ExpenseParticipantOut]


class ReimbursementCreate(BaseModel):
    from_member_id: str
    to_member_id: str
    amount_base: float = Field(gt=0)
    note: str | None = None
    settled_at: datetime | None = None


class ReimbursementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_id: str
    from_member_id: str
    to_member_id: str
    amount_base: float
    note: str | None
    settled_at: datetime


# ---- ledger projections (F-13) --------------------------------------------


class MemberBalanceOut(BaseModel):
    member_id: str
    display_name: str
    paid_to_vendors: float
    owed_from_participation: float
    reimbursements_sent: float
    reimbursements_received: float
    total_paid_out: float
    net_balance: float


class SettlementTransferOut(BaseModel):
    from_member_id: str
    from_display_name: str
    to_member_id: str
    to_display_name: str
    amount_base: float


class OrganizerLedgerView(BaseModel):
    """Full audit-grade view — organizer only."""

    group_id: str
    base_currency: str
    total_spend_base: float
    total_reimbursed_base: float
    balances: list[MemberBalanceOut]
    settlements: list[SettlementTransferOut]
    expenses: list[ExpenseOut]
    reimbursements: list[ReimbursementOut]


class ParticipantOwesReceives(BaseModel):
    counterpart_member_id: str
    counterpart_display_name: str
    amount_base: float
    direction: str  # "owe" | "receive"


class ExpenseLineForMe(BaseModel):
    expense_id: str
    title: str
    amount: float
    currency: str
    my_share_base: float
    paid_by_me: bool
    incurred_at: datetime


class ParticipantLedgerView(BaseModel):
    """Personal, scoped view — non-organizers use this."""

    group_id: str
    base_currency: str
    me_member_id: str
    my_balance: MemberBalanceOut
    action_items: list[ParticipantOwesReceives]
    my_expenses: list[ExpenseLineForMe]
