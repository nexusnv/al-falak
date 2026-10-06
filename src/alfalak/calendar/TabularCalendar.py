"""Tabular (arithmetic) Hijri calendar: Type IIa rule (phase 5).

Equivalent to the widely deployed "Kuwaiti algorithm" (arithmetic Type IIa),
the same leap pattern underlying e.g. Microsoft .NET ``HijriCalendar``
before per-install ``HijriAdjustment`` nudges; ``adjustment_days`` here
plays that nudge role.

Tabular dates routinely differ from observed (sighting-based) Hijri months
by +/-1-2 days. Never present tabular output as an observed/sighted date.
"""

import math
from datetime import date, datetime

from alfalak.astronomy.CalendricalHelper import julian_day
from alfalak.calendar.HijriCalendar import HijriCalendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.exceptions import ValidationError

# 1 Muharram 1 AH (civil day start) = 19 July 622 Gregorian proleptic.
_EPOCH_JD = 1948439.5

# Leap years within each 30-year cycle (Type IIa pattern: 11 leaps of
# 355 days per cycle, the al-Fazari/al-Khwarizmi/al-Battani pattern).
_LEAP_YEARS_IN_CYCLE = frozenset({2, 5, 7, 10, 13, 16, 18, 21, 24, 26, 29})

# Sibling arithmetic patterns, noted for context only and intentionally NOT
# implemented here: the Fatimid/Tayyibi (Ismaili) variant shifts some leap
# years within the 30-year cycle, the Habash al-Hasib / al-Biruni variant
# shifts others again, and the Ottoman 8-year cycle is a different
# construction altogether. This class is Type IIa only.


def _is_leap_year(year: int) -> bool:
    return (year % 30) in _LEAP_YEARS_IN_CYCLE


def _hijri_to_jd(year: int, month: int, day: int) -> float:
    """Julian Date of a tabular Hijri date (midnight start, .5 fraction)."""
    return (
        day
        + math.ceil(29.5 * (month - 1))
        + (year - 1) * 354
        + math.floor((3 + 11 * year) / 30)
        + _EPOCH_JD
        - 1
    )


def _jd_to_hijri(jd: float) -> HijriDate:
    """Tabular Hijri date for a Julian Date."""
    jd = math.floor(jd) + 0.5
    year = math.floor((30 * (jd - _EPOCH_JD) + 10646) / 10631)
    month = min(12, math.ceil((jd - (29 + _hijri_to_jd(year, 1, 1))) / 29.5) + 1)
    day = int(jd - _hijri_to_jd(year, month, 1) + 1)
    return HijriDate(year, month, day)


def _jd_to_gregorian(jd: float) -> date:
    """Proleptic Gregorian civil date for a Julian Date.

    Fliegel-Van Flandern inverse; proleptic by construction, matching
    ``CalendricalHelper.julian_day`` (which has no Julian-calendar branch).
    Out-of-range results (beyond ``date.min``/``date.max``) raise
    ``ValidationError``, never a bare ``ValueError``.
    """
    jdn = int(math.floor(jd + 0.5))
    v = jdn + 68569
    n = (4 * v) // 146097
    v = v - (146097 * n + 3) // 4
    i = (4000 * (v + 1)) // 1461001
    v = v - (1461 * i) // 4 + 31
    j = (80 * v) // 2447
    day = v - (2447 * j) // 80
    v = j // 11
    month = j + 2 - 12 * v
    year = 100 * (n - 49) + i + v
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise ValidationError(
            "TabularCalendar: Hijri date maps to Gregorian "
            f"{year}-{month:02d}-{day:02d}, outside the representable "
            f"Gregorian range ({exc})."
        ) from exc


class TabularCalendar(HijriCalendar):
    """Arithmetic Type IIa ("Kuwaiti") Hijri calendar.

    ``adjustment_days`` (int in [-2, 2], default 0) shifts the conversion
    by N days, playing the role of .NET ``HijriAdjustment`` for regional
    tabular corrections. See the module docstring for the +/-1-2 day
    tabular-vs-observed variance warning.
    """

    def __init__(self, adjustment_days: int = 0) -> None:
        if isinstance(adjustment_days, bool) or not isinstance(adjustment_days, int):
            raise ValidationError(
                "TabularCalendar 'adjustment_days' must be an int, "
                f"got {adjustment_days!r}."
            )
        if not -2 <= adjustment_days <= 2:
            raise ValidationError(
                "TabularCalendar 'adjustment_days' must be within [-2, 2], "
                f"got {adjustment_days}."
            )
        self._adjustment_days = adjustment_days

    @property
    def name(self) -> str:
        return "tabular"

    def month_length(self, year: int, month: int) -> int:
        if (
            isinstance(year, bool)
            or not isinstance(year, int)
            or isinstance(month, bool)
            or not isinstance(month, int)
        ):
            raise ValidationError(
                "TabularCalendar month_length needs int year/month, "
                f"got {year!r}, {month!r}."
            )
        if year < 1:
            raise ValidationError(f"TabularCalendar year must be >= 1, got {year}.")
        if not 1 <= month <= 12:
            raise ValidationError(
                f"TabularCalendar month must be within [1, 12], got {month}."
            )
        if month == 12:
            return 30 if _is_leap_year(year) else 29
        return 30 if month % 2 == 1 else 29

    def from_gregorian(self, d: date) -> HijriDate:
        if isinstance(d, datetime):
            raise ValidationError(
                "TabularCalendar needs a datetime.date (not a datetime); "
                f"pass d.date() or use gregorian_to_hijri, got {d!r}."
            )
        if not isinstance(d, date):
            raise ValidationError(f"TabularCalendar needs a datetime.date, got {d!r}.")
        jd = julian_day(d.year, d.month, d.day) + self._adjustment_days
        if jd < _EPOCH_JD:
            raise ValidationError(
                "TabularCalendar cannot convert Gregorian date "
                f"{d.isoformat()}: it predates 1 Muharram 1 AH "
                "(622-07-19 proleptic)."
            )
        return _jd_to_hijri(jd)

    def to_gregorian(self, h: HijriDate) -> date:
        if not isinstance(h, HijriDate):
            raise ValidationError(f"TabularCalendar needs a HijriDate, got {h!r}.")
        length = self.month_length(h.year, h.month)
        if h.day > length:
            raise ValidationError(
                f"TabularCalendar: day {h.day} exceeds the length "
                f"({length} days) of tabular month {h.month} "
                f"in year {h.year}."
            )
        jd = _hijri_to_jd(h.year, h.month, h.day) - self._adjustment_days
        return _jd_to_gregorian(jd)
