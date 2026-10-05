"""Gregorian datetime -> Hijri date bridge with sunset rollover (phase 5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from alfalak.calculation.CalculationMethod import CalculationMethod
from alfalak.calculation.CalculationParameters import CalculationParameters
from alfalak.calendar.HijriCalendar import HijriCalendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import ConfigurationError
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
    the method, not the parameters). Only the date part of ``dt`` feeds the
    prayer computation. A polar ``AstronomicalError`` from Maghrib
    propagates unwrapped with no fallback.

    Timezone handling: prefer aware datetimes. Naive inputs are normalized
    via ``dt.replace(tzinfo=timezone.utc)``, i.e. treated as UTC; a naive
    datetime carrying *local* wall-clock time therefore misplaces Maghrib
    by the UTC offset. Aware datetimes compare in their own frame
    (absolute instants), so any zone is fine.

    ``offsets`` is a Task 5 hook: any object with an
    ``apply(hijri, calendar)`` method (duck-typed ``OffsetStore``), applied
    last. ``None`` (default) skips it.
    """
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
        maghrib = PrayerTimes(coordinates, dt, calculation_parameters=effective).maghrib
        probe = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        if probe >= maghrib:
            civil = civil + timedelta(days=1)
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
