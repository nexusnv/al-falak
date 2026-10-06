"""Gregorian datetime -> Hijri date bridge with sunset rollover (phase 5)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from alfalak.calculation.CalculationMethod import CalculationMethod
from alfalak.calculation.CalculationParameters import CalculationParameters
from alfalak.calendar.HijriCalendar import HijriCalendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import ConfigurationError, ValidationError
from alfalak.PrayerTimes import PrayerTimes


def gregorian_to_hijri(
    dt: datetime,
    *,
    calendar: HijriCalendar,
    coordinates: Coordinates | None = None,
    params: CalculationParameters | None = None,
    change_at_sunset: bool = False,
    offsets: Any = None,
) -> HijriDate:
    """Convert a Gregorian datetime to a Hijri date on the given calendar.

    With ``change_at_sunset=False`` (default) the Hijri day follows the
    civil date: ``dt.date()`` is delegated to ``calendar.from_gregorian``.

    With ``change_at_sunset=True`` the Hijri day rolls over at that day's
    Maghrib: datetimes at or after Maghrib map to the *next* civil date's
    Hijri date. ``coordinates`` is then required (else
    ``ConfigurationError``); Maghrib comes from ``PrayerTimes`` in keyword
    form (``calculation_parameters=params`` — the third positional slot is
    the method, not the parameters). The civil date is normalized to UTC
    (``probe.astimezone(timezone.utc).date()``) and Maghrib is computed for
    that same UTC date via an explicit UTC-midnight datetime, so the same
    absolute instant maps to the same Hijri date regardless of ``dt``'s
    tz label. Instants before the previous UTC date's Maghrib (possible
    at far-west longitudes, where that Maghrib falls on the UTC civil
    date) step back one day. A polar ``AstronomicalError`` from Maghrib
    propagates unwrapped with no fallback.

    Timezone handling: prefer aware datetimes. Naive inputs are normalized
    via ``dt.replace(tzinfo=timezone.utc)``, i.e. treated as UTC; a naive
    datetime carrying *local* wall-clock time therefore misplaces Maghrib
    by the UTC offset. Aware datetimes are compared as absolute instants
    in the UTC frame, so any tz label for the same instant agrees. (With
    ``change_at_sunset=False`` there is no observer location, so the Hijri
    day still follows ``dt.date()`` in ``dt``'s own frame.)

    ``offsets`` is a Task 5 hook: any object with an
    ``apply(hijri, calendar)`` method (duck-typed ``OffsetStore``), applied
    last. ``None`` (default) skips it.
    """
    if not isinstance(dt, datetime):
        raise ValidationError(
            "gregorian_to_hijri needs a datetime, "
            f"got {dt!r} (pass a datetime, not a date)."
        )
    civil = dt.date()
    if change_at_sunset:
        if coordinates is None:
            raise ConfigurationError(
                "gregorian_to_hijri with change_at_sunset=True requires "
                "coordinates to locate sunset."
            )
        effective = (
            params
            if params is not None
            else CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
        )
        probe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        civil = probe.astimezone(timezone.utc).date()

        def _maghrib(d: date) -> datetime:
            return PrayerTimes(
                coordinates,
                datetime(d.year, d.month, d.day, tzinfo=timezone.utc),
                calculation_parameters=effective,
            ).maghrib

        if probe >= _maghrib(civil):
            civil = civil + timedelta(days=1)
        elif probe < _maghrib(civil - timedelta(days=1)):
            civil = civil - timedelta(days=1)
    hijri = calendar.from_gregorian(civil)
    if offsets is not None:
        apply = getattr(offsets, "apply", None)
        if not callable(apply):
            raise ConfigurationError(
                "offsets must expose an apply(hijri, calendar) method, "
                f"got {offsets!r}."
            )
        hijri = apply(hijri, calendar)
    return hijri
