"""Tests for TabularCalendar (Type IIa) (phase-5 task 1)."""

import random
from datetime import date, timedelta

import pytest

from alfalak.calendar import HijriDate, TabularCalendar
from alfalak.exceptions import ValidationError

SEED = 20261005
N_ROUNDTRIP = 300

START = date(1900, 1, 1)
END = date(2100, 12, 31)


def _sample_dates(n: int) -> list[date]:
    rng = random.Random(SEED)
    start_ord = START.toordinal()
    span = END.toordinal() - start_ord
    return [date.fromordinal(start_ord + rng.randrange(span + 1)) for _ in range(n)]


def _shift_hijri(cal: TabularCalendar, h: HijriDate, n: int) -> HijriDate:
    """Shift a Hijri date by n Hijri days using the calendar's month lengths."""
    year, month, day = h.year, h.month, h.day
    step = 1 if n >= 0 else -1
    for _ in range(abs(n)):
        day += step
        if day > cal.month_length(year, month):
            if month == 12:
                year, month, day = year + 1, 1, 1
            else:
                month, day = month + 1, 1
        elif day < 1:
            if month == 1:
                year, month = year - 1, 12
            else:
                month -= 1
            day = cal.month_length(year, month)
    return HijriDate(year, month, day)


def test_tabular_roundtrip_1900_2100() -> None:
    cal = TabularCalendar()
    for d in _sample_dates(N_ROUNDTRIP):
        h = cal.from_gregorian(d)
        assert cal.to_gregorian(h) == d
        # Hijri -> Gregorian -> Hijri direction on the same witness.
        assert cal.from_gregorian(cal.to_gregorian(h)) == h


def test_tabular_roundtrip_holds_under_adjustment() -> None:
    for adjustment in (1, -2):
        cal = TabularCalendar(adjustment_days=adjustment)
        for d in _sample_dates(100):
            assert cal.to_gregorian(cal.from_gregorian(d)) == d


def test_tabular_leap_set_11_per_30() -> None:
    cal = TabularCalendar()
    expected = {2, 5, 7, 10, 13, 16, 18, 21, 24, 26, 29}
    for cycle_start in (1, 31, 1411):
        leaps = [
            y
            for y in range(cycle_start, cycle_start + 30)
            if cal.month_length(y, 12) == 30
        ]
        assert len(leaps) == 11
        assert {y - cycle_start + 1 for y in leaps} == expected
    # Odd months are 30 days, even months 29; Dhu al-Hijjah pins leap state.
    for month in range(1, 12):
        assert cal.month_length(1446, month) == (30 if month % 2 == 1 else 29)
    assert cal.month_length(1446, 12) == 29  # 1446 % 30 == 6, common year.
    assert cal.month_length(1447, 12) == 30  # 1447 % 30 == 7, leap year.


def test_tabular_ramadan_1446_anchor_is_tabular_value() -> None:
    cal = TabularCalendar()
    # 1 Ramadan 1446 (tabular) = 2025-03-01. Observed Saudi 1 Ramadan 1446
    # was also 2025-03-01 (sighting Friday evening 28 Feb 2025); that
    # agreement is coincidence, not proof — tabular arithmetic carries a
    # routine +/-1-2 day variance vs observed months and must never be
    # presented as a sighting.
    assert cal.from_gregorian(date(2025, 3, 1)) == HijriDate(1446, 9, 1)
    assert cal.to_gregorian(HijriDate(1446, 9, 1)) == date(2025, 3, 1)


@pytest.mark.parametrize("adjustment", [1, -2])
def test_adjustment_plus1_minus2_shifts_exactly(adjustment: int) -> None:
    base = TabularCalendar()
    shifted = TabularCalendar(adjustment_days=adjustment)
    witnesses = [
        date(2025, 3, 1),  # 1 Ramadan 1446 tabular.
        date(2025, 3, 30),  # near a tabular month boundary.
        date(2024, 2, 29),  # Gregorian leap day.
        date(2000, 1, 1),
        date(1900, 1, 1),
    ]
    for d in witnesses:
        h0 = base.from_gregorian(d)
        assert shifted.from_gregorian(d) == _shift_hijri(base, h0, adjustment)
        assert shifted.to_gregorian(h0) == base.to_gregorian(h0) - timedelta(
            days=adjustment
        )


@pytest.mark.parametrize("bad", [3, -3, 100])
def test_tabular_rejects_adjustment_outside_range(bad: int) -> None:
    with pytest.raises(ValidationError):
        TabularCalendar(adjustment_days=bad)


def test_tabular_rejects_non_int_adjustment() -> None:
    with pytest.raises(ValidationError):
        TabularCalendar(adjustment_days=1.5)  # type: ignore[arg-type]


def test_tabular_to_gregorian_rejects_30th_of_29_day_month() -> None:
    cal = TabularCalendar()
    # Safar is always 29 days; Dhu al-Hijjah 1446 is 29 (common year).
    with pytest.raises(ValidationError):
        cal.to_gregorian(HijriDate(1446, 2, 30))
    with pytest.raises(ValidationError):
        cal.to_gregorian(HijriDate(1446, 12, 30))


def test_tabular_epoch_boundary() -> None:
    cal = TabularCalendar()
    assert cal.from_gregorian(date(622, 7, 19)) == HijriDate(1, 1, 1)
    assert cal.to_gregorian(HijriDate(1, 1, 1)) == date(622, 7, 19)
    with pytest.raises(ValidationError):
        cal.from_gregorian(date(622, 7, 18))


def test_tabular_month_length_rejects_bad_inputs() -> None:
    cal = TabularCalendar()
    with pytest.raises(ValidationError):
        cal.month_length(1446, 13)
    with pytest.raises(ValidationError):
        cal.month_length(0, 1)
    with pytest.raises(ValidationError):
        cal.month_length("1446", 1)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(1446, "1")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(True, 1)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(1446, False)  # type: ignore[arg-type]


def test_tabular_from_gregorian_rejects_non_date() -> None:
    cal = TabularCalendar()
    with pytest.raises(ValidationError):
        cal.from_gregorian("2025-03-01")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.from_gregorian(None)  # type: ignore[arg-type]


def test_tabular_to_gregorian_rejects_non_hijri() -> None:
    cal = TabularCalendar()
    with pytest.raises(ValidationError):
        cal.to_gregorian("1446-09-01")  # type: ignore[arg-type]
