import math
import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from alfalak.data.Coordinates import Coordinates
from alfalak.data.Prayer import Prayer
from alfalak.util.DateComponents import DateComponents
from alfalak.calculation.CalculationMethod import CalculationMethod
from alfalak.calculation.CalculationParameters import CalculationParameters
from alfalak.astronomy.SolarTime import SolarTime
from alfalak.util.TimeComponents import TimeComponents
from alfalak.calculation.Madhab import Madhab
from alfalak.calculation.PolarCircleRule import PolarCircleRule
from alfalak.PrayerTimes import PrayerTimes
from alfalak.calculation.PrayerAdjustments import PrayerAdjustments
from alfalak.exceptions import (
    AstronomicalError,
    ConfigurationError,
    ValidationError,
)
from zoneinfo import ZoneInfo


def test_prayer_times_raleigh_golden():
    # Arrange
    date = DateComponents(2015, 7, 12)
    params = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    params.madhab = Madhab.HANAFI
    coordinates = (35.7750, -78.6336)
    format = "%I:%M %p"
    tz = ZoneInfo("America/New_York")

    # Act
    prayer_times = PrayerTimes(coordinates, date, calculation_parameters=params)

    # Assert
    assert prayer_times.fajr.astimezone(tz).strftime(format) == "04:42 AM"
    assert prayer_times.sunrise.astimezone(tz).strftime(format) == "06:08 AM"
    assert prayer_times.dhuhr.astimezone(tz).strftime(format) == "01:21 PM"
    assert prayer_times.asr.astimezone(tz).strftime(format) == "06:22 PM"
    assert prayer_times.maghrib.astimezone(tz).strftime(format) == "08:32 PM"
    assert prayer_times.isha.astimezone(tz).strftime(format) == "09:57 PM"


def test_either_calculation_method_or_calculation_parameters_is_passed():
    date = DateComponents(2015, 7, 12)
    method = CalculationMethod.NORTH_AMERICA
    params = CalculationParameters(method=method)
    coordinates = (35.7750, -78.6336)

    with pytest.raises(
        ConfigurationError,
        match="Only one of calculation_method or calculation_parameters must be passed.",
    ):
        PrayerTimes(coordinates, date, method, params)


def test_when_transit_or_sunrise_components_or_sunset_components_or_tomorrow_sunrise_components_is_none_it_should_raise_exception():
    date = DateComponents(2015, 7, 12)
    method = CalculationMethod.NORTH_AMERICA
    coordinates = (35.7750, -78.6336)

    with patch.object(TimeComponents, "from_float", lambda e: None):
        with pytest.raises(AstronomicalError, match="(?i)polar day/night"):
            PrayerTimes(coordinates, date, method)


def test_when_asr_is_not_set_raise_exception():
    date = DateComponents(2015, 7, 12)
    method = CalculationMethod.NORTH_AMERICA
    coordinates = (35.7750, -78.6336)

    with patch.object(SolarTime, "afternoon", lambda e, f: math.inf):
        with pytest.raises(AstronomicalError, match="Unable to compute Asr"):
            PrayerTimes(coordinates, date, method)


def test_prayer_times_with_method_with_isha_interval():
    date = DateComponents(2022, 8, 8)
    parameters = CalculationParameters(method=CalculationMethod.UMM_AL_QURA)
    coordinates = (21.422510, 39.826168)

    prayer_times = PrayerTimes(coordinates, date, calculation_parameters=parameters)

    interval_maghrib_isha = prayer_times.isha - prayer_times.maghrib

    assert interval_maghrib_isha.total_seconds() / 60 == parameters.isha_interval


