"""MABIMS Hijri calendar: Neo-MABIMS 2021 rule at per-country proxies (phase 5).

Rule: on the 29th evening of each Hijri month, evaluated at local sunset
at the country's national-proxy reference via
``crescent_geometry_at_sunset`` + ``is_neo_mabims_2021`` (altitude >= 3.0
degrees and elongation >= 6.4 degrees): met -> the new month starts the
next day (29-day month), else the month completes 30 days.

The four references are national PROXIES pinned at 4 dp for v1, not
per-zone truth (Malaysia alone spans 60+ prayer zones; Indonesia spans
three time zones with 30+ rukyat points). Official announcements fold in
zone observations and actual sighting reports, so computed dates may
differ from announced dates by +/-1 day; see the delta tests.

Superseded predecessor (migration context only, NOT implemented): the
1992 Labuan MABIMS rule (altitude >= 2 degrees and elongation >= 3
degrees, or moon age >= 8 hours). Neo-MABIMS 2021 (KBIR 2016, adopted
2021) tightens both sunset thresholds to 3.0 / 6.4 degrees.

Month starts resolve by walking forward from a fixed anchor
(1 Muharram 1445H = 19 July 2023 Gregorian, observed in all four member
countries) applying the rule month by month. The walk is forward-only:
like UQU's 1423H epoch, the anchor is the support floor, and any input
mapping before it raises ``ValidationError`` (deferred) instead of
walking backward — a backward single-probe rule cannot reconstruct the
true 29th evening (a visible 30th evening is indistinguishable from a
visible 29th), so backward walking systematically misreads 30-day
months as 29-day ones. Intermediate results cache in bounded
``functools.lru_cache`` tables (see ``clear_mabims_cache``).
"""

import functools
from datetime import date, datetime

from alfalak.astronomy.CrescentGeometry import (
    CrescentGeometry,
    crescent_geometry_at_sunset,
)
from alfalak.astronomy.Mabims import is_neo_mabims_2021
from alfalak.calendar.HijriCalendar import HijriCalendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.calendar.TabularCalendar import TabularCalendar
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import (
    AstronomicalError,
    ConfigurationError,
    ValidationError,
)

# National-proxy references, pinned at 4 dp for v1. Documented as
# proxies, not per-zone truth (see module docstring).
_COUNTRY_REFS: dict[str, Coordinates] = {
    "MY": Coordinates(3.1390, 101.6869),  # Kuala Lumpur
    "ID": Coordinates(-6.2088, 106.8456),  # Jakarta
    "BN": Coordinates(4.8903, 114.9420),  # Bandar Seri Begawan
    "SG": Coordinates(1.3521, 103.8198),  # Singapore
}

_VALID_COUNTRIES = frozenset(_COUNTRY_REFS)

# Anchor: 1 Muharram 1445H = 19 July 2023 (Gregorian civil date).
# The anchor is the support floor: the walk is forward-only (mirror UQU's
# 1423H epoch), and pre-anchor inputs raise ValidationError (deferred).
_ANCHOR_YEAR = 1445
_ANCHOR_MONTH = 1
_ANCHOR_GREGORIAN = date(2023, 7, 19)

_DEFERRED_MESSAGE = "MABIMS calendar supports post-1445 dates only"

# Tabular seed for the containing-month search (same floor as tabular).
_TABULAR_SEED = TabularCalendar()

# Recursion headroom: the cached chain resolves one stack frame per
# month from the anchor; beyond this distance the driver walks
# iteratively instead. Test/golden dates sit ~40 months past the anchor.
_MAX_CACHED_WALK_MONTHS = 500


@functools.lru_cache(maxsize=4096)
def _sunset_geometry_cached(day_ordinal: int, country: str) -> CrescentGeometry:
    """Sunset geometry at the country proxy for a Gregorian date.

    Keyed by proleptic ordinal + country code: no raw-float keys.
    Polar ``AstronomicalError`` propagates unwrapped (impossible at the
    tropical proxies, but never swallowed if it ever fires).
    """
    return crescent_geometry_at_sunset(
        date.fromordinal(day_ordinal), _COUNTRY_REFS[country]
    )


