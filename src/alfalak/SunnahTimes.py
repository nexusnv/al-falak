from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import numbers

from alfalak.PrayerTimes import PrayerTimes
from alfalak.exceptions import ValidationError
from alfalak.util.CalendarUtil import rounded_minute


class SunnahTimes:
    """
    Sunnah night markers derived from prayer times.
    Ported from upstream adhan (adhan-kotlin SunnahTimes).

    The night is defined as Maghrib to next-day Fajr (inclusive of any
    per-prayer minute offsets: Maghrib = sunset + offsets, Fajr capped by
    the high-latitude rule). Duration arithmetic runs in UTC with
    minute rounding applied before converting back to the display zone.
    """

    #: The midpoint between Maghrib and (next-day) Fajr.
    middle_of_the_night: datetime

    #: One third into the period between Maghrib and (next-day) Fajr.
    first_third_of_the_night: datetime

    #: The beginning of the last third of the period between Maghrib
    #: and (next-day) Fajr, a recommended time to perform Qiyam.
    last_third_of_the_night: datetime

    #: Tahajjud/Qiyam window: (last_third_of_the_night, next-day Fajr).
    tahajjud_window: tuple[datetime, datetime]

    def __init__(self, prayer_times: PrayerTimes) -> None:
        tomorrow = PrayerTimes(
            prayer_times.coordinates,
            prayer_times._prayer_date + timedelta(days=1),
            calculation_parameters=prayer_times.calculation_parameters,
            time_zone=prayer_times.time_zone,
        )

        # Duration arithmetic runs in UTC: wall-clock subtraction on two
        # datetimes sharing one DST-observing ZoneInfo ignores the offset
        # change, shifting markers by an hour on transition nights.
        zone = prayer_times.maghrib.tzinfo or timezone.utc
        self._zone = zone
        self._maghrib_utc: datetime = prayer_times.maghrib.astimezone(timezone.utc)
        self._fajr_next_utc: datetime = tomorrow.fajr.astimezone(timezone.utc)
        self._tomorrow_fajr: datetime = tomorrow.fajr

        self.middle_of_the_night = self.night_fraction(1 / 2)
        self.first_third_of_the_night = self.night_fraction(1 / 3)
        self.last_third_of_the_night = self.night_fraction(2 / 3)
        self.tahajjud_window = (
            self.last_third_of_the_night,
            self._tomorrow_fajr,
        )

    def night_fraction(
        self,
        fraction: float | Decimal | Fraction,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> datetime:
        """Return Maghrib + ``fraction`` of the night.

        The default night is Maghrib to next-day Fajr. Pass explicit
        aware datetimes as ``start``/``end`` for alternative anchors
        (e.g. ``start=prayer_times.isha`` for the Isha-anchored school,
        or an unadjusted astronomical sunset for the sunset-anchored
        variant); omitted ends fall back to the default anchors.
        Output is minute-rounded in UTC, then converted to the
        display zone.

        ``fraction`` accepts ``int``/``float``/``Fraction``/``Decimal``
        in the open interval (0, 1) — ``int`` via the numeric tower,
        any other ``numbers.Real`` at runtime; ``bool`` is rejected.
        Validation and the offset use the exact input value (no binary
        float rounding), and the offset keeps sub-minute precision so
        minute rounding sees the true seconds. A degenerate interval
        (``end`` at or before ``start``, including a Maghrib at or
        after next-day Fajr) raises ``ValidationError``.
        """
        return rounded_minute(
            self._night_fraction_utc(fraction, start, end)
        ).astimezone(self._zone)

    def _night_fraction_utc(
        self,
        fraction: float | Decimal | Fraction,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> datetime:
        if isinstance(fraction, bool) or not isinstance(
            fraction, (numbers.Real, Decimal)
        ):
            raise ValidationError(
                f"Night fraction must be a real number in (0, 1), got {fraction!r}."
            )
        try:
            in_range = 0 < fraction < 1
        except InvalidOperation:
            raise ValidationError(
                f"Night fraction must be in (0, 1) exclusive, got {fraction!r}."
            ) from None
        if not in_range:
            raise ValidationError(
                f"Night fraction must be in (0, 1) exclusive, got {fraction!r}."
            )

        start_utc = (
            self._maghrib_utc if start is None else self._coerce_utc(start, "start")
        )
        end_utc = self._fajr_next_utc if end is None else self._coerce_utc(end, "end")
        delta = end_utc - start_utc
        if delta <= timedelta(0):
            raise ValidationError(
                "Night interval must have end after start, "
                f"got start={start_utc.isoformat()}, end={end_utc.isoformat()}."
            )
        # Exact duration from timedelta components (total_seconds() is a
        # binary float); exact fraction value (no float() underflow for
        # tiny Decimal/Fraction inputs). float() only at the end, where
        # timedelta needs it — microsecond resolution is far finer than
        # the minute rounding that follows.
        duration = Fraction(
            (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds,
            1_000_000,
        )
        try:
            frac_exact = Fraction(fraction)
        except TypeError:
            # Exotic numbers.Real outside (int/float/Fraction/Decimal):
            # input already validated above, fall back to its float value.
            frac_exact = Fraction(float(fraction))
        offset_seconds = float(duration * frac_exact)
        return start_utc + timedelta(seconds=offset_seconds)

    def night_fraction_unrounded(
        self,
        fraction: float | Decimal | Fraction,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> datetime:
        """Return Maghrib + ``fraction`` of the night, UTC, never rounded.

        Same computation and validation as ``night_fraction`` minus the minute
        rounding and the display-zone conversion.
        """
        return self._night_fraction_utc(fraction, start, end)

    @staticmethod
    def _coerce_utc(value: datetime, name: str) -> datetime:
        if not isinstance(value, datetime):
            raise ValidationError(
                f"Night anchor {name} must be a datetime, got {value!r}."
            )
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(
                f"Night anchor {name} must be timezone-aware, got {value!r}."
            )
        return value.astimezone(timezone.utc)
