"""Tests for gregorian_to_hijri sunset bridge (phase-5 task 4)."""

from datetime import datetime, timedelta, timezone

import pytest

from alfalak.calculation.CalculationMethod import CalculationMethod
from alfalak.calculation.CalculationParameters import CalculationParameters
from alfalak.calculation.PolarCircleRule import PolarCircleRule
from alfalak.calendar.HijriCalendar import HijriCalendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.calendar.TabularCalendar import TabularCalendar
from alfalak.calendar.bridge import gregorian_to_hijri
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AstronomicalError, ConfigurationError
from alfalak.PrayerTimes import PrayerTimes

# Fixed witness: Kuala Lumpur (tropical, Maghrib always well-defined).
KL = Coordinates(3.1390, 101.6869)
DAY = datetime(2025, 3, 15, 12, 0, tzinfo=timezone.utc)
PARAMS = CalculationParameters(method=CalculationMethod.JAKIM)


def _maghrib() -> datetime:
    # Only the date part feeds prayer computation (PrayerTimes takes the
    # civil date via DateComponents.from_utc); the wall-clock of DAY is
    # irrelevant here.
    return PrayerTimes(KL, DAY, calculation_parameters=PARAMS).maghrib


def test_bridge_maghrib_minus5_plus5_successive_when_on() -> None:
    cal = TabularCalendar()
    maghrib = _maghrib()
    before = gregorian_to_hijri(
        maghrib - timedelta(minutes=5),
        calendar=cal,
        coordinates=KL,
        params=PARAMS,
        change_at_sunset=True,
    )
    after = gregorian_to_hijri(
        maghrib + timedelta(minutes=5),
        calendar=cal,
        coordinates=KL,
        params=PARAMS,
        change_at_sunset=True,
    )
    civil = maghrib.date()
    assert before == cal.from_gregorian(civil)
    assert after == cal.from_gregorian(civil + timedelta(days=1))
    # Successive Hijri days: the round-tripped civil dates differ by one day.
    assert cal.to_gregorian(after) - cal.to_gregorian(before) == timedelta(days=1)


def test_bridge_same_day_when_off() -> None:
    cal = TabularCalendar()
    maghrib = _maghrib()
    before = gregorian_to_hijri(
        maghrib - timedelta(minutes=5),
        calendar=cal,
        coordinates=KL,
        params=PARAMS,
        change_at_sunset=False,
    )
    after = gregorian_to_hijri(
        maghrib + timedelta(minutes=5),
        calendar=cal,
        coordinates=KL,
        params=PARAMS,
        change_at_sunset=False,
    )
    assert before == after == cal.from_gregorian(maghrib.date())


def test_bridge_change_at_sunset_without_coordinates_raises() -> None:
    with pytest.raises(ConfigurationError):
        gregorian_to_hijri(DAY, calendar=TabularCalendar(), change_at_sunset=True)


def test_bridge_naive_treated_as_utc() -> None:
    # DOCUMENTED: naive datetimes are normalized as UTC
    # (dt.replace(tzinfo=timezone.utc)). A naive datetime carrying *local*
    # wall-clock time therefore misplaces Maghrib by the UTC offset — pass
    # aware datetimes when change_at_sunset=True.
    cal = TabularCalendar()
    maghrib = _maghrib()
    aware = maghrib - timedelta(minutes=5)
    naive = aware.replace(tzinfo=None)
    assert naive.tzinfo is None
    assert gregorian_to_hijri(
        naive,
        calendar=cal,
        coordinates=KL,
        params=PARAMS,
        change_at_sunset=True,
    ) == gregorian_to_hijri(
        aware,
        calendar=cal,
        coordinates=KL,
        params=PARAMS,
        change_at_sunset=True,
    )


def test_bridge_polar_maghrib_propagates() -> None:
    # Longyearbyen on the June solstice: polar day, no sunset. With
    # PolarCircleRule.NONE the Maghrib lookup raises AstronomicalError and
    # the bridge must let it propagate unwrapped (no fallback).
    polar = Coordinates(78.2232, 15.6267)
    day = datetime(2025, 6, 21, 12, 0, tzinfo=timezone.utc)
    params = CalculationParameters(
        method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
        polar_circle_rule=PolarCircleRule.NONE,
    )
    with pytest.raises(AstronomicalError):
        gregorian_to_hijri(
            day,
            calendar=TabularCalendar(),
            coordinates=polar,
            params=params,
            change_at_sunset=True,
        )


def test_bridge_offsets_applied_last_via_duck_typing() -> None:
    # OffsetStore (Task 5) does not exist yet: the bridge only requires an
    # object with an apply(hijri, calendar) method (duck-typing).
    calls: list[tuple[HijriDate, HijriCalendar]] = []

    class _StubOffsets:
        def apply(self, hijri: HijriDate, calendar: HijriCalendar) -> HijriDate:
            calls.append((hijri, calendar))
            return hijri

    cal = TabularCalendar()
    result = gregorian_to_hijri(
        DAY, calendar=cal, offsets=_StubOffsets(), change_at_sunset=False
    )
    assert result == cal.from_gregorian(DAY.date())
    assert calls == [(result, cal)]
