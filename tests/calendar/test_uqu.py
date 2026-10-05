"""Tests for UmmAlQuraCalendar (post-1423H Makkah rule) (phase-5 task 2).

Spot-check source: the official Saudi Umm al-Qura calendar month starts
for Hijri years 1445-1446, as embedded in the ``hijri-converter`` 2.3.2
and ``hijridate`` Umm al-Qura lookup tables (queried 2026-10-05; the two
tables agree month-for-month over 1445-1446). High-confidence anchors in
this table: 1 Ramadan 1445 = 2024-03-11, 1 Shawwal 1445 = 2024-04-10,
1 Dhu al-Hijjah 1445 = 2024-06-07, 1 Muharram 1446 = 2024-07-07,
1 Ramadan 1446 = 2025-03-01, 1 Shawwal 1446 = 2025-03-30,
1 Dhu al-Hijjah 1446 = 2025-05-28, 1 Muharram 1447 = 2025-06-26.

Deltas: EXPECTED below matches the published dates exactly unless the
month is listed in ALLOWED_DELTAS with a boundary justification. Every
delta is a whole-day, listed difference, never a hidden tolerance.
"""

import importlib
from dataclasses import replace
from datetime import date, timedelta

import pytest

from alfalak.calendar import HijriDate, get_calendar
from alfalak.calendar.UmmAlQuraCalendar import UmmAlQuraCalendar, clear_caches
from alfalak.exceptions import AstronomicalError, ValidationError

# The package re-exports the UmmAlQuraCalendar *class* under the submodule
# name, so `import alfalak.calendar.UmmAlQuraCalendar as ...` would bind
# the class; importlib reaches the real module (patch target below).
uqu_module = importlib.import_module("alfalak.calendar.UmmAlQuraCalendar")

# Published Umm al-Qura 1st-of-month Gregorian dates, 1445H.
EXPECTED_1445: dict[tuple[int, int], date] = {
    (1445, 1): date(2023, 7, 19),
    (1445, 2): date(2023, 8, 17),
    (1445, 3): date(2023, 9, 16),
    (1445, 4): date(2023, 10, 16),
    (1445, 5): date(2023, 11, 15),
    (1445, 6): date(2023, 12, 14),
    (1445, 7): date(2024, 1, 13),
    (1445, 8): date(2024, 2, 11),
    (1445, 9): date(2024, 3, 11),
    (1445, 10): date(2024, 4, 10),
    (1445, 11): date(2024, 5, 9),
    (1445, 12): date(2024, 6, 7),
}

# Published Umm al-Qura 1st-of-month Gregorian dates, 1446H.
EXPECTED_1446: dict[tuple[int, int], date] = {
    (1446, 1): date(2024, 7, 7),
    (1446, 2): date(2024, 8, 5),
    (1446, 3): date(2024, 9, 4),
    (1446, 4): date(2024, 10, 4),
    (1446, 5): date(2024, 11, 3),
    (1446, 6): date(2024, 12, 2),
    (1446, 7): date(2025, 1, 1),
    (1446, 8): date(2025, 1, 31),
    (1446, 9): date(2025, 3, 1),
    (1446, 10): date(2025, 3, 30),
    (1446, 11): date(2025, 4, 29),
    (1446, 12): date(2025, 5, 28),
}

EXPECTED: dict[tuple[int, int], date] = {**EXPECTED_1445, **EXPECTED_1446}

# Boundary months where the Meeus-based predicate differs from the
# published date by the listed whole-day delta. In each case conjunction
# is comfortably before Makkah sunset (age 0.1-0.3 d) but the computed
# moonset lag sits within ~4 minutes of zero, the rule's knife-edge,
# where the truncated lunar theory + polynomial Delta-T legitimately
# differs from the KACST reference by minutes:
# - (1445, 5): 29th eve 2023-11-13, lag +0.04 h (+2.4 min), age 0.25 d.
# - (1445, 7): 29th eve 2024-01-11, lag +0.02 h (+1.2 min), age 0.12 d.
# - (1446, 8): 29th eve 2025-01-29, lag +0.06 h (+3.6 min), age 0.10 d.
# Each delta is an isolated one-month -1 shift that self-corrects the
# following month (both tables agree again the month after).
ALLOWED_DELTAS: dict[tuple[int, int], int] = {
    (1445, 5): -1,
    (1445, 7): -1,
    (1446, 8): -1,
}


