import pytest
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from alfalak import (
    CalculationMethod,
    CalculationParameters,
    PrayerTimes,
)
from alfalak.data.Coordinates import Coordinates
from alfalak.util.DateComponents import DateComponents
from alfalak.calculation import PolarCircleRule
from alfalak.exceptions import AstronomicalError


def _build_pt(lat, lon, y, m, d, method=CalculationMethod.MUSLIM_WORLD_LEAGUE, tz=None):
    return PrayerTimes(
        (lat, lon),
        DateComponents(y, m, d),
        calculation_method=method,
        time_zone=tz,
    )


def test_mxc_dac_abolition_2023_04_02():
    pt = _build_pt(
        19.432608, -99.133209, 2023, 4, 2, tz=ZoneInfo("America/Mexico_City")
    )
    assert (
        pt._prayer_date.year == 2023
        and pt._prayer_date.month == 4
        and pt._prayer_date.day == 2
    )
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_tokyo_boundary_sanity():
    pt = _build_pt(35.6895, 139.6917, 2024, 3, 20, tz=ZoneInfo("Asia/Tokyo"))
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_arctic_high_latitude_defined_or_error():
    lat = 66.5
    try:
        pt = _build_pt(lat, 18.96, 2024, 6, 21, tz=ZoneInfo("UTC"))
        assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha
    except AstronomicalError:
        pass


def test_africa_cairo_2023_plus():
    pt = _build_pt(30.0444, 31.2357, 2024, 4, 15, tz=ZoneInfo("Africa/Cairo"))
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_australia_lord_howe_dst_behavior():
    try:
        tz = ZoneInfo("Australia/Lord_Howe")
    except ZoneInfoNotFoundError:
        pytest.skip("Australia/Lord_Howe not present in tzdata")
    pt = _build_pt(-31.5549, 159.0817, 2024, 1, 15, tz=tz)
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_utc_across_dst():
    pt = _build_pt(40.7128, -74.0060, 2024, 3, 10, tz=ZoneInfo("UTC"))
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_europe_paris_transition():
    pt = _build_pt(48.8566, 2.3522, 2024, 3, 31, tz=ZoneInfo("Europe/Paris"))
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_america_new_york_transition():
    pt = _build_pt(40.7128, -74.0060, 2024, 3, 10, tz=ZoneInfo("America/New_York"))
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_pacific_kiritimati_far_east():
    try:
        tz = ZoneInfo("Pacific/Kiritimati")
    except ZoneInfoNotFoundError:
        pytest.skip("Pacific/Kiritimati not present in tzdata")
    pt = _build_pt(1.8729, -157.4381, 2024, 1, 15, tz=tz)
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_tzdata_only_zone_if_present():
    candidates = ["Pacific/Chatham", "Pacific/Apia", "Asia/Colombo"]
    found = None
    for c in candidates:
        try:
            ZoneInfo(c)
            found = c
            break
        except ZoneInfoNotFoundError:
            continue
    if found is None:
        pytest.skip("no additional tzdata zones present")
    pt = _build_pt(0, 0, 2024, 6, 15, tz=ZoneInfo(found))
    assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha


def test_high_lat_polar_rule_none_behavior():
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.polar_circle_rule = PolarCircleRule.NONE
    try:
        pt = PrayerTimes(
            (66.4, 18.96), DateComponents(2015, 12, 21), calculation_parameters=params
        )
        assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha
    except AstronomicalError:
        pass