def test_offsets():
    # Arrange
    date = DateComponents(2015, 12, 1)
    coordinates = (35.7750, -78.6336)
    format = "%I:%M %p"
    tz = ZoneInfo("America/New_York")
    calculation_method = CalculationMethod.MUSLIM_WORLD_LEAGUE

    parameters_with_no_offsets = CalculationParameters(method=calculation_method)

    parameters_with_offsets = CalculationParameters(method=calculation_method)
    parameters_with_offsets.adjustments.fajr = 10
    parameters_with_offsets.adjustments.sunrise = 10
    parameters_with_offsets.adjustments.dhuhr = 10
    parameters_with_offsets.adjustments.asr = 10
    parameters_with_offsets.adjustments.maghrib = 10
    parameters_with_offsets.adjustments.isha = 10

    parameters_with_blank_adjustments = CalculationParameters(method=calculation_method)
    parameters_with_blank_adjustments.adjustments = PrayerAdjustments()

    # Act
    prayer_times_with_no_offsets = PrayerTimes(
        coordinates, date, calculation_parameters=parameters_with_no_offsets
    )
    prayer_times_with_offsets = PrayerTimes(
        coordinates, date, calculation_parameters=parameters_with_offsets
    )
    prayer_times_with_blank_adjustments = PrayerTimes(
        coordinates, date, calculation_parameters=parameters_with_blank_adjustments
    )

    # Assert
    assert (
        prayer_times_with_no_offsets.fajr.astimezone(tz).strftime(format) == "05:35 AM"
    )
    assert prayer_times_with_offsets.fajr.astimezone(tz).strftime(format) == "05:45 AM"
    assert (
        prayer_times_with_blank_adjustments.fajr.astimezone(tz).strftime(format)
        == "05:35 AM"
    )

    assert (
        prayer_times_with_no_offsets.sunrise.astimezone(tz).strftime(format)
        == "07:06 AM"
    )
    assert (
        prayer_times_with_offsets.sunrise.astimezone(tz).strftime(format) == "07:16 AM"
    )
    assert (
        prayer_times_with_blank_adjustments.sunrise.astimezone(tz).strftime(format)
        == "07:06 AM"
    )

    assert (
        prayer_times_with_no_offsets.dhuhr.astimezone(tz).strftime(format) == "12:05 PM"
    )
    assert prayer_times_with_offsets.dhuhr.astimezone(tz).strftime(format) == "12:15 PM"
    assert (
        prayer_times_with_blank_adjustments.dhuhr.astimezone(tz).strftime(format)
        == "12:05 PM"
    )

    assert (
        prayer_times_with_no_offsets.asr.astimezone(tz).strftime(format) == "02:42 PM"
    )
    assert prayer_times_with_offsets.asr.astimezone(tz).strftime(format) == "02:52 PM"
    assert (
        prayer_times_with_blank_adjustments.asr.astimezone(tz).strftime(format)
        == "02:42 PM"
    )

    assert (
        prayer_times_with_no_offsets.maghrib.astimezone(tz).strftime(format)
        == "05:01 PM"
    )
    assert (
        prayer_times_with_offsets.maghrib.astimezone(tz).strftime(format) == "05:11 PM"
    )
    assert (
        prayer_times_with_blank_adjustments.maghrib.astimezone(tz).strftime(format)
        == "05:01 PM"
    )

    assert (
        prayer_times_with_no_offsets.isha.astimezone(tz).strftime(format) == "06:26 PM"
    )
    assert prayer_times_with_offsets.isha.astimezone(tz).strftime(format) == "06:36 PM"
    assert (
        prayer_times_with_blank_adjustments.isha.astimezone(tz).strftime(format)
        == "06:26 PM"
    )


def test_moon_sighting_method():
    # Arrange
    date = DateComponents(2016, 1, 31)
    coordinates = (35.7750, -78.6336)
    calculation_method = CalculationMethod.MOON_SIGHTING_COMMITTEE
    format = "%I:%M %p"
    tz = ZoneInfo("America/New_York")

    # Act
    prayer_times = PrayerTimes(coordinates, date, calculation_method)

    # Assert
    assert prayer_times.fajr.astimezone(tz).strftime(format) == "05:48 AM"
    assert prayer_times.sunrise.astimezone(tz).strftime(format) == "07:16 AM"
    assert prayer_times.dhuhr.astimezone(tz).strftime(format) == "12:33 PM"
    assert prayer_times.asr.astimezone(tz).strftime(format) == "03:20 PM"
    assert prayer_times.maghrib.astimezone(tz).strftime(format) == "05:43 PM"
    assert prayer_times.isha.astimezone(tz).strftime(format) == "07:05 PM"


def test_moon_sighting_method_high_lat():
    # Values from http://www.moonsighting.com/pray.php
    # Arrange
    date = DateComponents(2016, 1, 1)
    parameters = CalculationParameters(method=CalculationMethod.MOON_SIGHTING_COMMITTEE)
    parameters.madhab = Madhab.HANAFI
    coordinates = (59.9094, 10.7349)
    format = "%I:%M %p"
    tz = ZoneInfo("Europe/Oslo")

    # Act
    prayer_times = PrayerTimes(coordinates, date, calculation_parameters=parameters)

    # Assert
    assert prayer_times.fajr.astimezone(tz).strftime(format) == "07:34 AM"
    assert prayer_times.sunrise.astimezone(tz).strftime(format) == "09:19 AM"
    assert prayer_times.dhuhr.astimezone(tz).strftime(format) == "12:25 PM"
    assert prayer_times.asr.astimezone(tz).strftime(format) == "01:36 PM"
    assert prayer_times.maghrib.astimezone(tz).strftime(format) == "03:25 PM"
    assert prayer_times.isha.astimezone(tz).strftime(format) == "05:02 PM"