def _neo_visible(evening_ordinal: int, country: str) -> bool:
    """Neo-MABIMS 2021 predicate on a 29th-evening at the country proxy."""
    geometry = _sunset_geometry_cached(evening_ordinal, country)
    return is_neo_mabims_2021(geometry.moon_alt_topo_deg, geometry.arcl_deg)


def _forward_month_length(start_ordinal: int, country: str) -> int:
    """Length of the month starting on ``start_ordinal`` (29 or 30)."""
    return 29 if _neo_visible(start_ordinal + 28, country) else 30


def _previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


@functools.lru_cache(maxsize=4096)
def _month_start_ordinal(country: str, year: int, month: int) -> int:
    """Gregorian ordinal of Hijri day 1 for ``(country, year, month)``.

    Recursive single-step forward chain from the anchor: every
    intermediate month start lands in the cache, so a full-year sweep
    costs one rule evaluation per month. Months before the anchor raise
    ``ValidationError`` here as defense in depth. Deep (far from anchor)
    targets go through ``resolve_month_start`` instead to bound stack use.
    """
    if (year, month) < (_ANCHOR_YEAR, _ANCHOR_MONTH):
        raise ValidationError(_DEFERRED_MESSAGE)
    if year == _ANCHOR_YEAR and month == _ANCHOR_MONTH:
        return _ANCHOR_GREGORIAN.toordinal()
    prev_year, prev_month = _previous_month(year, month)
    prev_start = _month_start_ordinal(country, prev_year, prev_month)
    return prev_start + _forward_month_length(prev_start, country)


def _month_distance_from_anchor(year: int, month: int) -> int:
    return (year - _ANCHOR_YEAR) * 12 + (month - _ANCHOR_MONTH)


def resolve_month_start(country: str, year: int, month: int) -> int:
    """Gregorian ordinal of Hijri day 1, bounding recursion depth.

    Near-anchor targets use the cached chain; far targets walk
    iteratively forward from the anchor (geometry stays cached,
    intermediate month starts are not retained). Pre-anchor inputs raise
    ``ValidationError`` (deferred); unknown countries raise
    ``ConfigurationError`` (never a bare ``KeyError``).
    """
    if not isinstance(country, str) or country.upper() not in _VALID_COUNTRIES:
        raise ConfigurationError(
            f"Unknown MABIMS country {country!r}. "
            f"Expected one of {sorted(_VALID_COUNTRIES)}."
        )
    country = country.upper()
    if (year, month) < (_ANCHOR_YEAR, _ANCHOR_MONTH):
        raise ValidationError(_DEFERRED_MESSAGE)
    if abs(_month_distance_from_anchor(year, month)) <= (_MAX_CACHED_WALK_MONTHS):
        return _month_start_ordinal(country, year, month)
    current = _ANCHOR_GREGORIAN.toordinal()
    cy, cm = _ANCHOR_YEAR, _ANCHOR_MONTH
    while (cy, cm) < (year, month):
        current += _forward_month_length(current, country)
        cy, cm = _next_month(cy, cm)
    return current


def clear_mabims_cache() -> None:
    """Drop all cached MABIMS geometry and month-start results (tests)."""
    _sunset_geometry_cached.cache_clear()
    _month_start_ordinal.cache_clear()


