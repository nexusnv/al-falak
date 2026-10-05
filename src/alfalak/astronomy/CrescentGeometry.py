"""Topocentric crescent geometry at local sunset (moon-sighting path).

Evaluates Sun/Moon equatorial positions at TT sunset on the given civil
date, converts to local horizontal coordinates, and derives the
standard crescent-visibility quantities: elongation (ARCL), geocentric
and topocentric arcs of vision, azimuth difference (DAZ), crescent
width, illumination, moonset lag, and moon age from a backward search
for the previous new moon (minimum ARCL).

References: Meeus 2nd ed. Ch.47 (lunar position), Ch.15 (transit/hour
angle interpolation); parallax/waxing-width relations from the standard
spherical-astronomy treatment used by Odeh/Yallop criteria.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from alfalak.astronomy.Astronomical import (
    approximate_transit,
    corrected_hour_angle,
)
from alfalak.astronomy.CalendricalHelper import julian_day
from alfalak.astronomy.DeltaT import delta_t
from alfalak.astronomy.LunarCoordinates import LunarCoordinates
from alfalak.astronomy.SolarCoordinates import SolarCoordinates
from alfalak.astronomy.SolarTime import SolarTime
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AstronomicalError, ValidationError
from alfalak.util.DateComponents import DateComponents
from alfalak.util.FloatUtil import unwind_angle

_EARTH_EQUATORIAL_RADIUS_KM: float = 6378.137
_SUNSET_ALTITUDE_DEG: float = -50.0 / 60.0
# Full synodic month (29.53d): the previous conjunction is always inside.
_MOON_AGE_SEARCH_DAYS: float = 30.0
_MOON_AGE_MIN_DAYS: float = 0.1
_MOON_AGE_STEP_DAYS: float = 1.0 / 24.0


@dataclass(frozen=True)
class CrescentGeometry:
    arcl_deg: float
    arcv_geo_deg: float
    arcv_topo_deg: float
    sun_alt_deg: float
    moon_alt_topo_deg: float
    daz_deg: float
    width_arcmin: float
    illumination: float
    lag_hours: float
    moon_age_days: float
    used_delta_t_s: float
    sunset_jd_utc: float


def _altaz(
    latitude_deg: float, lst_deg: float, ra_deg: float, dec_deg: float
) -> tuple[float, float]:
    """Local horizontal coordinates for equatorial (ra, dec) at LST."""
    hour_angle = math.radians(lst_deg - ra_deg)
    lat = math.radians(latitude_deg)
    dec = math.radians(dec_deg)
    sin_alt = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(
        hour_angle
    )
    altitude = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))
    azimuth = unwind_angle(
        math.degrees(
            math.atan2(
                math.sin(hour_angle),
                math.cos(hour_angle) * math.sin(lat) - math.tan(dec) * math.cos(lat),
            )
        )
        + 180.0
    )
    return altitude, azimuth


def _angular_separation_deg(
    ra1_deg: float, dec1_deg: float, ra2_deg: float, dec2_deg: float
) -> float:
    """Great-circle separation of two equatorial positions in degrees."""
    cos_sep = math.sin(math.radians(dec1_deg)) * math.sin(
        math.radians(dec2_deg)
    ) + math.cos(math.radians(dec1_deg)) * math.cos(math.radians(dec2_deg)) * math.cos(
        math.radians(ra2_deg - ra1_deg)
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_sep))))


def _arcl_at_jd(julian_day_tt: float) -> float:
    sun = SolarCoordinates(julian_day_tt)
    moon = LunarCoordinates(julian_day_tt)
    return _angular_separation_deg(
        sun.right_ascension,
        sun.declination,
        moon.right_ascension,
        moon.declination,
    )


def _moonset_lag_hours(
    year: int,
    month: int,
    day_of_month: int,
    coordinates: Coordinates,
    delta_t_s: float,
) -> float:
    """Hours from sunset to moonset.

    Negative when the Moon sets before the Sun (no evening visibility
    window); NaN when no moonset occurs on that civil date (e.g. a
    circumpolar Moon).

    Time-base note: the lunar transit/hour-angle interpolation is anchored
    at TT midnight (``julian_day(...) + delta_t_s / 86400``) because the
    lunar ephemeris takes TT, while ``sunset`` comes from ``SolarTime``
    anchored at UTC midnight (the prayer path treats UTC as TT, good to
    ~1 min). Both instants are fractions of the same civil date so the
    difference cancels most of the ~70 s offset; the residual ephemeris
    drift over that shift is ~0.01 deg, negligible for visibility scoring.
    Absolute altitudes carry the full LST shift (~0.3 deg), which is why
    ``CrescentGeometry`` stores them instead of assuming ``-0.833`` deg.
    """
    jd_midnight_utc = julian_day(year, month, day_of_month)
    jd_midnight_tt = jd_midnight_utc + delta_t_s / 86400.0
    solar_ref = SolarCoordinates(jd_midnight_tt)
    moon_prev = LunarCoordinates(jd_midnight_tt - 1.0)
    moon_day = LunarCoordinates(jd_midnight_tt)
    moon_next = LunarCoordinates(jd_midnight_tt + 1.0)
    approx = approximate_transit(
        coordinates.longitude,
        solar_ref.apparent_sidereal_time,
        moon_day.right_ascension,
    )
    moonset = corrected_hour_angle(
        approx,
        _SUNSET_ALTITUDE_DEG,
        coordinates,
        True,
        solar_ref.apparent_sidereal_time,
        moon_day.right_ascension,
        moon_prev.right_ascension,
        moon_next.right_ascension,
        moon_day.declination,
        moon_prev.declination,
        moon_next.declination,
    )
    sunset = SolarTime(DateComponents(year, month, day_of_month), coordinates).sunset
    if math.isnan(moonset) or math.isnan(sunset):
        return math.nan
    return moonset - sunset


def _moon_age_days(julian_day_tt: float) -> float:
    """Elapsed days since the previous new moon.

    Youngest local minimum of geocentric elongation (ARCL), sampled
    hourly from sunset back over the prior month. The youngest — not
    the deepest — minimum is used because a 30-day window usually
    spans two conjunctions and the global minimum may belong to the
    older one. Sampling starts at sunset itself so a conjunction hours
    before sunset is still caught; ages below the floor report the floor.

    When the sunset sample itself is the lowest (conjunction at or just
    before sunset), it can never win the interior-minimum search below,
    so a single forward sample disambiguates: waxing (ARCL growing after
    sunset) reports the floor, while a pre-conjunction evening (ARCL
    still shrinking toward a future conjunction) falls through to the
    older minimum.
    """
    offsets: list[float] = []
    offset = 0.0
    while offset <= _MOON_AGE_SEARCH_DAYS + 1e-12:
        offsets.append(offset)
        offset += _MOON_AGE_STEP_DAYS
    arcls = [_arcl_at_jd(julian_day_tt - offset) for offset in offsets]
    if (
        arcls[0] <= arcls[1]
        and _arcl_at_jd(julian_day_tt + _MOON_AGE_STEP_DAYS) >= arcls[0]
    ):
        return _MOON_AGE_MIN_DAYS
    for i in range(1, len(arcls) - 1):
        if arcls[i] <= arcls[i - 1] and arcls[i] <= arcls[i + 1]:
            return max(_MOON_AGE_MIN_DAYS, offsets[i])
    return _MOON_AGE_SEARCH_DAYS


def crescent_geometry_at_sunset(
    day: date, coordinates: Coordinates, delta_t_override: float | None = None
) -> CrescentGeometry:
    """Compute topocentric crescent geometry at sunset for a civil date.

    A ``datetime`` is accepted and its calendar date is used (the time
    component is ignored).
    """
    if not isinstance(day, date):
        raise ValidationError(f"day must be a datetime.date, got {day!r}.")
    if not isinstance(coordinates, Coordinates):
        raise ValidationError(
            "coordinates must be a Coordinates instance, " f"got {coordinates!r}."
        )
    year = day.year
    month = day.month
    day_of_month = day.day
    st = SolarTime(DateComponents(year, month, day_of_month), coordinates)
    if math.isnan(st.sunset):
        raise AstronomicalError(
            "Crescent geometry is undefined: the Sun does not set "
            f"(no sunset) on {day.isoformat()} at this location."
        )
    jd_sunset_utc = julian_day(year, month, day_of_month) + st.sunset / 24.0
    # Day-of-year is 1-based: subtract 1 so Dec 31 of a leap year stays
    # inside this calendar year instead of spilling ~1 day into the next.
    decimal_year = year + (day.timetuple().tm_yday - 1) / 365.25
    dt = delta_t(decimal_year, override=delta_t_override)
    jd_tt = jd_sunset_utc + dt / 86400.0

    sun = SolarCoordinates(jd_tt)
    moon = LunarCoordinates(jd_tt)
    lst = unwind_angle(sun.apparent_sidereal_time + coordinates.longitude)

    sun_alt, sun_az = _altaz(
        coordinates.latitude, lst, sun.right_ascension, sun.declination
    )
    moon_alt_geo, moon_az = _altaz(
        coordinates.latitude, lst, moon.right_ascension, moon.declination
    )

    parallax_deg = math.degrees(
        math.asin(_EARTH_EQUATORIAL_RADIUS_KM / max(moon.distance_km, 1.0))
    )
    moon_alt_topo = moon_alt_geo - parallax_deg * math.cos(math.radians(moon_alt_geo))

    arcl = _angular_separation_deg(
        sun.right_ascension,
        sun.declination,
        moon.right_ascension,
        moon.declination,
    )
    arcv_topo = moon_alt_topo - sun_alt
    arcv_geo = moon_alt_geo - sun_alt
    az_diff = abs(moon_az - sun_az)
    daz = min(az_diff, 360.0 - az_diff)

    semi_diameter_arcmin = 0.27245 * parallax_deg * 60.0
    width = semi_diameter_arcmin * (1.0 - math.cos(math.radians(arcl)))
    illumination = (1.0 - math.cos(math.radians(arcl))) / 2.0

    lag_hours = _moonset_lag_hours(year, month, day_of_month, coordinates, dt)
    moon_age = _moon_age_days(jd_tt)

    return CrescentGeometry(
        arcl_deg=arcl,
        arcv_geo_deg=arcv_geo,
        arcv_topo_deg=arcv_topo,
        sun_alt_deg=sun_alt,
        moon_alt_topo_deg=moon_alt_topo,
        daz_deg=daz,
        width_arcmin=width,
        illumination=illumination,
        lag_hours=lag_hours,
        moon_age_days=moon_age,
        used_delta_t_s=dt,
        sunset_jd_utc=jd_sunset_utc,
    )