def test_moon_sighting_method_high_lat_different_times_of_year():
    # Values from http://www.moonsighting.com/pray.php
    # Arrange
    params = CalculationParameters(method=CalculationMethod.MOON_SIGHTING_COMMITTEE)
    coordinates = (59.9094, 10.7349)
    format = "%I:%M %p"
    tz = ZoneInfo("Europe/Oslo")

    # Act, Assert
    date = DateComponents(2015, 7, 12)
    prayer_times = PrayerTimes(coordinates, date, calculation_parameters=params)
    assert prayer_times.fajr.astimezone(tz).strftime(format) == "03:26 AM"

    date = DateComponents(2015, 10, 12)
    prayer_times = PrayerTimes(coordinates, date, calculation_parameters=params)
    assert prayer_times.dhuhr.astimezone(tz).strftime(format) == "01:09 PM"

    date = DateComponents(2015, 4, 12)
    prayer_times = PrayerTimes(coordinates, date, calculation_parameters=params)
    assert prayer_times.asr.astimezone(tz).strftime(format) == "05:04 PM"

    date = DateComponents(2015, 5, 12)
    prayer_times = PrayerTimes(coordinates, date, calculation_parameters=params)
    assert prayer_times.maghrib.astimezone(tz).strftime(format) == "09:43 PM"

    date = DateComponents(2015, 9, 12)
    prayer_times = PrayerTimes(coordinates, date, calculation_parameters=params)
    assert prayer_times.isha.astimezone(tz).strftime(format) == "09:03 PM"


def test_prayer_times_second_precision_locked():
    # minute-resolution goldens cannot catch rounding drift; lock full
    # precision in UTC so future rounding changes show up here
    date = DateComponents(2015, 7, 12)
    params = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    params.madhab = Madhab.HANAFI
    prayer_times = PrayerTimes((35.7750, -78.6336), date, calculation_parameters=params)

    assert prayer_times.fajr.strftime("%H:%M:%S") == "08:42:00"
    assert prayer_times.sunrise.strftime("%H:%M:%S") == "10:08:00"
    assert prayer_times.dhuhr.strftime("%H:%M:%S") == "17:21:00"
    assert prayer_times.asr.strftime("%H:%M:%S") == "22:22:00"
    assert prayer_times.maghrib.strftime("%H:%M:%S") == "00:32:00"
    assert prayer_times.isha.strftime("%H:%M:%S") == "01:57:00"


def test_polar_night_error_message():
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.polar_circle_rule = PolarCircleRule.NONE

    with pytest.raises(AstronomicalError, match="(?i)polar"):
        PrayerTimes(
            (68.35, 18.83),
            DateComponents(2015, 12, 21),
            calculation_parameters=params,
        )


def test_invalid_madhab_raises_configuration_error():
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.madhab = None

    with pytest.raises(ConfigurationError, match="(?i)madhab"):
        PrayerTimes(
            (35.7750, -78.6336),
            DateComponents(2015, 7, 12),
            calculation_parameters=params,
        )


def test_prayer_times_accepts_coordinates_object():
    date = DateComponents(2015, 7, 12)
    params_tuple = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    params_coords = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)

    from_tuple = PrayerTimes(
        (35.7750, -78.6336), date, calculation_parameters=params_tuple
    )
    from_object = PrayerTimes(
        Coordinates(35.7750, -78.6336), date, calculation_parameters=params_coords
    )

    assert from_object.fajr == from_tuple.fajr
    assert from_object.isha == from_tuple.isha


def test_prayer_times_accepts_datetime_and_date_components():
    params_dt = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    params_dc = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)

    from_datetime = PrayerTimes(
        (35.7750, -78.6336),
        datetime(2015, 7, 12, tzinfo=timezone.utc),
        calculation_parameters=params_dt,
    )
    from_components = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=params_dc,
    )

    assert from_components.fajr == from_datetime.fajr
    assert from_components.isha == from_datetime.isha


def test_prayer_times_timezone_conversion():
    # Arrange
    calculation_method = CalculationMethod.MOON_SIGHTING_COMMITTEE
    coordinates = (51.49799827422162, -0.1358135027951458)
    format = "%I:%M %p"
    tz = ZoneInfo("Europe/London")

    # Winter time, UTC and GMT share the same time
    date_winter = DateComponents(2022, 1, 1)

    # Summer time, BST: UTC + 1
    date_summer = DateComponents(2022, 8, 1)

    # Act,  Assert
    prayer_times = PrayerTimes(
        coordinates, date_winter, calculation_method=calculation_method
    )
    assert prayer_times.fajr.strftime(format) == "06:25 AM"

    prayer_times = PrayerTimes(
        coordinates, date_winter, calculation_method=calculation_method, time_zone=tz
    )
    assert prayer_times.fajr.strftime(format) == "06:25 AM"

    prayer_times = PrayerTimes(
        coordinates, date_summer, calculation_method=calculation_method
    )
    assert prayer_times.fajr.strftime(format) == "02:37 AM"

    prayer_times = PrayerTimes(
        coordinates, date_summer, calculation_method=calculation_method, time_zone=tz
    )
    assert prayer_times.fajr.strftime(format) == "03:37 AM"


