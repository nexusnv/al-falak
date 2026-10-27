import pytest
from datetime import date, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from alfalak import (
    CalculationMethod,
    CalculationParameters,
    PrayerTimes,
)
from alfalak.util.DateComponents import DateComponents
from alfalak.calculation import PolarCircleRule
from alfalak.exceptions import AstronomicalError

PRAYERS = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")


def _build_pt(lat, lon, y, m, d, method=CalculationMethod.MUSLIM_WORLD_LEAGUE, tz=None):
    return PrayerTimes(
        (lat, lon),
        DateComponents(y, m, d),
        calculation_method=method,
        time_zone=tz,
    )


def _assert_ordering(pt):
    values = [getattr(pt, prayer) for prayer in PRAYERS]
    assert values == sorted(values)


def test_mxc_dac_abolition_2023_04_02():
    tz = ZoneInfo("America/Mexico_City")
    pt = _build_pt(19.432608, -99.133209, 2023, 4, 2, tz=tz)
    # Mexico abolished DST in October 2022; April 2023 is CST (UTC-6)
    # year-round.
    for prayer in PRAYERS:
        assert getattr(pt, prayer).utcoffset() == timedelta(hours=-6), prayer
    assert pt.fajr.date() == date(2023, 4, 2)
    _assert_ordering(pt)


def test_tokyo_boundary_sanity():
    tz = ZoneInfo("Asia/Tokyo")
    pt = _build_pt(35.6895, 139.6917, 2024, 3, 20, tz=tz)
    # UTC+9: the local prayer date is one day ahead of the UTC date of the
    # early-morning prayers.
    assert pt.fajr.utcoffset() == timedelta(hours=9)
    assert pt.fajr.date() == date(2024, 3, 20)
    assert pt.fajr.astimezone(timezone.utc).date() == date(2024, 3, 19)
    _assert_ordering(pt)


def test_arctic_high_latitude_resolves_with_default_rule():
    tz = ZoneInfo("Europe/Oslo")
    pt = _build_pt(69.6492, 18.9553, 2024, 6, 21, tz=tz)
    # 69.6N is inside the Arctic Circle; the default NEAREST_LATITUDE rule
    # resolves the polar day instead of raising.
    for prayer in PRAYERS:
        assert getattr(pt, prayer).utcoffset() == timedelta(hours=2), prayer
    _assert_ordering(pt)


def test_arctic_polar_day_raises_with_none_rule():
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.polar_circle_rule = PolarCircleRule.NONE
    with pytest.raises(AstronomicalError):
        PrayerTimes(
            (69.6492, 18.9553),
            DateComponents(2024, 6, 21),
            calculation_parameters=params,
            time_zone=ZoneInfo("Europe/Oslo"),
        )


def test_arctic_polar_night_raises_with_none_rule():
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.polar_circle_rule = PolarCircleRule.NONE
    with pytest.raises(AstronomicalError):
        PrayerTimes(
            (69.6492, 18.9553),
            DateComponents(2024, 12, 21),
            calculation_parameters=params,
            time_zone=ZoneInfo("Europe/Oslo"),
        )


def test_africa_cairo_2023_plus():
    tz = ZoneInfo("Africa/Cairo")
    pt = _build_pt(30.0444, 31.2357, 2024, 4, 15, tz=tz)
    assert pt.fajr.utcoffset() == timedelta(hours=2)
    _assert_ordering(pt)


def test_australia_lord_howe_dst_behavior():
    try:
        tz = ZoneInfo("Australia/Lord_Howe")
    except ZoneInfoNotFoundError:
        pytest.skip("Australia/Lord_Howe not present in tzdata")
    pt = _build_pt(-31.5549, 159.0817, 2024, 1, 15, tz=tz)
    # Southern summer: Lord Howe is UTC+11 (30-minute DST shift).
    assert pt.fajr.utcoffset() == timedelta(hours=11)
    _assert_ordering(pt)


def test_utc_zone_offsets_are_zero():
    pt = _build_pt(40.7128, -74.0060, 2024, 3, 10, tz=ZoneInfo("UTC"))
    for prayer in PRAYERS:
        assert getattr(pt, prayer).utcoffset() == timedelta(0), prayer
    _assert_ordering(pt)


def test_europe_paris_transition():
    tz = ZoneInfo("Europe/Paris")
    pt = _build_pt(48.8566, 2.3522, 2024, 3, 31, tz=tz)
    # 2024-03-31 is the CET->CEST spring-forward; fajr is after the 02:00
    # transition, so it carries UTC+2.
    assert pt.fajr.utcoffset() == timedelta(hours=2)
    _assert_ordering(pt)


def test_america_new_york_transition():
    tz = ZoneInfo("America/New_York")
    pt = _build_pt(40.7128, -74.0060, 2024, 3, 10, tz=tz)
    # 2024-03-10 is the EST->EDT spring-forward; fajr is after the 02:00
    # transition, so it carries UTC-4.
    assert pt.fajr.utcoffset() == timedelta(hours=-4)
    _assert_ordering(pt)


def test_pacific_kiritimati_far_east():
    try:
        tz = ZoneInfo("Pacific/Kiritimati")
    except ZoneInfoNotFoundError:
        pytest.skip("Pacific/Kiritimati not present in tzdata")
    pt = _build_pt(1.8729, -157.4381, 2024, 1, 15, tz=tz)
    # UTC+14: the local calendar date is one day ahead of the UTC date used
    # for the solar calculation.
    assert pt.fajr.utcoffset() == timedelta(hours=14)
    assert pt.fajr.date() == date(2024, 1, 16)
    assert pt.fajr.astimezone(timezone.utc).date() == date(2024, 1, 15)
    _assert_ordering(pt)


def test_tzdata_only_zone_if_present():
    expected_offsets = {
        "Pacific/Chatham": timedelta(hours=12, minutes=45),
        "Pacific/Apia": timedelta(hours=13),
        "Asia/Colombo": timedelta(hours=5, minutes=30),
    }
    found = None
    for candidate in expected_offsets:
        try:
            ZoneInfo(candidate)
            found = candidate
            break
        except ZoneInfoNotFoundError:
            continue
    if found is None:
        pytest.skip("no additional tzdata zones present")
    pt = _build_pt(0, 0, 2024, 6, 15, tz=ZoneInfo(found))
    assert pt.fajr.utcoffset() == expected_offsets[found]
    _assert_ordering(pt)
