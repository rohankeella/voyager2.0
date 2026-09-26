"""F-18: Event Staggering & Route Optimizer.

Given a scheduled event and a total headcount to disperse, generate a set of
time-banded departure windows spaced enough that no single band overwhelms
the transit capacity feeding the zone. Deliberately simple: uniform bands
around the event end time, sized by an operator-configurable
`max_per_band`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class DepartureBand:
    label: str
    start_at: datetime
    end_at: datetime
    assigned_headcount: int


def generate_staggered_departures(
    event_end_at: datetime,
    total_attendees: int,
    max_per_band: int = 200,
    band_minutes: int = 15,
    pre_end_bands: int = 1,
) -> list[DepartureBand]:
    """Produce band recommendations centred on `event_end_at`.

    `pre_end_bands` = 1 means the first band starts `band_minutes` before
    the event ends (early birds), then subsequent bands each shifted by
    `band_minutes`. Each band is capped at `max_per_band` — if the crowd
    doesn't fit we simply add more bands rather than raising cap.
    """
    if total_attendees <= 0:
        return []
    n_bands = max(1, (total_attendees + max_per_band - 1) // max_per_band)
    n_bands = max(n_bands, 2)  # never a single band — staggering requires ≥ 2

    bands: list[DepartureBand] = []
    remaining = total_attendees
    for i in range(n_bands):
        # Bands run pre_end -> post_end. i=0 is `pre_end_bands` bands before end.
        offset = i - pre_end_bands
        start = event_end_at + timedelta(minutes=offset * band_minutes)
        end = start + timedelta(minutes=band_minutes)
        assigned = min(max_per_band, remaining)
        remaining -= assigned
        bands.append(
            DepartureBand(
                label=chr(ord("A") + i),
                start_at=start,
                end_at=end,
                assigned_headcount=assigned,
            )
        )
        if remaining <= 0:
            break
    return bands