def test_twilight_preset_definitions_locked():
    # Slice 2.1: any change to METHODS_PARAMETERS must fail loudly here.
    # (fajr_angle, isha_angle, isha_interval, fajr, sunrise, dhuhr, asr,
    # maghrib, isha method_adjustments).
    expected = {
        CalculationMethod.NONE: (0.0, 0.0, 0, (0, 0, 0, 0, 0, 0)),
        CalculationMethod.MUSLIM_WORLD_LEAGUE: (18.0, 17.0, 0, (0, 0, 1, 0, 0, 0)),
        CalculationMethod.EGYPTIAN: (19.5, 17.5, 0, (0, 0, 1, 0, 0, 0)),
        CalculationMethod.KARACHI: (18.0, 18.0, 0, (0, 0, 1, 0, 0, 0)),
        CalculationMethod.UMM_AL_QURA: (18.5, 0.0, 90, (0, 0, 0, 0, 0, 0)),
        CalculationMethod.DUBAI: (18.2, 18.2, 0, (0, -3, 3, 3, 3, 0)),
        CalculationMethod.MOON_SIGHTING_COMMITTEE: (
            18.0,
            18.0,
            0,
            (0, 0, 5, 0, 3, 0),
        ),
        CalculationMethod.NORTH_AMERICA: (15.0, 15.0, 0, (0, 0, 1, 0, 0, 0)),
        CalculationMethod.KUWAIT: (18.0, 17.5, 0, (0, 0, 0, 0, 0, 0)),
        CalculationMethod.QATAR: (18.0, 0.0, 90, (0, 0, 0, 0, 0, 0)),
        CalculationMethod.SINGAPORE: (20.0, 18.0, 0, (0, 0, 1, 0, 0, 0)),
        CalculationMethod.UOIF: (12.0, 12.0, 0, (0, 0, 0, 0, 0, 0)),
        CalculationMethod.JAKIM: (18.0, 18.0, 0, (0, 0, 1, 0, 0, 0)),
    }

    assert set(expected) == set(CalculationMethod)

    for method, (
        fajr_angle,
        isha_angle,
        isha_interval,
        adjustments,
    ) in expected.items():
        params = CalculationParameters(method=method)
        assert params.fajr_angle == fajr_angle
        assert params.isha_angle == isha_angle
        assert params.isha_interval == isha_interval
        method_adjustments = params.method_adjustments
        assert (
            method_adjustments.fajr,
            method_adjustments.sunrise,
            method_adjustments.dhuhr,
            method_adjustments.asr,
            method_adjustments.maghrib,
            method_adjustments.isha,
        ) == adjustments
        assert method_adjustments.imsak == 0
        assert method_adjustments.ishraq == 0
        assert method_adjustments.dhuha == 0
        assert params.imsak_offset == 10
        assert params.ishraq_offset == 15
        assert params.dhuha_offset == 28
        assert params.elevation_m == 0.0


def test_milestone_twilight_rows_pinned():
    # Milestone Phase 2 rows mapped to presets: MWL 18/17, Egypt 19.5/17.5,
    # ISNA 15/15 via NORTH_AMERICA, JAKIM 18/18, Singapore 20/18.
    assert (
        CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE).fajr_angle
        == 18.0
    )
    assert (
        CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE).isha_angle
        == 17.0
    )
    assert CalculationParameters(method=CalculationMethod.EGYPTIAN).fajr_angle == 19.5
    assert CalculationParameters(method=CalculationMethod.EGYPTIAN).isha_angle == 17.5
    assert (
        CalculationParameters(method=CalculationMethod.NORTH_AMERICA).fajr_angle == 15.0
    )
    assert (
        CalculationParameters(method=CalculationMethod.NORTH_AMERICA).isha_angle == 15.0
    )
    assert CalculationParameters(method=CalculationMethod.SINGAPORE).fajr_angle == 20.0
    assert CalculationParameters(method=CalculationMethod.SINGAPORE).isha_angle == 18.0
    assert CalculationParameters(method=CalculationMethod.JAKIM).fajr_angle == 18.0
    assert CalculationParameters(method=CalculationMethod.JAKIM).isha_angle == 18.0


