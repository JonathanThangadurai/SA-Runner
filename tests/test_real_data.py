"""Verifies real_data.py against known values hand-checked against the raw
Ausgrid source CSV, and the season-shift / hemisphere logic that makes the
replay consistent with the Netherlands' actual seasons."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

import real_data
from real_data import _half_hour_index, _season_shifted_date, assigned_customer_id, real_value_kwh

NL = ZoneInfo("Europe/Amsterdam")


def test_known_value_matches_raw_ausgrid_csv():
    # Customer 1, GC, 2010-07-01, first half-hour value - hand-verified against
    # the raw "Solar home 2010-2011.csv" row for Customer 1 on that date.
    dataset = real_data._load()
    assert dataset["customers"]["1"]["GC"]["2010-07-01"][0] == pytest.approx(0.303)


def test_36_house_slots_map_to_36_distinct_customers():
    ids = {assigned_customer_id(c, h) for c in range(1, 10) for h in range(1, 5)}
    assert len(ids) == 36


def test_season_shift_maps_nl_summer_to_sydney_summer_equivalent():
    # NL mid-July (NL summer) must land in the Jan 2011 half of the dataset
    # (Sydney's real summer), not the Jul 2010 half (Sydney's real winter) -
    # otherwise a real NL summer day would replay a real Sydney *winter* day.
    shifted = _season_shifted_date(date(2026, 7, 15))
    assert shifted.month == 1

    # and the reverse: NL mid-January (NL winter) lands in Sydney's winter (July)
    shifted_winter = _season_shifted_date(date(2026, 1, 15))
    assert shifted_winter.month == 7


def test_half_hour_index_covers_full_day_without_gaps_or_overlap():
    minutes_to_check = (0, 15, 29, 30, 45, 59)
    indices = {
        _half_hour_index(datetime(2026, 1, 1, h, m)) for h in range(24) for m in minutes_to_check
    }
    assert indices == set(range(48))


def test_solar_generation_is_real_zero_at_night_and_positive_at_nl_summer_midday():
    night = real_value_kwh(1, 1, "GG", datetime(2026, 1, 15, 2, 0, tzinfo=NL))
    assert night == 0.0

    midday = real_value_kwh(1, 1, "GG", datetime(2026, 7, 15, 13, 0, tzinfo=NL))
    assert midday > 0.0


def test_consumption_lookup_returns_a_real_recorded_value_not_a_formula():
    value = real_value_kwh(2, 3, "GC", datetime(2026, 3, 1, 9, 0, tzinfo=NL))
    assert value >= 0.0
    # A second call for the identical moment must return the identical real
    # value - this is a deterministic replay, not a random draw.
    value_again = real_value_kwh(2, 3, "GC", datetime(2026, 3, 1, 9, 0, tzinfo=NL))
    assert value == value_again
