"""Real household solar production and consumption, replacing the synthetic
random/formula-based values this project used to generate.

Source: Ausgrid "Solar home electricity data" - 300 real Sydney households,
half-hourly metered production (GG) and consumption (GC), 1 Jul 2010 - 30 Jun
2011. Originally published by Ausgrid under CC BY 3.0 Australia; Ausgrid's own
hosting of it has since gone offline (confirmed: 404 as of Oct 2026) - this
project ships a small subset (data/ausgrid_subset.json.gz, 36 of the 300
households, the ones with zero missing days in the source year) extracted from
an archival mirror of the original CC-BY-licensed files, preserving their
original 2014-2017 timestamps. See README for the full provenance chain.

Why this replaces the sine-curve solar_factor() and random.uniform() consumption
from the previous version: those modeled *what a plausible household might do*;
this replays *what a real household actually did*, half-hour by half-hour. The
zero-at-night behavior, the day-to-day variation, the exact magnitude - all of
it is now a real measurement, not an estimate.

Hemisphere caveat (the one real limitation worth stating plainly): Ausgrid's
households are in Sydney, Australia - Southern Hemisphere. This project's price
data (eu-power-poc) is for the Netherlands - Northern Hemisphere. Sydney's
summer is Amsterdam's winter. To avoid replaying summer-strength solar output
during a real NL winter (which would contradict the real NL price signal this
project also uses), every lookup date is shifted by 6 months before indexing
into the Ausgrid year, so "today, in NL" maps to the Ausgrid date that sits in
the equivalent point of *its own* seasonal cycle. This is a deliberate,
documented transformation, not an attempt to pass off Sydney weather as Dutch
weather - the absolute values are still the real household's real measurements,
just time-shifted to the matching season.
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import date, datetime, timedelta

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "ausgrid_subset.json.gz")

_dataset: dict | None = None


def _load() -> dict:
    global _dataset
    if _dataset is None:
        with gzip.open(_DATA_PATH, "rt") as f:
            _dataset = json.load(f)
    return _dataset


def assigned_customer_id(community_id: int, house_id: int) -> str:
    """Deterministic, fixed mapping from this project's (community, house) slots
    to one of the 36 real Ausgrid customers shipped in the subset. Communities
    1-9 x houses 1-4 = 36 slots, matching the 36 customers exactly - every slot
    gets its own distinct real household, none shared or reused."""
    dataset = _load()
    customer_ids = sorted(dataset["customers"].keys(), key=int)
    index = (community_id - 1) * 4 + (house_id - 1)
    return customer_ids[index % len(customer_ids)]


def _season_shifted_date(real_date: date) -> date:
    """Shift by ~6 months (182 days) so Sydney's seasonal cycle lines up with
    the Northern Hemisphere's, then map into the single real year the dataset
    covers (2010-07-01 .. 2011-06-30) by matching month/day."""
    shifted = real_date + timedelta(days=182)
    # Map onto the dataset's single real year by month/day, choosing whichever
    # of the two years the data spans puts that month/day inside range.
    for year in (2010, 2011):
        is_feb_29 = shifted.month == 2 and shifted.day == 29
        candidate = date(year, 2, 28) if is_feb_29 else date(year, shifted.month, shifted.day)
        if date(2010, 7, 1) <= candidate <= date(2011, 6, 30):
            return candidate
    # Fallback (shouldn't happen: every month/day falls in range for one of the two years)
    return date(2010, 7, 1)


def _half_hour_index(dt: datetime) -> int:
    """0 = "0:30" (the first 30 minutes after midnight) .. 47 = "0:00" (the last
    half hour before the next midnight), matching the dataset's own column order."""
    minutes_since_midnight = dt.hour * 60 + dt.minute
    return min(minutes_since_midnight // 30, 47)


def real_value_kwh(community_id: int, house_id: int, category: str, now: datetime) -> float:
    """category: "GC" (consumption) or "GG" (solar generation). `now` should be
    the current real time in the timezone this simulation treats as local
    (Europe/Amsterdam) - see producer-sync.py / consumer-sync.py."""
    dataset = _load()
    customer_id = assigned_customer_id(community_id, house_id)
    lookup_date = _season_shifted_date(now.date())
    half_hour = _half_hour_index(now)

    day_values = dataset["customers"][customer_id][category].get(lookup_date.isoformat())
    if day_values is None:
        return 0.0  # shouldn't happen for the 36 shipped customers (all 365 days present)
    return day_values[half_hour]