@pytest.mark.parametrize(
    "method, fajr, sunrise, dhuhr, asr, maghrib, isha",
    [
        (
            CalculationMethod.NONE,
            "10:13:00",
            "10:08:00",
            "17:20:00",
            "21:09:00",
            "00:32:00",
            "00:28:00",
        ),
        (
            CalculationMethod.MUSLIM_WORLD_LEAGUE,
            "08:22:00",
            "10:08:00",
            "17:21:00",
            "21:09:00",
            "00:32:00",
            "02:11:00",
        ),
        (
            CalculationMethod.EGYPTIAN,
            "08:11:00",
            "10:08:00",
            "17:21:00",
            "21:09:00",
            "00:32:00",
            "02:14:00",
        ),
        (
            CalculationMethod.KARACHI,
            "08:22:00",
            "10:08:00",
            "17:21:00",
            "21:09:00",
            "00:32:00",
            "02:18:00",
        ),
        (
            CalculationMethod.UMM_AL_QURA,
            "08:18:00",
            "10:08:00",
            "17:20:00",
            "21:09:00",
            "00:32:00",
            "02:02:00",
        ),
        (
            CalculationMethod.DUBAI,
            "08:20:00",
            "10:05:00",
            "17:23:00",
            "21:12:00",
            "00:35:00",
            "02:19:00",
        ),
        (
            CalculationMethod.MOON_SIGHTING_COMMITTEE,
            "08:26:00",
            "10:08:00",
            "17:25:00",
            "21:09:00",
            "00:35:00",
            "01:47:00",
        ),
        (
            CalculationMethod.NORTH_AMERICA,
            "08:42:00",
            "10:08:00",
            "17:21:00",
            "21:09:00",
            "00:32:00",
            "01:57:00",
        ),
        (
            CalculationMethod.KUWAIT,
            "08:22:00",
            "10:08:00",
            "17:20:00",
            "21:09:00",
            "00:32:00",
            "02:14:00",
        ),
        (
            CalculationMethod.QATAR,
            "08:22:00",
            "10:08:00",
            "17:20:00",
            "21:09:00",
            "00:32:00",
            "02:02:00",
        ),
        (
            CalculationMethod.SINGAPORE,
            "08:07:00",
            "10:08:00",
            "17:21:00",
            "21:09:00",
            "00:32:00",
            "02:18:00",
        ),
        (
            CalculationMethod.UOIF,
            "09:02:00",
            "10:08:00",
            "17:20:00",
            "21:09:00",
            "00:32:00",
            "01:38:00",
        ),
        (
            CalculationMethod.JAKIM,
            "08:22:00",
            "10:08:00",
            "17:21:00",
            "21:09:00",
            "00:32:00",
            "02:18:00",
        ),
    ],
)
def test_twilight_preset_goldens_raleigh(
    method, fajr, sunrise, dhuhr, asr, maghrib, isha
):
    # One golden day per method: Raleigh (35.7750, -78.6336), 2015-07-12, UTC.
    # Angle-vs-interval mode is asserted below for UMM_AL_QURA/QATAR.
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_method=method,
    )

    assert prayer_times.fajr.strftime("%H:%M:%S") == fajr
    assert prayer_times.sunrise.strftime("%H:%M:%S") == sunrise
    assert prayer_times.dhuhr.strftime("%H:%M:%S") == dhuhr
    assert prayer_times.asr.strftime("%H:%M:%S") == asr
    assert prayer_times.maghrib.strftime("%H:%M:%S") == maghrib
    assert prayer_times.isha.strftime("%H:%M:%S") == isha

    if method in (CalculationMethod.UMM_AL_QURA, CalculationMethod.QATAR):
        assert (prayer_times.isha - prayer_times.maghrib).total_seconds() / 60 == 90
    elif method is not CalculationMethod.NONE:
        assert (
            prayer_times.fajr
            <= prayer_times.sunrise
            <= prayer_times.dhuhr
            <= prayer_times.asr
            <= prayer_times.maghrib
            <= prayer_times.isha
        )


def test_jakim_uses_current_18_degree_fajr():
    # JAKIM moved its Subuh criterion to 18 degrees; SINGAPORE keeps 20/18.
    # The presets share Isha, interval mode, and dhuhr+1, so only Fajr differs.
    jakim = CalculationParameters(method=CalculationMethod.JAKIM)
    singapore = CalculationParameters(method=CalculationMethod.SINGAPORE)

    assert (jakim.fajr_angle, jakim.isha_angle, jakim.isha_interval) == (
        18.0,
        18.0,
        0,
    )
    assert (singapore.fajr_angle, singapore.isha_angle, singapore.isha_interval) == (
        20.0,
        18.0,
        0,
    )
    assert (
        jakim.method_adjustments.fajr,
        jakim.method_adjustments.sunrise,
        jakim.method_adjustments.dhuhr,
        jakim.method_adjustments.asr,
        jakim.method_adjustments.maghrib,
        jakim.method_adjustments.isha,
    ) == (
        singapore.method_adjustments.fajr,
        singapore.method_adjustments.sunrise,
        singapore.method_adjustments.dhuhr,
        singapore.method_adjustments.asr,
        singapore.method_adjustments.maghrib,
        singapore.method_adjustments.isha,
    )

    for coordinates, prayer_date in [
        ((35.7750, -78.6336), DateComponents(2015, 7, 12)),
        ((3.1390, 101.6869), DateComponents(2015, 7, 12)),
        ((5.9804, 116.0735), DateComponents(2015, 7, 12)),
        ((3.1390, 101.6869), DateComponents(2025, 1, 15)),
        ((5.9804, 116.0735), DateComponents(2025, 1, 15)),
    ]:
        jakim_times = PrayerTimes(
            coordinates, prayer_date, calculation_method=CalculationMethod.JAKIM
        )
        singapore_times = PrayerTimes(
            coordinates, prayer_date, calculation_method=CalculationMethod.SINGAPORE
        )

        # 18-degree Fajr is later than 20-degree Fajr; the rest is identical.
        assert jakim_times.fajr > singapore_times.fajr
        assert jakim_times.sunrise == singapore_times.sunrise
        assert jakim_times.dhuhr == singapore_times.dhuhr
        assert jakim_times.asr == singapore_times.asr
        assert jakim_times.maghrib == singapore_times.maghrib
        assert jakim_times.isha == singapore_times.isha


