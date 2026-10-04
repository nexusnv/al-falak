import pytest

import alfalak
from alfalak import PrayerTimes as RootPrayerTimes
from alfalak import Qibla, SunnahTimes
from alfalak.astronomy.CrescentGeometry import (
    CrescentGeometry,
    crescent_geometry_at_sunset,
)
from alfalak.astronomy.DeltaT import delta_t
from alfalak.astronomy.LunarCoordinates import LunarCoordinates
from alfalak.exceptions import (
    AlFalakError,
    AstronomicalError,
    ConfigurationError,
    ValidationError,
)
from alfalak.calculation import (
    CalculationMethod,
    CalculationParameters,
    HighLatitudeRule,
    Madhab,
    PolarCircleRule,
    PrayerAdjustments,
)
from alfalak.data import Coordinates, NightPortions, Prayer, ShadowLength
from alfalak.PrayerTimes import PrayerTimes
from alfalak.util.DateComponents import DateComponents


def test_root_exports_match_all():
    assert getattr(alfalak, "__all__") == [
        "AlFalakError",
        "AstronomicalError",
        "ConfigurationError",
        "ValidationError",
        "PrayerTimes",
        "Qibla",
        "SunnahTimes",
        "CalculationMethod",
        "CalculationParameters",
        "HighLatitudeRule",
        "Madhab",
        "PolarCircleRule",
        "PrayerAdjustments",
        "Coordinates",
        "Prayer",
        "LunarCoordinates",
        "CrescentGeometry",
        "crescent_geometry_at_sunset",
        "delta_t",
    ]
    assert {
        "AlFalakError": AlFalakError,
        "AstronomicalError": AstronomicalError,
        "ConfigurationError": ConfigurationError,
        "ValidationError": ValidationError,
        "PrayerTimes": PrayerTimes,
        "Qibla": Qibla,
        "SunnahTimes": SunnahTimes,
        "CalculationMethod": CalculationMethod,
        "CalculationParameters": CalculationParameters,
        "HighLatitudeRule": HighLatitudeRule,
        "Madhab": Madhab,
        "PolarCircleRule": PolarCircleRule,
        "PrayerAdjustments": PrayerAdjustments,
        "Coordinates": Coordinates,
        "Prayer": Prayer,
        "LunarCoordinates": LunarCoordinates,
        "CrescentGeometry": CrescentGeometry,
        "crescent_geometry_at_sunset": crescent_geometry_at_sunset,
        "delta_t": delta_t,
    } == {name: getattr(alfalak, name) for name in alfalak.__all__}
    assert alfalak.PrayerTimes is RootPrayerTimes


def test_subpackage_exports():
    from alfalak import calculation, data

    assert {
        "CalculationMethod": CalculationMethod,
        "CalculationParameters": CalculationParameters,
        "HighLatitudeRule": HighLatitudeRule,
        "Madhab": Madhab,
        "PolarCircleRule": PolarCircleRule,
        "PrayerAdjustments": PrayerAdjustments,
    } == {name: getattr(calculation, name) for name in calculation.__all__}
    assert {
        "Coordinates": Coordinates,
        "NightPortions": NightPortions,
        "Prayer": Prayer,
        "ShadowLength": ShadowLength,
    } == {name: getattr(data, name) for name in data.__all__}


def test_time_for_prayer_matches_attributes():
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.NORTH_AMERICA
        ),
    )

    assert prayer_times.time_for_prayer(Prayer.IMSAK) == prayer_times.imsak
    assert prayer_times.time_for_prayer(Prayer.FAJR) == prayer_times.fajr
    assert prayer_times.time_for_prayer(Prayer.SUNRISE) == prayer_times.sunrise
    assert prayer_times.time_for_prayer(Prayer.SYURUK) == prayer_times.syuruk
    assert prayer_times.time_for_prayer(Prayer.ISHRAQ) == prayer_times.ishraq
    assert prayer_times.time_for_prayer(Prayer.DHUHA) == prayer_times.dhuha
    assert prayer_times.time_for_prayer(Prayer.DHUHR) == prayer_times.dhuhr
    assert prayer_times.time_for_prayer(Prayer.ASR) == prayer_times.asr
    assert prayer_times.time_for_prayer(Prayer.MAGHRIB) == prayer_times.maghrib
    assert prayer_times.time_for_prayer(Prayer.ISHA) == prayer_times.isha


def test_time_for_prayer_rejects_none():
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.NORTH_AMERICA
        ),
    )

    with pytest.raises(ConfigurationError, match="(?i)prayer"):
        prayer_times.time_for_prayer(Prayer.NONE)


def test_prayer_definition_order_is_chronological_and_values_frozen():
    # Definition (iteration) order is the canonical chronological order.
    # Numeric values are frozen: FAJR=1..ISHA=6 predate the newer markers,
    # so never sort by .value for chronology — iterate the enum instead.
    assert [prayer.name for prayer in Prayer] == [
        "NONE",
        "IMSAK",
        "FAJR",
        "SUNRISE",
        "SYURUK",
        "ISHRAQ",
        "DHUHA",
        "DHUHR",
        "ASR",
        "MAGHRIB",
        "ISHA",
    ]
    assert {
        "NONE": 0,
        "FAJR": 1,
        "SUNRISE": 2,
        "DHUHR": 3,
        "ASR": 4,
        "MAGHRIB": 5,
        "ISHA": 6,
        "IMSAK": 7,
        "SYURUK": 8,
        "ISHRAQ": 9,
        "DHUHA": 10,
    } == {prayer.name: prayer.value for prayer in Prayer}


def test_docs_cover_public_api():
    # docs/user/api-reference.md must name every public export or the
    # reference rots; word boundaries so Prayer is not satisfied by
    # PrayerTimes
    import re
    from pathlib import Path

    api_docs = (
        Path(__file__).resolve().parent.parent / "docs" / "user" / "api-reference.md"
    ).read_text(encoding="utf-8")

    for name in alfalak.__all__:
        assert re.search(rf"\b{name}\b", api_docs), name
    for name in ("time_for_prayer", "Qibla", "SunnahTimes"):
        assert re.search(rf"\b{name}\b", api_docs), name
