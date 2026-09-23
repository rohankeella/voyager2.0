"""F-20: Incentive-Driven Nudge System.

Given an active nudge pool and a balancer recommendation (from-zone ->
to-zone), pick the highest-signal nudge to attach. Preference order:

  1. Nudges targeting the recommended `to_zone_id` explicitly
  2. Priority passes (higher perceived value than discounts)
  3. Discounts
  4. Badges (gamification fallback)

Expired or inactive nudges are filtered out before ranking.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.capacity import Nudge, NudgeKind


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


_KIND_PRIORITY = {NudgeKind.PRIORITY_PASS: 3, NudgeKind.DISCOUNT: 2, NudgeKind.BADGE: 1}


def pick_nudge_for_zone(active_nudges: list[Nudge], to_zone_id: str, now: datetime | None = None) -> Nudge | None:
    now = now or datetime.now(timezone.utc)
    fresh = [
        n for n in active_nudges
        if n.is_active and (n.expires_at is None or _as_utc(n.expires_at) > now)
    ]
    if not fresh:
        return None

    zone_targeted = [n for n in fresh if n.target_zone_id == to_zone_id]
    generic = [n for n in fresh if n.target_zone_id is None]

    pool = zone_targeted or generic
    if not pool:
        return None
    pool.sort(key=lambda n: _KIND_PRIORITY.get(n.kind, 0), reverse=True)
    return pool[0]