@pytest.mark.parametrize(
    "coordinates, date, fajr, sunrise, dhuhr, asr, maghrib, isha",
    [
        (
            (3.1390, 101.6869),
            DateComponents(2025, 1, 15),
            "22:10:00",
            "23:24:00",
            "05:24:00",
            "08:46:00",
            "11:21:00",
            "12:35:00",
        ),
        (
            (5.9804, 116.0735),
            DateComponents(2025, 1, 15),
            "21:17:00",
            "22:31:00",
            "04:26:00",
            "07:48:00",
            "10:20:00",
            "11:33:00",
        ),
    ],
)
def test_jakim_malaysian_zone_goldens(
    coordinates, date, fajr, sunrise, dhuhr, asr, maghrib, isha
):
    # Takwim verification anchors: Kuala Lumpur (3.1390, 101.6869) and
    # Kota Kinabalu (5.9804, 116.0735) on 2025-01-15, UTC. These lock the
    # computed 18/18 baseline; the official 2025-01-16 rows are checked in
    # test_esolat_takwim_portal_rows against the published 0-2 minute ihtiyat.
    prayer_times = PrayerTimes(
        coordinates, date, calculation_method=CalculationMethod.JAKIM
    )

    assert prayer_times.fajr.strftime("%H:%M:%S") == fajr
    assert prayer_times.sunrise.strftime("%H:%M:%S") == sunrise
    assert prayer_times.dhuhr.strftime("%H:%M:%S") == dhuhr
    assert prayer_times.asr.strftime("%H:%M:%S") == asr
    assert prayer_times.maghrib.strftime("%H:%M:%S") == maghrib
    assert prayer_times.isha.strftime("%H:%M:%S") == isha


@pytest.mark.parametrize(
    "coordinates, local_date, official_utc, ihtiyat_minutes",
    [
        pytest.param(
            (3.1390, 101.6869),  # Kuala Lumpur
            date(2025, 1, 16),
            {
                "fajr": "2025-01-15T22:13:00+00:00",
                "sunrise": "2025-01-15T23:24:00+00:00",
                "dhuhr": "2025-01-16T05:26:00+00:00",
                "asr": "2025-01-16T08:48:00+00:00",
                "maghrib": "2025-01-16T11:23:00+00:00",
                "isha": "2025-01-16T12:37:00+00:00",
            },
            {
                "fajr": 2,
                "sunrise": 0,
                "dhuhr": 2,
                "asr": 1,
                "maghrib": 1,
                "isha": 2,
            },
            id="WLY01-2025-01-16",
        ),
        pytest.param(
            (5.9804, 116.0735),  # Kota Kinabalu
            date(2025, 1, 16),
            {
                "fajr": "2025-01-15T21:18:00+00:00",
                "sunrise": "2025-01-15T22:31:00+00:00",
                "dhuhr": "2025-01-16T04:28:00+00:00",
                "asr": "2025-01-16T07:49:00+00:00",
                "maghrib": "2025-01-16T10:21:00+00:00",
                "isha": "2025-01-16T11:35:00+00:00",
            },
            {
                "fajr": 1,
                "sunrise": 0,
                "dhuhr": 2,
                "asr": 1,
                "maghrib": 1,
                "isha": 1,
            },
            id="SBH07-2025-01-16",
        ),
    ],
)
def test_esolat_takwim_portal_rows(
    coordinates, local_date, official_utc, ihtiyat_minutes
):
    # Official JAKIM Takwim rows for the local prayer date 2025-01-16
    # (MYT, UTC+8), converted to UTC. Retrieved 2026-10-24 from:
    # - WLY01 (KL/Putrajaya): JADUAL-WAKTU-SOLAT-WPKLPTJ-2025.pdf, 16 Jan row
    #   (06:03 06:13 07:24 13:26 16:48 19:23 20:37).
    # - SBH07 (Kota Kinabalu): e-solat XML feed snapshot 2025-01-16 10:31:15
    #   (05:08 05:18 06:31 12:28 15:49 18:21 19:35).
    # The published tables add a 0-2 minute ihtiyat. Asserting that bound --
    # not subtracting an arbitrary per-prayer offset -- makes the 18-degree
    # Fajr criterion testable: a 20-degree Fajr is 9-11 minutes early and
    # falls outside it.
    prayer_times = PrayerTimes(
        coordinates,
        DateComponents(local_date.year, local_date.month, local_date.day),
        calculation_method=CalculationMethod.JAKIM,
    )
    myt = timezone(timedelta(hours=8))

    for prayer, official in official_utc.items():
        computed = getattr(prayer_times, prayer)
        assert computed.astimezone(myt).date() == local_date, prayer
        delta = datetime.fromisoformat(official) - computed
        assert timedelta(0) <= delta <= timedelta(minutes=2), (
            f"{prayer} on {local_date}: computed {computed.isoformat()}, "
            f"official {official}, delta {delta}"
        )
        assert delta == timedelta(minutes=ihtiyat_minutes[prayer]), (
            f"{prayer} on {local_date}: expected {ihtiyat_minutes[prayer]}m "
            f"ihtiyat, got {delta}"
        )


