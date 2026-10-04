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
from alfalak.exceptions import AstronomicalError
from alfalak.util.DateComponents import DateComponents
from alfalak.util.FloatUtil import unwind_angle

_EARTH_EQUATORIAL_RADIUS_KM: float = 6378.137
_SUNSET_ALTITUDE_DEG: float = -50.0 / 60.0
_MOON_AGE_SEARCH_DAYS: float = 2.0
_MOON_AGE_MIN_DAYS: float = 0.1
_MOON_AGE_STEP_DAYS: float = 1.0 / 24.0


@dataclass(frozen=True)
class CrescentGeometry:
    arcl_deg: float
    arcv_geo_deg: float
    arcv_topo_deg: float
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
    """Hours from sunset to moonset; 0.0 when the Moon never sets."""
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
        return 0.0
    return max(0.0, moonset - sunset)


def _moon_age_days(julian_day_tt: float) -> float:
    """Elapsed days since the previous new moon (minimum ARCL search)."""
    best_jd = julian_day_tt - _MOON_AGE_SEARCH_DAYS
    best_arcl = math.inf
    offset = _MOON_AGE_SEARCH_DAYS
    while offset >= _MOON_AGE_MIN_DAYS - 1e-12:
        arcl = _arcl_at_jd(julian_day_tt - offset)
        if arcl < best_arcl:
            best_arcl = arcl
            best_jd = julian_day_tt - offset
        offset -= _MOON_AGE_STEP_DAYS
    age = julian_day_tt - best_jd
    return max(_MOON_AGE_MIN_DAYS, min(_MOON_AGE_SEARCH_DAYS, age))


def crescent_geometry_at_sunset(
    day: date, coordinates: Coordinates, delta_t_override: float | None = None
) -> CrescentGeometry:
    """Compute topocentric crescent geometry at sunset for a civil date."""
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
    decimal_year = year + day.timetuple().tm_yday / 365.25
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
        daz_deg=daz,
        width_arcmin=width,
        illumination=illumination,
        lag_hours=lag_hours,
        moon_age_days=moon_age,
        used_delta_t_s=dt,
        sunset_jd_utc=jd_sunset_utc,
    )
