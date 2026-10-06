"""Umm al-Qura Hijri calendar: Makkah moonset rule, post-1423H (phase 5).

This is a *calendar* (Gregorian <-> Hijri date conversion under the
published Umm al-Qura month-start rule). It is not the prayer preset
``CalculationMethod.UMM_AL_QURA`` (Fajr 18.5 degrees, 90/120-minute Isha),
which only tunes daily prayer times and never converts calendar dates.

Rule (van Gent / KACST, in force since 1423H / 15 Mar 2002): on the 29th
of each Hijri month, if geocentric conjunction occurred before Makkah
sunset AND the moon sets after Makkah sunset, the next day is the 1st of
the new month; otherwise the month completes 30 days. The reference is
Makkah (``MAKKAH`` from ``data/Constants.py``), never a prayer site.

Rule history (cited, not implemented): earlier Umm al-Qura variants (the
1392H scheme and the 1420-1422H interim criteria) used different
moonset/elongation conditions and are explicitly out of scope. Only the
1423H rule is implemented; any input mapping before the 1423H epoch
(Gregorian 2002-03-15, 1 Muharram 1423H) raises ``ValidationError`` with
the deferred message instead of returning a wrong date.

Like every observational rule, Umm al-Qura month starts routinely differ
from tabular (arithmetic) dates by +/-1-2 days. Never present Umm al-Qura
output as a tabular date or vice versa.
"""

from __future__ import annotations

import math
import warnings
from datetime import date, datetime, timedelta
from functools import lru_cache

from alfalak.astronomy.CrescentGeometry import (
    CrescentGeometry,
    crescent_geometry_at_sunset,
)
from alfalak.calendar.HijriCalendar import HijriCalendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.calendar.TabularCalendar import TabularCalendar
from alfalak.data.Constants import MAKKAH
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AstronomicalError, ValidationError

_CALENDAR_KEY = "uqu"

# First civil date under the current (1423H) rule: 1 Muharram 1423H.
_EPOCH_GREGORIAN = date(2002, 3, 15)
_EPOCH_HIJRI_YEAR = 1423
_EPOCH_HIJRI_MONTH = 1

_DEFERRED_MESSAGE = "Umm al-Qura calendar supports post-1423H dates only"

# Tabular-vs-observed divergence is routinely +/-1-2 days; the search
# window is twice that and is never extended silently.
_WINDOW_DAYS = 4

# Conjunction-before-sunset side discriminator (not a visibility
# threshold): post-conjunction age on a 29th evening is 0-30 h while a
# pre-conjunction evening still shows ~28.5-29.5 d.
_MOON_AGE_SIDE_DAYS = 15.0

# ``_moon_age_days`` reports exactly 30.0 on search failure; a real
# 29th-evening age is a multiple of the hourly sampling step and can
# never approach this closely, so anything within eps is the sentinel.
_MOON_AGE_SENTINEL_EPS = 1e-6

_MAX_MONTH_START_CACHE = 2048
_MAX_GEOMETRY_CACHE = 4096

_TABULAR_SEED = TabularCalendar()


@lru_cache(maxsize=_MAX_GEOMETRY_CACHE)
def _cached_geometry(date_iso: str, lat: float, lon: float) -> CrescentGeometry:
    """Sunset geometry for an ISO date at rounded (lat, lon).

    Keys are strings and rounded floats only, never raw floats or live
    ``Coordinates`` objects (which are mutable).
    """
    return crescent_geometry_at_sunset(
        date.fromisoformat(date_iso), Coordinates(lat, lon)
    )


def _geometry_at_makkah(evening: date) -> CrescentGeometry:
    """29th-evening geometry at Makkah (patch point for tests)."""
    return _cached_geometry(
        evening.isoformat(),
        round(MAKKAH.latitude, 4),
        round(MAKKAH.longitude, 4),
    )


def clear_caches() -> None:
    """Drop the Umm al-Qura month-start and geometry caches (test hook)."""
    _cached_geometry.cache_clear()
    _month_start_ordinal.cache_clear()