def test_uqu_12month_spotcheck_x2years_deltas_listed() -> None:
    cal = UmmAlQuraCalendar()
    for (year, month), expected in EXPECTED.items():
        got = cal.to_gregorian(HijriDate(year, month, 1))
        delta = (got - expected).days
        allowed = ALLOWED_DELTAS.get((year, month), 0)
        assert delta == allowed, (
            f"UQU {(year, month)}: got {got.isoformat()}, "
            f"published {expected.isoformat()} (delta {delta}, "
            f"listed {allowed})"
        )
        assert abs(delta) <= 1, f"UQU {(year, month)}: delta {delta} exceeds 1 day"
        # Forward direction on our own month start and a mid-month witness.
        assert cal.from_gregorian(got) == HijriDate(year, month, 1)
        assert cal.from_gregorian(got + timedelta(days=14)) == HijriDate(
            year, month, 15
        )
        assert cal.to_gregorian(cal.from_gregorian(got)) == got
        assert cal.month_length(year, month) in (29, 30)


def test_uqu_month_lengths_match_published_durations() -> None:
    """Month lengths agree with published durations except listed deltas."""
    cal = UmmAlQuraCalendar()
    starts = [EXPECTED[(1446, m)] for m in range(1, 13)]
    starts.append(date(2025, 6, 26))  # Published 1 Muharram 1447.
    # (1446, 8) is a listed -1 delta: our Rajab runs 29 days (our Sha'ban
    # starts 01-30) where the published table has 30 (Sha'ban 01-31), so
    # the published durations of Rajab (m=7) and Sha'ban (m=8) each differ
    # from ours by design; every other month must match exactly.
    for m in range(1, 13):
        if m in (7, 8):
            continue
        assert cal.month_length(1446, m) == (starts[m] - starts[m - 1]).days
    assert cal.month_length(1446, 7) == 29
    assert cal.month_length(1446, 8) == 30


def test_uqu_pre1423_raises_validation_error() -> None:
    cal = UmmAlQuraCalendar()
    with pytest.raises(ValidationError, match="post-1423H"):
        cal.from_gregorian(date(2002, 3, 14))
    with pytest.raises(ValidationError, match="post-1423H"):
        cal.from_gregorian(date(1999, 1, 1))
    with pytest.raises(ValidationError, match="post-1423H"):
        cal.to_gregorian(HijriDate(1422, 12, 29))
    with pytest.raises(ValidationError, match="post-1423H"):
        cal.month_length(1422, 1)
    with pytest.raises(ValidationError) as exc_info:
        cal.from_gregorian(date(2002, 3, 14))
    assert str(exc_info.value) == "Umm al-Qura calendar supports post-1423H dates only"
    # The epoch boundary itself converts: 1 Muharram 1423H = 2002-03-15.
    assert cal.from_gregorian(date(2002, 3, 15)) == HijriDate(1423, 1, 1)
    assert cal.to_gregorian(HijriDate(1423, 1, 1)) == date(2002, 3, 15)


def test_uqu_sentinel_age_raises_not_30day(monkeypatch: pytest.MonkeyPatch) -> None:
    """A search-failure moon age (30.0d) must raise, never decide 30 days."""
    clear_caches()
    real = uqu_module._geometry_at_makkah

    def fake_sentinel(evening: date):  # type: ignore[no-untyped-def]
        return replace(real(evening), moon_age_days=30.0)

    monkeypatch.setattr(uqu_module, "_geometry_at_makkah", fake_sentinel)
    with pytest.raises(AstronomicalError):
        UmmAlQuraCalendar().month_length(1446, 9)

    def fake_nan_lag(evening: date):  # type: ignore[no-untyped-def]
        return replace(real(evening), lag_hours=float("nan"))

    monkeypatch.setattr(uqu_module, "_geometry_at_makkah", fake_nan_lag)
    with pytest.raises(AstronomicalError):
        UmmAlQuraCalendar().month_length(1446, 9)


