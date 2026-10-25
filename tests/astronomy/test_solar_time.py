from datetime import datetime, timezone, timedelta
import math
import pytest
from alfalak.astronomy.CalendricalHelper import julian_day
from alfalak.astronomy.SolarCoordinates import SolarCoordinates
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import ValidationError
from alfalak.util.DateComponents import DateComponents
from alfalak.util.TimeComponents import TimeComponents
from alfalak.astronomy.SolarTime import (
    SolarTime,
    _solar_coords_for_date,
    _clear_solar_coords_cache,
)


def test_solar_time():
    """
    Comparison values generated from
    http://aa.usno.navy.mil/rstt/onedaytable?form=1&ID=AA&year=2015&month=7&day=12&state=NC&place=raleigh
    """

    coordinates = Coordinates(35 + 47.0 / 60.0, -78 - 39.0 / 60.0)
    solar = SolarTime(DateComponents(2015, 7, 12), coordinates)

    transit = solar.transit
    sunrise = solar.sunrise
    sunset = solar.sunset
    twilight_start = solar.hour_angle(-6, False)
    twilight_end = solar.hour_angle(-6, True)
    invalid = solar.hour_angle(-36, True)

    assert _time_string(twilight_start) == "9:38"
    assert _time_string(sunrise) == "10:08"
    assert _time_string(transit) == "17:20"
    assert _time_string(sunset) == "24:32"
    assert _time_string(twilight_end) == "25:02"
    assert _time_string(invalid) == ""


def test_right_ascension_edge_case():
    coordinates = Coordinates(35 + 47.0 / 60.0, -78 - 39.0 / 60.0)

    previous_time = None
    for i in range(365):
        time = SolarTime(_make_date_with_offset(2016, 1, 1, i), coordinates)

        if i > 0:
            # transit from one day to another should not differ more than one minute
            assert abs(time.transit - previous_time.transit) < (1.0 / 60.0)

            # sunrise and sunset from one day to another should not differ more than two minutes
            assert abs(time.sunrise - previous_time.sunrise) < (2.0 / 60.0)
            assert abs(time.sunset - previous_time.sunset) < (2.0 / 60.0)

        previous_time = time


def test_calendrical_date():
    # generated from http://aa.usno.navy.mil/data/docs/RS_OneYear.php for KUKUIHAELE, HAWAII
    coordinates = Coordinates(20 + 7.0 / 60.0, -155.0 - 34.0 / 60.0)
    day1solar = SolarTime(DateComponents(2015, 4, 2), coordinates)
    day2solar = SolarTime(DateComponents(2015, 4, 3), coordinates)

    day1 = day1solar.sunrise
    day2 = day2solar.sunrise

    assert _time_string(day1) == "16:15"
    assert _time_string(day2) == "16:14"


def _make_date_with_offset(year: int, month: int, day: int, offset: int):
    date_time = datetime(year, month, day, tzinfo=timezone.utc)

    date_time_offset = date_time + timedelta(days=offset)
    return DateComponents.from_utc(date_time_offset)


@pytest.mark.parametrize(
    "elevation_m",
    [-1.0, -0.5, float("nan"), float("inf"), True, "100", None],
)
def test_invalid_elevation_rejected_by_solar_time(elevation_m):
    # Direct SolarTime construction must honor the same contract as
    # CalculationParameters: ValidationError, never a bare ValueError from
    # math.sqrt or NaN altitude propagating downstream.
    with pytest.raises(ValidationError, match="(?i)elevation"):
        SolarTime(
            DateComponents(2015, 7, 12),
            Coordinates(35.7750, -78.6336),
            elevation_m,
        )


def test_zero_elevation_accepted_by_solar_time():
    solar = SolarTime(DateComponents(2015, 7, 12), Coordinates(35.7750, -78.6336), 0.0)
    assert solar.sunrise == pytest.approx(10.133, abs=0.01)


@pytest.mark.parametrize(
    "date",
    [(1, 1, 1), (2024, 2, 29), (2024, 3, 1), (2024, 12, 31), (9999, 12, 31)],
    ids=["year-1", "leap-day", "month-start", "year-end", "year-9999"],
)
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_cached_solar_coords_match_direct_construction(date, offset):
    """The date cache must be a pure memo of ``SolarCoordinates(jd)``.

    Neighbours are computed in Julian-day space, so the proleptic calendar
    edges (year 1 and year 9999) stay total: no ``date ± timedelta``
    ``OverflowError`` is introduced by the cache.
    """
    _clear_solar_coords_cache()
    year, month, day = date
    cached = _solar_coords_for_date(year, month, day, offset)
    direct = SolarCoordinates(julian_day(year, month, day) + offset)

    assert cached.declination == direct.declination
    assert cached.right_ascension == direct.right_ascension
    assert cached.apparent_sidereal_time == direct.apparent_sidereal_time


def test_solar_time_accepts_proleptic_calendar_start():
    # Year 1 previously worked through direct SolarCoordinates construction;
    # the cache must not replace it with an overflow-prone date arithmetic.
    solar = SolarTime(DateComponents(1, 1, 1), Coordinates(0.0, 0.0))
    assert math.isfinite(solar.transit)
    assert math.isfinite(solar.sunrise)


def test_solar_coords_cache_reuses_and_clears():
    _clear_solar_coords_cache()
    try:
        first = _solar_coords_for_date(2024, 3, 20)
        second = _solar_coords_for_date(2024, 3, 20)
        info = _solar_coords_for_date.cache_info()
        assert first is second
        assert info.hits >= 1
        assert info.currsize == 1
    finally:
        _clear_solar_coords_cache()
    assert _solar_coords_for_date.cache_info().currsize == 0


def _time_string(when: float):
    components = TimeComponents.from_float(when)
    if components is None:
        return ""

    minutes = int((components.minutes + round(components.seconds / 60.0)))

    return f"{components.hours}:{minutes:0>2d}"