def _decide_month_length(evening: date) -> int:
    """Apply the 1423H rule to a 29th evening at Makkah: 29 or 30 days."""
    # The anchored walk routinely evaluates pre-2005 evenings, where the
    # shared delta_t polynomial extrapolates past its calibration range.
    # That extrapolation warning is expected here (the published-table
    # goldens already calibrate the rule against it), so it is scoped off
    # for this call only; every other warning still propagates.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*delta_t polynomial is calibrated.*",
            category=UserWarning,
        )
        geometry = _geometry_at_makkah(evening)
    iso = evening.isoformat()
    if math.isnan(geometry.lag_hours):
        raise AstronomicalError(
            f"Umm al-Qura ('{_CALENDAR_KEY}') cannot decide the month: "
            f"moonset lag is NaN at Makkah on {iso} (no moonset computed)."
        )
    if math.isnan(geometry.moon_age_days) or geometry.moon_age_days >= (
        30.0 - _MOON_AGE_SENTINEL_EPS
    ):
        raise AstronomicalError(
            f"Umm al-Qura ('{_CALENDAR_KEY}') cannot decide the month: "
            f"moon age {geometry.moon_age_days} days at Makkah on {iso} "
            "is the conjunction-search failure sentinel, not a 30-day month."
        )
    if geometry.lag_hours > 0.0 and geometry.moon_age_days < _MOON_AGE_SIDE_DAYS:
        return 29
    return 30


@lru_cache(maxsize=_MAX_MONTH_START_CACHE)
def _month_start_ordinal(year: int, month: int) -> int:
    """Ordinal of the 1st of a Hijri month via the anchored walk.

    Recursive single-step forward chain from the 1423H epoch: every
    intermediate month start lands in the cache, so a full-year sweep
    costs one rule evaluation per month. Callers must validate
    ``(year, month)`` first; months before the 1423H anchor raise
    ``ValidationError`` here as defense in depth. Deep (far from epoch)
    targets go through ``_resolve_month_start`` instead to bound stack use.
    """
    if (year, month) < (_EPOCH_HIJRI_YEAR, _EPOCH_HIJRI_MONTH):
        raise ValidationError(_DEFERRED_MESSAGE)
    if (year, month) == (_EPOCH_HIJRI_YEAR, _EPOCH_HIJRI_MONTH):
        return _EPOCH_GREGORIAN.toordinal()
    prev_year, prev_month = _prev_month(year, month)
    prev_start = _month_start_ordinal(prev_year, prev_month)
    return prev_start + _decide_month_length(date.fromordinal(prev_start + 28))


def _month_distance_from_epoch(year: int, month: int) -> int:
    return (year - _EPOCH_HIJRI_YEAR) * 12 + (month - _EPOCH_HIJRI_MONTH)


# Recursion headroom: the cached chain resolves one stack frame per
# month from the epoch; beyond this distance the driver walks
# iteratively instead (mirrors MabimsCalendar's 500-month headroom).
_MAX_CACHED_WALK_MONTHS = 500


def _resolve_month_start(year: int, month: int) -> int:
    """Ordinal of the 1st of a Hijri month, bounding recursion depth.

    Near-epoch targets use the cached chain; far targets walk
    iteratively forward from the epoch (geometry stays cached,
    intermediate month starts are not retained). Pre-epoch inputs raise
    ``ValidationError`` (deferred).
    """
    if (year, month) < (_EPOCH_HIJRI_YEAR, _EPOCH_HIJRI_MONTH):
        raise ValidationError(_DEFERRED_MESSAGE)
    if _month_distance_from_epoch(year, month) <= _MAX_CACHED_WALK_MONTHS:
        return _month_start_ordinal(year, month)
    start = _EPOCH_GREGORIAN.toordinal()
    walk_year, walk_month = _EPOCH_HIJRI_YEAR, _EPOCH_HIJRI_MONTH
    while (walk_year, walk_month) != (year, month):
        start += _decide_month_length(date.fromordinal(start + 28))
        walk_year, walk_month = _next_month(walk_year, walk_month)
    return start


def _month_start(year: int, month: int) -> date:
    """True month start, window-checked against the tabular seed."""
    start = date.fromordinal(_resolve_month_start(year, month))
    seed = _TABULAR_SEED.to_gregorian(HijriDate(year, month, 1))
    lower = seed - timedelta(days=_WINDOW_DAYS)
    upper = seed + timedelta(days=_WINDOW_DAYS)
    if not lower <= start <= upper:
        raise AstronomicalError(
            f"Umm al-Qura ('{_CALENDAR_KEY}') month-start search exhausted: "
            f"month {year}-{month:02d} starts {start.isoformat()}, outside "
            f"the +-{_WINDOW_DAYS}-day window "
            f"[{lower.isoformat()}..{upper.isoformat()}] around tabular "
            f"seed {seed.isoformat()}."
        )
    return start


def _validate_year_month(year: int, month: int) -> None:
    if (
        isinstance(year, bool)
        or not isinstance(year, int)
        or isinstance(month, bool)
        or not isinstance(month, int)
    ):
        raise ValidationError(
            "UmmAlQuraCalendar month_length needs int year/month, "
            f"got {year!r}, {month!r}."
        )
    if year < 1:
        raise ValidationError(f"UmmAlQuraCalendar year must be >= 1, got {year}.")
    if not 1 <= month <= 12:
        raise ValidationError(
            f"UmmAlQuraCalendar month must be within [1, 12], got {month}."
        )