def test_imsak_defaults_to_fajr_minus_ten():
    # Slice 2.3: Imsak = Fajr - imsak_offset (default 10). Raleigh golden:
    # fajr 08:42 UTC -> imsak 08:32 UTC.
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_method=CalculationMethod.NORTH_AMERICA,
    )

    assert prayer_times.imsak.strftime("%H:%M:%S") == "08:32:00"
    assert prayer_times.time_for_prayer(Prayer.IMSAK) == prayer_times.imsak
    assert prayer_times.imsak < prayer_times.fajr


def test_imsak_custom_offset_and_none_method():
    params = CalculationParameters(
        method=CalculationMethod.NORTH_AMERICA, imsak_offset=15
    )
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=params,
    )
    assert prayer_times.imsak.strftime("%H:%M:%S") == "08:27:00"

    params_zero = CalculationParameters(
        method=CalculationMethod.NORTH_AMERICA, imsak_offset=0
    )
    prayer_times_zero = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=params_zero,
    )
    assert prayer_times_zero.imsak == prayer_times_zero.fajr

    # NONE is angle-less but Imsak stays defined as Fajr - offset.
    prayer_times_none = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_method=CalculationMethod.NONE,
    )
    assert prayer_times_none.imsak.strftime("%H:%M:%S") == "10:03:00"


def test_imsak_follows_fajr_adjustments():
    # Imsak tracks rounded Fajr: fajr adjustments flow through, imsak
    # adjustments apply on top. Integer offsets commute with half-up
    # minute rounding, so pre/post-rounding order is equivalent.
    base = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    pt_base = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=base,
    )

    shifted = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    shifted.adjustments.fajr = 10
    pt_shifted = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=shifted,
    )
    assert pt_shifted.fajr - pt_base.fajr == timedelta(minutes=10)
    assert pt_shifted.imsak - pt_base.imsak == timedelta(minutes=10)

    tweak = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    tweak.adjustments.imsak = 2
    pt_tweak = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=tweak,
    )
    assert pt_tweak.imsak - pt_base.imsak == timedelta(minutes=2)
    assert pt_tweak.fajr == pt_base.fajr


def test_negative_imsak_offset_raises():
    with pytest.raises(ValidationError, match="(?i)imsak"):
        CalculationParameters(method=CalculationMethod.NORTH_AMERICA, imsak_offset=-1)


def test_syuruk_ishraq_dhuha_goldens():
    # Slice 2.4: Raleigh 2015-07-12 NORTH_AMERICA, UTC. Syuruk == sunrise;
    # Ishraq = sunrise+15; Dhuha window starts at sunrise+28 (single
    # Malaysian source, not universal fiqh).
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_method=CalculationMethod.NORTH_AMERICA,
    )

    assert prayer_times.syuruk == prayer_times.sunrise
    assert prayer_times.syuruk.strftime("%H:%M:%S") == "10:08:00"
    assert prayer_times.ishraq.strftime("%H:%M:%S") == "10:23:00"
    assert prayer_times.dhuha.strftime("%H:%M:%S") == "10:36:00"
    assert prayer_times.time_for_prayer(Prayer.SYURUK) == prayer_times.syuruk
    assert prayer_times.time_for_prayer(Prayer.ISHRAQ) == prayer_times.ishraq
    assert prayer_times.time_for_prayer(Prayer.DHUHA) == prayer_times.dhuha


def test_derived_markers_ordering_and_offsets():
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_method=CalculationMethod.NORTH_AMERICA,
    )

    assert (
        prayer_times.fajr
        < prayer_times.sunrise
        <= prayer_times.syuruk
        <= prayer_times.ishraq
        <= prayer_times.dhuha
        <= prayer_times.dhuhr
    )

    custom = CalculationParameters(
        method=CalculationMethod.NORTH_AMERICA, ishraq_offset=20, dhuha_offset=30
    )
    prayer_times_custom = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=custom,
    )
    assert prayer_times_custom.ishraq.strftime("%H:%M:%S") == "10:28:00"
    assert prayer_times_custom.dhuha.strftime("%H:%M:%S") == "10:38:00"

    # Sunrise adjustments flow through to derived markers; marker-specific
    # adjustments apply on top without moving sunrise itself.
    tweak = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    tweak.adjustments.sunrise = 5
    prayer_times_tweak = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=tweak,
    )
    assert prayer_times_tweak.syuruk == prayer_times_tweak.sunrise
    assert prayer_times_tweak.ishraq - prayer_times.ishraq == timedelta(minutes=5)

    ishraq_tweak = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    ishraq_tweak.adjustments.ishraq = 3
    prayer_times_ishraq = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=ishraq_tweak,
    )
    assert prayer_times_ishraq.ishraq - prayer_times.ishraq == timedelta(minutes=3)
    assert prayer_times_ishraq.sunrise == prayer_times.sunrise


