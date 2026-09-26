"""F-28 · Policy-Aware Rule Engine.

Given a `PlanAction` targeting a node, return the monetary and reputation
penalty of executing it. The recovery scorer folds these into its overall
Penalty so plans that only touch refundable bookings are naturally
preferred over plans that rewrite non-refundable ones.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.graph import ItineraryNode, RefundClass


REFUND_PENALTY_MULTIPLIER: dict[RefundClass, float] = {
    RefundClass.FULLY_REFUNDABLE:     0.0,   # nothing lost — clean cancel
    RefundClass.PARTIALLY_REFUNDABLE: 0.5,   # roughly half the sunk cost is unrecoverable
    RefundClass.NON_REFUNDABLE:       1.0,   # full sunk cost + potential rebooking premium
}


@dataclass
class PolicyEvaluation:
    node_id: str
    action: str
    monetary_penalty: float
    forfeited_cost: float
    change_fee: float
    note: str


def evaluate_cancellation(node: ItineraryNode) -> PolicyEvaluation:
    mult = REFUND_PENALTY_MULTIPLIER.get(node.refund_class, 1.0)
    forfeited = round(float(node.cost) * mult, 2)
    return PolicyEvaluation(
        node_id=node.id,
        action="CANCEL",
        monetary_penalty=forfeited,
        forfeited_cost=forfeited,
        change_fee=0.0,
        note=f"{node.refund_class.value}: {int(mult*100)}% of cost forfeited on cancel.",
    )


def evaluate_modification(node: ItineraryNode) -> PolicyEvaluation:
    """A modification (reschedule / re-route) typically only costs the
    change fee — unless the vendor is non-refundable, in which case
    modifications tend to charge like a partial cancel."""
    fee = float(node.change_fee)
    if node.refund_class == RefundClass.NON_REFUNDABLE:
        # Practical rule: non-refundable modifications lose 30% of cost on top of any fee.
        forfeited = round(float(node.cost) * 0.3, 2)
        return PolicyEvaluation(
            node_id=node.id,
            action="MODIFY",
            monetary_penalty=round(fee + forfeited, 2),
            forfeited_cost=forfeited,
            change_fee=fee,
            note="Non-refundable modification: change fee + 30% sunk cost.",
        )
    return PolicyEvaluation(
        node_id=node.id,
        action="MODIFY",
        monetary_penalty=fee,
        forfeited_cost=0.0,
        change_fee=fee,
        note=f"{node.refund_class.value}: change fee only.",
    )


def evaluate_shift(node: ItineraryNode) -> PolicyEvaluation:
    """A shift is a schedule adjustment without a formal modification — no
    monetary cost, just downstream time impact."""
    return PolicyEvaluation(
        node_id=node.id,
        action="SHIFT",
        monetary_penalty=0.0,
        forfeited_cost=0.0,
        change_fee=0.0,
        note="Schedule shift — no vendor interaction required.",
    )
