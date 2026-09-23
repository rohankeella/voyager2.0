"""Ledger math for P2 (Module 4).

Three responsibilities:

  1. `compute_splits`  — F-09 multi-strategy cost splitting. Given an
     expense (amount + strategy + participant list with share_values),
     returns each participant's owed amount in the group's base currency.
     Rounding drift is absorbed by the payer so the sum always matches
     the total to the cent.

  2. `compute_balances` — F-11 two-layer accounting. For each member,
     returns paid_to_vendors, owed_from_participation, reimbursements
     sent/received, and the final net balance (positive = they're owed,
     negative = they owe).

  3. `min_cashflow_settlements` — F-12 greedy netting. Reduces the N-node
     balance graph to at most N-1 directed transfers.

None of these functions touch the database; they operate on plain data
objects. The routers wire them up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from app.models.ledger import SplitStrategy


# --- 1. Split computation ---------------------------------------------------


def _q(x) -> Decimal:
    """Round to 2 decimal places, banker-safe."""
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class ParticipantSplitInput:
    member_id: str
    share_value: float | None = None


@dataclass
class ParticipantSplitOutput:
    member_id: str
    computed_amount_base: float


def compute_splits(
    total_amount: float,
    strategy: SplitStrategy,
    participants: list[ParticipantSplitInput],
    payer_member_id: str,
    fx_rate_to_base: float = 1.0,
) -> list[ParticipantSplitOutput]:
    """Split `total_amount` across participants under the given strategy.

    Raises `ValueError` on invalid inputs (empty participants, share
    validation failures, etc.) — routers translate that to 4xx.
    """
    if not participants:
        raise ValueError("expense must have at least one participant")

    total_base = _q(Decimal(str(total_amount)) * Decimal(str(fx_rate_to_base)))
    n = len(participants)

    if strategy == SplitStrategy.ORGANIZER_COVERED:
        return [ParticipantSplitOutput(p.member_id, 0.0) for p in participants]

    if strategy == SplitStrategy.EQUAL:
        even = (total_base / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        amounts = [even] * n
        drift = total_base - sum(amounts)
        amounts = _absorb_drift(amounts, drift, participants, payer_member_id)
        return [ParticipantSplitOutput(p.member_id, float(a)) for p, a in zip(participants, amounts)]

    if strategy == SplitStrategy.EXACT_AMOUNT:
        for p in participants:
            if p.share_value is None or p.share_value < 0:
                raise ValueError(f"EXACT_AMOUNT requires non-negative share_value on every participant")
        # Convert to base currency (share_values are entered in the expense currency).
        amounts = [_q(Decimal(str(p.share_value)) * Decimal(str(fx_rate_to_base))) for p in participants]
        if sum(amounts) != total_base:
            raise ValueError(
                f"EXACT_AMOUNT shares must sum to expense total: got {sum(amounts)} vs {total_base}"
            )
        return [ParticipantSplitOutput(p.member_id, float(a)) for p, a in zip(participants, amounts)]

    if strategy == SplitStrategy.PERCENTAGE:
        pcts = []
        for p in participants:
            if p.share_value is None or p.share_value < 0:
                raise ValueError("PERCENTAGE requires non-negative share_value on every participant")
            pcts.append(Decimal(str(p.share_value)))
        pct_total = sum(pcts)
        if abs(pct_total - Decimal(100)) > Decimal("0.01"):
            raise ValueError(f"PERCENTAGE shares must sum to 100 (got {pct_total})")
        amounts = [(total_base * pct / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for pct in pcts]
        drift = total_base - sum(amounts)
        amounts = _absorb_drift(amounts, drift, participants, payer_member_id)
        return [ParticipantSplitOutput(p.member_id, float(a)) for p, a in zip(participants, amounts)]

    if strategy == SplitStrategy.SHARE_WEIGHTED:
        weights = []
        for p in participants:
            if p.share_value is None or p.share_value <= 0:
                raise ValueError("SHARE_WEIGHTED requires positive share_value (weight) on every participant")
            weights.append(Decimal(str(p.share_value)))
        weight_total = sum(weights)
        amounts = [(total_base * w / weight_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for w in weights]
        drift = total_base - sum(amounts)
        amounts = _absorb_drift(amounts, drift, participants, payer_member_id)
        return [ParticipantSplitOutput(p.member_id, float(a)) for p, a in zip(participants, amounts)]

    raise ValueError(f"unknown split strategy: {strategy}")


def _absorb_drift(
    amounts: list[Decimal],
    drift: Decimal,
    participants: list[ParticipantSplitInput],
    payer_member_id: str,
) -> list[Decimal]:
    """Push any rounding remainder onto the payer's line so the sum matches
    the total exactly. Drift is at most a few cents."""
    if drift == 0:
        return amounts
    for i, p in enumerate(participants):
        if p.member_id == payer_member_id:
            amounts[i] += drift
            return amounts
    # Payer isn't a participant — dump drift onto the first line.
    amounts[0] += drift
    return amounts


# --- 2. Two-layer accounting ------------------------------------------------


@dataclass
class MemberBalance:
    member_id: str
    display_name: str
    paid_to_vendors: float = 0.0
    owed_from_participation: float = 0.0
    reimbursements_sent: float = 0.0
    reimbursements_received: float = 0.0

    @property
    def total_paid_out(self) -> float:
        """Layer-2 rollup — vendor payments + peer reimbursements sent."""
        return round(self.paid_to_vendors + self.reimbursements_sent, 2)

    @property
    def net_balance(self) -> float:
        # Positive: group owes them. Negative: they owe the group.
        return round(
            self.paid_to_vendors
            - self.owed_from_participation
            - self.reimbursements_received
            + self.reimbursements_sent,
            2,
        )


@dataclass
class LedgerSnapshot:
    balances: list[MemberBalance]
    total_spend_base: float
    total_reimbursed_base: float


def compute_balances(
    members: list,           # GroupMember ORM rows
    expenses: list,          # Expense ORM rows with .participants loaded
    reimbursements: list,    # PeerReimbursement ORM rows
) -> LedgerSnapshot:
    balances: dict[str, MemberBalance] = {
        m.id: MemberBalance(member_id=m.id, display_name=m.display_name) for m in members
    }

    total_spend = Decimal("0")
    for exp in expenses:
        amount_base = _q(Decimal(str(exp.amount)) * Decimal(str(exp.fx_rate_to_base)))
        total_spend += amount_base
        # Layer 2 (Asset): the payer fronted this to a vendor.
        if exp.payer_member_id in balances:
            balances[exp.payer_member_id].paid_to_vendors = float(
                _q(Decimal(str(balances[exp.payer_member_id].paid_to_vendors)) + amount_base)
            )
        # Layer 1 (Liability): each participant owes their computed share.
        for part in exp.participants:
            if part.member_id in balances:
                balances[part.member_id].owed_from_participation = float(
                    _q(
                        Decimal(str(balances[part.member_id].owed_from_participation))
                        + Decimal(str(part.computed_amount_base))
                    )
                )

    total_reimbursed = Decimal("0")
    for r in reimbursements:
        amt = Decimal(str(r.amount_base))
        total_reimbursed += amt
        if r.from_member_id in balances:
            balances[r.from_member_id].reimbursements_sent = float(
                _q(Decimal(str(balances[r.from_member_id].reimbursements_sent)) + amt)
            )
        if r.to_member_id in balances:
            balances[r.to_member_id].reimbursements_received = float(
                _q(Decimal(str(balances[r.to_member_id].reimbursements_received)) + amt)
            )

    return LedgerSnapshot(
        balances=list(balances.values()),
        total_spend_base=float(total_spend),
        total_reimbursed_base=float(total_reimbursed),
    )


# --- 3. Min-cash-flow settlement solver -------------------------------------


@dataclass
class SettlementTransfer:
    from_member_id: str
    from_display_name: str
    to_member_id: str
    to_display_name: str
    amount_base: float


def min_cashflow_settlements(snapshot: LedgerSnapshot) -> list[SettlementTransfer]:
    """Greedy net-balance matching (F-12). Produces at most N-1 transfers
    for N members. Guaranteed to zero-out balances up to floating-point
    rounding (we clamp anything within a cent to zero)."""
    # Copy so we can mutate.
    working = [(b.member_id, b.display_name, round(b.net_balance, 2)) for b in snapshot.balances]
    transfers: list[SettlementTransfer] = []

    while True:
        # Debtors (negative balance) and creditors (positive)
        debtors = [(i, w) for i, w in enumerate(working) if w[2] < -0.01]
        creditors = [(i, w) for i, w in enumerate(working) if w[2] > 0.01]
        if not debtors or not creditors:
            break

        di, (d_id, d_name, d_bal) = min(debtors, key=lambda t: t[1][2])          # most negative
        ci, (c_id, c_name, c_bal) = max(creditors, key=lambda t: t[1][2])         # most positive
        settle_amount = round(min(-d_bal, c_bal), 2)
        transfers.append(
            SettlementTransfer(
                from_member_id=d_id,
                from_display_name=d_name,
                to_member_id=c_id,
                to_display_name=c_name,
                amount_base=settle_amount,
            )
        )
        working[di] = (d_id, d_name, round(d_bal + settle_amount, 2))
        working[ci] = (c_id, c_name, round(c_bal - settle_amount, 2))

    return transfers