def test_derived_markers_timezone_aware():
    tz = ZoneInfo("America/New_York")
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_method=CalculationMethod.NORTH_AMERICA,
        time_zone=tz,
    )

    assert prayer_times.syuruk.tzinfo is not None
    assert prayer_times.syuruk == prayer_times.sunrise
    assert prayer_times.ishraq - prayer_times.sunrise == timedelta(minutes=15)
    assert prayer_times.dhuha - prayer_times.sunrise == timedelta(minutes=28)


def test_negative_ishraq_dhuha_offsets_raise():
    with pytest.raises(ValidationError, match="(?i)ishraq"):
        CalculationParameters(method=CalculationMethod.NORTH_AMERICA, ishraq_offset=-1)
    with pytest.raises(ValidationError, match="(?i)dhuha"):
        CalculationParameters(method=CalculationMethod.NORTH_AMERICA, dhuha_offset=-1)


def test_elevation_default_zero_preserves_goldens():
    # Slice 2.6: default elevation_m=0 keeps every sea-level golden.
    params = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    assert params.elevation_m == 0.0

    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=params,
    )
    assert prayer_times.sunrise.strftime("%H:%M:%S") == "10:08:00"
    assert prayer_times.maghrib.strftime("%H:%M:%S") == "00:32:00"


def test_elevation_shifts_sunrise_sunset_only():
    # 1000 m of eye height lowers the visible horizon (dip ≈ 0.93°):
    # sunrise earlier, sunset/maghrib later by minutes; transit-based
    # dhuhr and angle-based fajr/isha are unaffected.
    base = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    pt_base = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=base,
    )

    high = CalculationParameters(
        method=CalculationMethod.NORTH_AMERICA, elevation_m=1000.0
    )
    pt_high = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=high,
    )

    sunrise_shift = (pt_high.sunrise - pt_base.sunrise).total_seconds() / 60
    sunset_shift = (pt_high.maghrib - pt_base.maghrib).total_seconds() / 60
    assert 1 <= -sunrise_shift <= 8
    assert 1 <= sunset_shift <= 8
    assert pt_high.dhuhr == pt_base.dhuhr
    assert pt_high.fajr == pt_base.fajr
    assert pt_high.isha == pt_base.isha


def test_invalid_elevation_raises():
    for bad in (-1.0, float("nan"), float("inf"), True, "100"):
        with pytest.raises(ValidationError, match="(?i)elevation"):
            CalculationParameters(
                method=CalculationMethod.NORTH_AMERICA, elevation_m=bad
            )


def test_umm_al_qura_ramadan_mode():
    # Slice 2.7: opt-in is_ramadan flag gives 120 minutes total after
    # Maghrib for UMM_AL_QURA (not an additive +30). Default stays 90.
    coordinates = (21.422510, 39.826168)
    date = DateComponents(2022, 8, 8)

    base = CalculationParameters(method=CalculationMethod.UMM_AL_QURA)
    assert base.is_ramadan is False
    pt_base = PrayerTimes(coordinates, date, calculation_parameters=base)
    assert (pt_base.isha - pt_base.maghrib).total_seconds() / 60 == 90

    ramadan = CalculationParameters(
        method=CalculationMethod.UMM_AL_QURA, is_ramadan=True
    )
    pt_ramadan = PrayerTimes(coordinates, date, calculation_parameters=ramadan)
    assert (pt_ramadan.isha - pt_ramadan.maghrib).total_seconds() / 60 == 120
    assert pt_ramadan.fajr == pt_base.fajr
    assert pt_ramadan.maghrib == pt_base.maghrib


def test_ramadan_flag_leaves_other_methods_unchanged():
    coordinates = (21.422510, 39.826168)
    date = DateComponents(2022, 8, 8)

    # QATAR shares the 90-minute interval shape but the Ramadan rule is
    # Umm al-Qura-specific: unaffected.
    qatar = CalculationParameters(method=CalculationMethod.QATAR, is_ramadan=True)
    pt_qatar = PrayerTimes(coordinates, date, calculation_parameters=qatar)
    assert (pt_qatar.isha - pt_qatar.maghrib).total_seconds() / 60 == 90

    # Angle-based methods ignore the flag entirely.
    angle = CalculationParameters(
        method=CalculationMethod.MUSLIM_WORLD_LEAGUE, is_ramadan=True
    )
    pt_angle = PrayerTimes(coordinates, date, calculation_parameters=angle)
    pt_plain = PrayerTimes(
        coordinates,
        date,
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )
    assert pt_angle.isha == pt_plain.isha