class MabimsCalendar(HijriCalendar):
    """Neo-MABIMS 2021 observational Hijri calendar for one country.

    ``country`` is required, case-insensitive, normalized to upper;
    anything outside ``{"MY", "ID", "BN", "SG"}`` raises
    ``ConfigurationError``. Supported range starts at 1 Muharram 1445H
    (Gregorian 2023-07-19, the walk anchor); earlier inputs raise
    ``ValidationError`` (deferred). The old 1992 Labuan rule is not
    implemented (see module docstring).
    """

    def __init__(self, country: str | None = None) -> None:
        if not isinstance(country, str) or not country:
            raise ConfigurationError(
                "MabimsCalendar requires a 'country' " "(one of MY, ID, BN, SG)."
            )
        normalized = country.upper()
        if normalized not in _VALID_COUNTRIES:
            raise ConfigurationError(
                f"Unknown MABIMS country {country!r}. "
                f"Expected one of {sorted(_VALID_COUNTRIES)}."
            )
        self._country = normalized

    @property
    def name(self) -> str:
        return "mabims"

    @property
    def country(self) -> str:
        """Upper-case country code this calendar was built for."""
        return self._country

    def month_length(self, year: int, month: int) -> int:
        if (
            isinstance(year, bool)
            or not isinstance(year, int)
            or isinstance(month, bool)
            or not isinstance(month, int)
        ):
            raise ValidationError(
                "MabimsCalendar month_length needs int year/month, "
                f"got {year!r}, {month!r}."
            )
        if year < 1:
            raise ValidationError(f"MabimsCalendar year must be >= 1, got {year}.")
        if not 1 <= month <= 12:
            raise ValidationError(
                f"MabimsCalendar month must be within [1, 12], got {month}."
            )
        if (year, month) < (_ANCHOR_YEAR, _ANCHOR_MONTH):
            raise ValidationError(_DEFERRED_MESSAGE)
        start = resolve_month_start(self._country, year, month)
        end = resolve_month_start(self._country, *_next_month(year, month))
        length = end - start
        if length not in (29, 30):
            raise AstronomicalError(
                f"MabimsCalendar({self._country}): month {year}-{month:02d} "
                f"resolved to {length} days "
                f"({date.fromordinal(start).isoformat()}.."
                f"{date.fromordinal(end - 1).isoformat()}); "
                "expected 29 or 30."
            )
        return length

    def from_gregorian(self, d: date) -> HijriDate:
        if isinstance(d, datetime):
            raise ValidationError(
                "MabimsCalendar needs a datetime.date (not a datetime); "
                f"pass d.date() or use gregorian_to_hijri, got {d!r}."
            )
        if not isinstance(d, date):
            raise ValidationError(f"MabimsCalendar needs a datetime.date, got {d!r}.")
        if d < _ANCHOR_GREGORIAN:
            raise ValidationError(_DEFERRED_MESSAGE)
        # Tabular seed: the true (observational) date sits within +/-4
        # days of it (spec section 4), hence within the seed month or its
        # immediate neighbours; probes at +/-2 months add wide margin.
        # Probes crossing the anchor raise ValidationError and are
        # skipped (mirror UQU); exhaustion means the seed assumption
        # broke: loud failure, never a silently extended window.
        seed = _TABULAR_SEED.from_gregorian(d)
        target = d.toordinal()
        probed: list[str] = []
        for offset in (0, -1, 1, -2, 2):
            year, month = seed.year, seed.month
            step = 1 if offset >= 0 else -1
            for _ in range(abs(offset)):
                year, month = (
                    _next_month(year, month)
                    if step > 0
                    else _previous_month(year, month)
                )
            if (year, month) < (_ANCHOR_YEAR, _ANCHOR_MONTH):
                continue  # Probe crossed the anchor; skip it.
            try:
                start = resolve_month_start(self._country, year, month)
                end = resolve_month_start(self._country, *_next_month(year, month))
            except ValidationError:
                continue  # Probe crossed the anchor; skip it.
            probed.append(
                f"{year}-{month:02d}=" f"{date.fromordinal(start).isoformat()}"
            )
            if start <= target < end:
                return HijriDate(year, month, target - start + 1)
        raise AstronomicalError(
            f"MabimsCalendar({self._country}): no Hijri month contains "
            f"{d.isoformat()} within the bounded probe "
            f"({', '.join(probed)}) seeded from tabular {seed.isoformat()}."
        )

    def to_gregorian(self, h: HijriDate) -> date:
        if not isinstance(h, HijriDate):
            raise ValidationError(f"MabimsCalendar needs a HijriDate, got {h!r}.")
        length = self.month_length(h.year, h.month)
        if h.day > length:
            raise ValidationError(
                f"MabimsCalendar({self._country}): day {h.day} exceeds "
                f"the length ({length} days) of month {h.month} "
                f"in year {h.year}."
            )
        return date.fromordinal(
            resolve_month_start(self._country, h.year, h.month) + h.day - 1
        )
