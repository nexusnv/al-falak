import pytest
from datetime import date, datetime, timezone
from alfalak import PrayerTimes
from alfalak.calculation import (
    CalculationMethod,
    CalculationParameters,
    PolarCircleRule,
)
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AstronomicalError, ConfigurationError
from alfalak.Qibla import MAKKAH
from alfalak.util.DateComponents import DateComponents
from support import is_ordered as _ordered

TROMSO = (69.65, 18.96)
SUMMER = DateComponents(2015, 6, 21)
WINTER = DateComponents(2015, 12, 21)


def _params(**kwargs):
    return CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE, **kwargs)


@pytest.mark.parametrize("date", [SUMMER, WINTER])
def test_default_assumes_nearest_latitude(date):
    prayer_times = PrayerTimes(TROMSO, date, calculation_parameters=_params())

    assert _ordered(prayer_times)
    # clamped toward the equator, near the solstice boundary (~66.5)
    assert 60 < prayer_times.coordinates.latitude < TROMSO[0]
    assert prayer_times.coordinates.longitude == TROMSO[1]


def test_nearest_day_keeps_location_but_shifts_date():
    prayer_times = PrayerTimes(
        TROMSO,
        WINTER,
        calculation_parameters=_params(polar_circle_rule=PolarCircleRule.NEAREST_DAY),
    )

    assert _ordered(prayer_times)
    assert prayer_times.coordinates.latitude == TROMSO[0]
    assert prayer_times.fajr.date() != date(2015, 12, 21)
    assert prayer_times.prayer_date.date() == prayer_times.fajr.date()
    assert prayer_times.prayer_date != datetime(2015, 12, 21, tzinfo=timezone.utc)


def test_makkah_rule_matches_makkah_schedule():
    polar = PrayerTimes(
        TROMSO,
        WINTER,
        calculation_parameters=_params(polar_circle_rule=PolarCircleRule.MAKKAH),
    )
    makkah = PrayerTimes(
        (MAKKAH.latitude, MAKKAH.longitude),
        WINTER,
        calculation_parameters=_params(polar_circle_rule=PolarCircleRule.MAKKAH),
    )

    assert polar.coordinates.latitude == MAKKAH.latitude
    for name in ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"):
        assert getattr(polar, name) == getattr(makkah, name)


def test_no_rule_change_on_normal_days():
    normal_default = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=_params(),
    )
    normal_none = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=_params(polar_circle_rule=PolarCircleRule.NONE),
    )

    for name in ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"):
        assert getattr(normal_default, name) == getattr(normal_none, name)


def test_unknown_polar_rule_raises():
    params = _params()
    params.polar_circle_rule = "bogus"

    with pytest.raises(ConfigurationError, match="(?i)polar"):
        PrayerTimes(TROMSO, WINTER, calculation_parameters=params)


def test_invalid_polar_rule_type_raises_at_construction():
    with pytest.raises(ConfigurationError, match="(?i)polar"):
        CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
            polar_circle_rule="bogus",
        )


def test_coordinates_object_accepted_for_polar():
    prayer_times = PrayerTimes(
        Coordinates(*TROMSO), SUMMER, calculation_parameters=_params()
    )

    assert _ordered(prayer_times)


def test_asr_saturates_to_dhuhr_at_polar_boundary():
    # 66.4N on 2015-12-21 computes Asr before Dhuhr without the clamp
    prayer_times = PrayerTimes(
        (66.4, 18.96),
        DateComponents(2015, 12, 21),
        calculation_parameters=_params(polar_circle_rule=PolarCircleRule.NONE),
    )

    assert prayer_times.asr == prayer_times.dhuhr


def test_extreme_adjustments_saturate_asr_to_dhuhr():
    params = _params()
    params.adjustments.dhuhr = 180
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 12, 1),
        calculation_parameters=params,
    )

    assert prayer_times.asr == prayer_times.dhuhr
    assert _ordered(prayer_times)


def test_asr_saturates_to_maghrib_near_polar_boundary():
    # 89.1N on 2024-03-19: shadow-length hour angle spills past sunset
    # without the maghrib-side clamp (Asr 22:12 > Maghrib 21:22).
    prayer_times = PrayerTimes(
        (89.1, 0.0),
        DateComponents(2024, 3, 19),
        calculation_parameters=_params(polar_circle_rule=PolarCircleRule.NONE),
    )

    assert prayer_times.asr == prayer_times.maghrib


@pytest.mark.parametrize("lat", [90.0, -90.0])
def test_nearest_day_at_exact_pole_raises_actionable_error(lat):
    params = _params(polar_circle_rule=PolarCircleRule.NEAREST_DAY)
    with pytest.raises(AstronomicalError, match="(?i)exact.*pole|NEAREST_LATITUDE"):
        PrayerTimes(
            (lat, 0.0),
            DateComponents(2024, 6, 21),
            calculation_parameters=params,
        )