def _uqu_month_length(year: int, month: int) -> int:
    """Shared month-length core for the class and Hijri-day shifting."""
    _validate_year_month(year, month)
    if (year, month) < (_EPOCH_HIJRI_YEAR, _EPOCH_HIJRI_MONTH):
        raise ValidationError(_DEFERRED_MESSAGE)
    return _decide_month_length(_month_start(year, month) + timedelta(days=28))


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _shift_hijri(h: HijriDate, delta: int) -> HijriDate:
    """Shift a Hijri date by ``delta`` Hijri days (UQU month lengths).

    Probes crossing the 1423H epoch raise the deferred ``ValidationError``;
    callers skip such candidates.
    """
    year, month, day = h.year, h.month, h.day
    step = 1 if delta >= 0 else -1
    for _ in range(abs(delta)):
        day += step
        if step > 0:
            if day > _uqu_month_length(year, month):
                year, month = _next_month(year, month)
                day = 1
        elif day < 1:
            year, month = _prev_month(year, month)
            day = _uqu_month_length(year, month)
    return HijriDate(year, month, day)


class UmmAlQuraCalendar(HijriCalendar):
    """Observational Umm al-Qura calendar (1423H rule at Makkah).

    Distinct from the ``CalculationMethod.UMM_AL_QURA`` prayer preset;
    see the module docstring. Supported range starts at 1 Muharram 1423H
    (Gregorian 2002-03-15); earlier inputs raise ``ValidationError``.
    """

    @property
    def name(self) -> str:
        return "uqu"

    def month_length(self, year: int, month: int) -> int:
        return _uqu_month_length(year, month)

    def to_gregorian(self, h: HijriDate) -> date:
        if not isinstance(h, HijriDate):
            raise ValidationError(f"UmmAlQuraCalendar needs a HijriDate, got {h!r}.")
        if (h.year, h.month) < (_EPOCH_HIJRI_YEAR, _EPOCH_HIJRI_MONTH):
            raise ValidationError(_DEFERRED_MESSAGE)
        length = _uqu_month_length(h.year, h.month)
        if h.day > length:
            raise ValidationError(
                f"Umm al-Qura ('{_CALENDAR_KEY}'): day {h.day} exceeds "
                f"the length ({length} days) of month {h.month} "
                f"in year {h.year}."
            )
        return _month_start(h.year, h.month) + timedelta(days=h.day - 1)

    def from_gregorian(self, d: date) -> HijriDate:
        if isinstance(d, datetime):
            raise ValidationError(
                "UmmAlQuraCalendar needs a datetime.date (not a datetime); "
                f"pass d.date() or use gregorian_to_hijri, got {d!r}."
            )
        if not isinstance(d, date):
            raise ValidationError(
                f"UmmAlQuraCalendar needs a datetime.date, got {d!r}."
            )
        if d < _EPOCH_GREGORIAN:
            raise ValidationError(_DEFERRED_MESSAGE)
        tabular = _TABULAR_SEED.from_gregorian(d)
        if (tabular.year, tabular.month) < (_EPOCH_HIJRI_YEAR, _EPOCH_HIJRI_MONTH):
            seed = HijriDate(_EPOCH_HIJRI_YEAR, _EPOCH_HIJRI_MONTH, 1)
        else:
            seed = HijriDate(
                tabular.year,
                tabular.month,
                min(tabular.day, _uqu_month_length(tabular.year, tabular.month)),
            )
        for offset in range(-_WINDOW_DAYS, _WINDOW_DAYS + 1):
            try:
                candidate = _shift_hijri(seed, offset)
            except ValidationError:
                continue  # Probe crossed the 1423H epoch; skip it.
            try:
                if self.to_gregorian(candidate) == d:
                    return candidate
            except ValidationError:
                continue
        try:
            first = _shift_hijri(seed, -_WINDOW_DAYS)
        except ValidationError:
            first = seed
        try:
            last = _shift_hijri(seed, _WINDOW_DAYS)
        except ValidationError:
            last = seed
        raise AstronomicalError(
            f"Umm al-Qura ('{_CALENDAR_KEY}') month-start search exhausted: "
            f"no Hijri date within +-{_WINDOW_DAYS} days of tabular seed "
            f"{seed.isoformat()} (Gregorian {d.isoformat()}) maps to "
            f"{d.isoformat()}; window bounds "
            f"{first.isoformat()}..{last.isoformat()}."
        )