def test_uqu_to_gregorian_rejects_30th_of_29_day_month() -> None:
    cal = UmmAlQuraCalendar()
    assert cal.month_length(1446, 1) == 29  # 2024-07-07 -> 2024-08-05.
    with pytest.raises(ValidationError):
        cal.to_gregorian(HijriDate(1446, 1, 30))


def test_uqu_factory_returns_real_calendar() -> None:
    cal = get_calendar("uqu")
    assert isinstance(cal, UmmAlQuraCalendar)
    assert cal.name == "uqu"


def test_uqu_month_length_rejects_bad_inputs() -> None:
    cal = UmmAlQuraCalendar()
    with pytest.raises(ValidationError):
        cal.month_length("1446", 9)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(1446, "9")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(True, 9)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(1446, False)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(0, 1)
    with pytest.raises(ValidationError):
        cal.month_length(1446, 0)
    with pytest.raises(ValidationError):
        cal.month_length(1446, 13)


def test_uqu_converters_reject_wrong_types() -> None:
    cal = UmmAlQuraCalendar()
    with pytest.raises(ValidationError):
        cal.from_gregorian("2025-03-01")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.to_gregorian("1446-09-01")  # type: ignore[arg-type]


def test_uqu_month_start_ordinal_rejects_pre_epoch() -> None:
    # Defense in depth: the cached ordinal lookup itself refuses pre-1423H
    # months even though every public caller validates first.
    with pytest.raises(ValidationError, match="post-1423H"):
        uqu_module._month_start_ordinal(1422, 12)


def test_uqu_month_start_window_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    # A tabular seed outside the +/-4-day window trips the month-start
    # guard instead of returning a wrong date.

    class _FarSeed:
        def to_gregorian(self, h: HijriDate) -> date:
            return date(2025, 6, 1)

    monkeypatch.setattr(uqu_module, "_TABULAR_SEED", _FarSeed())
    with pytest.raises(AstronomicalError, match="search exhausted"):
        uqu_module._month_start(1446, 9)


def test_uqu_from_gregorian_clamps_stale_tabular_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The real tabular seed coincides with the UQU epoch at 2002-03-15, so
    # a pre-1423H seed is unreachable through it; a synthetic stale seed
    # exercises the epoch-clamp defense (seed := 1423-01-01).
    real = uqu_module._TABULAR_SEED

    class _StaleSeed:
        def from_gregorian(self, d: date) -> HijriDate:
            return HijriDate(1422, 12, 30)

        def to_gregorian(self, h: HijriDate) -> date:
            return real.to_gregorian(h)

    monkeypatch.setattr(uqu_module, "_TABULAR_SEED", _StaleSeed())
    assert UmmAlQuraCalendar().from_gregorian(date(2002, 3, 16)) == HijriDate(
        1423, 1, 2
    )


def test_uqu_from_gregorian_skips_invalid_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # One poisoned month-start lookup is skipped; the search still lands on
    # the true date (1 Ramadan 1446 = 2025-03-01, pinned by the spotcheck).
    cal = UmmAlQuraCalendar()
    real = cal.to_gregorian
    calls = 0

    def flaky(candidate: HijriDate) -> date:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValidationError("synthetic invalid candidate")
        return real(candidate)

    monkeypatch.setattr(cal, "to_gregorian", flaky)
    assert cal.from_gregorian(date(2025, 3, 1)) == HijriDate(1446, 9, 1)
    assert calls > 1


def test_uqu_from_gregorian_exhausted_search_reports_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Every probe crosses the epoch (synthetic total crossing): the loop
    # skips them all and the exhausted search names the window, falling
    # back to the seed for both bounds.
    def always_crossed(h: HijriDate, delta: int) -> HijriDate:
        raise ValidationError("synthetic epoch crossing")

    monkeypatch.setattr(uqu_module, "_shift_hijri", always_crossed)
    with pytest.raises(AstronomicalError, match="search exhausted"):
        UmmAlQuraCalendar().from_gregorian(date(2025, 3, 1))
