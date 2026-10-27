import functools
import math
from alfalak.astronomy.Astronomical import (
    approximate_transit,
    corrected_hour_angle,
    corrected_transit,
)
from alfalak.astronomy.CalendricalHelper import julian_day
from alfalak.data.Coordinates import Coordinates
from alfalak.data.ShadowLength import ShadowLength
from alfalak.astronomy.SolarCoordinates import SolarCoordinates
from alfalak.exceptions import ValidationError
from alfalak.util.DateComponents import DateComponents


@functools.lru_cache(maxsize=512)
def _solar_coords_for_date(
    year: int, month: int, day: int, day_offset: int = 0
) -> SolarCoordinates:
    """Return solar coordinates for a calendar date shifted by ``day_offset``.

    The key is the calendar date plus a small integer offset, never a Julian
    day float: adjacent calendar days differ by exactly 1.0 day, so the
    neighbour is computed in Julian-day space. That keeps ``DateComponents``
    at the edges of the proleptic calendar total (no ``date ± timedelta``
    ``OverflowError``) while preserving byte-identical output.

    ``SolarTime`` asks for offsets -1, 0 and +1. ``PrayerTimes`` builds
    today's and tomorrow's ``SolarTime``, so one build requests six keys over
    four unique Julian days (``D-1`` through ``D+2``). Two key pairs alias the
    same Julian day without sharing a cache entry: ``(D, 0)`` with
    ``(D+1, -1)``, and ``(D, +1)`` with ``(D+1, 0)``. Repeated builds of the
    same date hit the cache; adjacent dates in a multi-day sweep use disjoint
    keys and do not share entries. Elevation is applied downstream in
    ``SolarTime`` and is not part of the key.
    """
    return SolarCoordinates(julian_day(year, month, day) + day_offset)


def _clear_solar_coords_cache() -> None:
    """Drop the date-keyed solar-coordinate cache (test hook)."""
    _solar_coords_for_date.cache_clear()


class SolarTime:
    def __init__(
        self,
        date_components: DateComponents,
        coordinates: Coordinates,
        elevation_m: float = 0.0,
    ):
        if (
            isinstance(elevation_m, bool)
            or not isinstance(elevation_m, (int, float))
            or not math.isfinite(elevation_m)
            or elevation_m < 0
        ):
            raise ValidationError(
                "Elevation must be a finite non-negative number of metres, "
                f"got {elevation_m!r}."
            )

        self.prev_solar = _solar_coords_for_date(
            date_components.year, date_components.month, date_components.day, -1
        )
        self.solar = _solar_coords_for_date(
            date_components.year, date_components.month, date_components.day
        )
        self.next_solar = _solar_coords_for_date(
            date_components.year, date_components.month, date_components.day, 1
        )

        self.approximate_transit = approximate_transit(
            coordinates.longitude,
            self.solar.apparent_sidereal_time,
            self.solar.right_ascension,
        )
        # Dip of the horizon for eye height h (Nautical Almanac/Bowditch:
        # dip = 0.0293°·√h_m, h in metres). Default 0 preserves sea-level
        # behavior (h0 = −0.833° = 34′ refraction + 16′ semi-diameter).
        solar_altitude = -50.0 / 60.0 - 0.0293 * math.sqrt(elevation_m)

        self.observer = coordinates
        self.transit = corrected_transit(
            self.approximate_transit,
            coordinates.longitude,
            self.solar.apparent_sidereal_time,
            self.solar.right_ascension,
            self.prev_solar.right_ascension,
            self.next_solar.right_ascension,
        )
        self.sunrise = corrected_hour_angle(
            self.approximate_transit,
            solar_altitude,
            coordinates,
            False,
            self.solar.apparent_sidereal_time,
            self.solar.right_ascension,
            self.prev_solar.right_ascension,
            self.next_solar.right_ascension,
            self.solar.declination,
            self.prev_solar.declination,
            self.next_solar.declination,
        )
        self.sunset = corrected_hour_angle(
            self.approximate_transit,
            solar_altitude,
            coordinates,
            True,
            self.solar.apparent_sidereal_time,
            self.solar.right_ascension,
            self.prev_solar.right_ascension,
            self.next_solar.right_ascension,
            self.solar.declination,
            self.prev_solar.declination,
            self.next_solar.declination,
        )

    def hour_angle(self, angle: float, after_transit: bool) -> float:
        return corrected_hour_angle(
            self.approximate_transit,
            angle,
            self.observer,
            after_transit,
            self.solar.apparent_sidereal_time,
            self.solar.right_ascension,
            self.prev_solar.right_ascension,
            self.next_solar.right_ascension,
            self.solar.declination,
            self.prev_solar.declination,
            self.next_solar.declination,
        )

    def afternoon(self, shadow_length: ShadowLength) -> float:
        # TODO (from Swift version) source shadow angle calculation
        tangent = abs(self.observer.latitude - self.solar.declination)
        inverse = shadow_length.shadow_length + math.tan(math.radians(tangent))
        angle = math.degrees(math.atan(1.0 / inverse))

        return self.hour_angle(angle, True)
