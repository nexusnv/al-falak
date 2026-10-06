import pytest
from decimal import Decimal
from alfalak import PrayerTimes, Qibla
from alfalak.calculation import CalculationMethod, CalculationParameters
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import (
    AlFalakError,
    ConfigurationError,
    ValidationError,
)
from alfalak.util.DateComponents import DateComponents


@pytest.mark.parametrize(
    "latitude, longitude", [(90, 0), (-90, 0), (0, 180), (0, -180), (35.77, -78.63)]
)
def test_boundary_coordinates_accepted(latitude, longitude):
    assert Coordinates(latitude, longitude).latitude == latitude


@pytest.mark.parametrize(
    "latitude, longitude",
    [(90.1, 0), (-90.1, 0), (0, 180.1), (0, -180.1), (200, 400)],
)
def test_out_of_range_coordinates_rejected(latitude, longitude):
    with pytest.raises(ValidationError, match="(?i)latitude|longitude"):
        Coordinates(latitude, longitude)


def test_out_of_range_tuple_rejected_by_prayer_times():
    with pytest.raises(ValidationError, match="(?i)latitude|longitude"):
        PrayerTimes(
            (91, 0),
            DateComponents(2015, 7, 12),
            CalculationMethod.MUSLIM_WORLD_LEAGUE,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fajr_angle": -1},
        {"fajr_angle": 91},
        {"isha_angle": -1},
        {"isha_angle": 91},
        {"isha_interval": -5},
    ],
)
def test_out_of_range_parameters_rejected(kwargs):
    with pytest.raises(ValidationError, match="(?i)angle|interval"):
        CalculationParameters(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fajr_angle": 0, "isha_angle": 0},
        {"fajr_angle": 90, "isha_angle": 90},
        {"isha_interval": 0},
        {"isha_interval": 90},
    ],
)
def test_boundary_parameters_accepted(kwargs):
    CalculationParameters(**kwargs)


@pytest.mark.parametrize(
    "latitude, longitude",
    [("a", "b"), (None, None), (float("nan"), "b"), (True, False)],
)
def test_non_numeric_coordinates_rejected(latitude, longitude):
    with pytest.raises(ValidationError, match="(?i)real number|latitude|longitude"):
        Coordinates(latitude, longitude)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"imsak_offset": -1},
        {"ishraq_offset": -1},
        {"dhuha_offset": -1},
        {"imsak_offset": True},
        {"ishraq_offset": True},
        {"dhuha_offset": True},
        {"imsak_offset": "10"},
        {"ishraq_offset": "15"},
        {"dhuha_offset": "28"},
        {"imsak_offset": 2.5},
        {"ishraq_offset": 15.0},
        {"isha_interval": True},
        {"isha_interval": "90"},
        {"isha_interval": 90.0},
    ],
)
def test_out_of_range_minute_offsets_rejected(kwargs):
    with pytest.raises(ValidationError, match="(?i)offset|interval"):
        CalculationParameters(**kwargs)


def test_inverted_ishraq_dhuha_offsets_rejected():
    with pytest.raises(ValidationError, match="(?i)dhuha|ishraq"):
        CalculationParameters(ishraq_offset=30, dhuha_offset=5)


@pytest.mark.parametrize("is_ramadan", ["yes", 1, 0, None, "true"])
def test_non_bool_is_ramadan_rejected(is_ramadan):
    with pytest.raises(ConfigurationError, match="(?i)is_ramadan"):
        CalculationParameters(is_ramadan=is_ramadan)


@pytest.mark.parametrize(
    "coordinates",
    [("a", "b"), (None, None), (35.7,), (), None, 35.7, (True, False)],
)
def test_malformed_coordinates_rejected_by_prayer_times(coordinates):
    with pytest.raises(ValidationError, match="(?i)coordinates|real number"):
        PrayerTimes(
            coordinates,
            DateComponents(2015, 7, 12),
            CalculationMethod.MUSLIM_WORLD_LEAGUE,
        )


def test_malformed_coordinates_rejected_by_qibla():
    with pytest.raises(ValidationError, match="(?i)coordinates|real number"):
        Qibla(("a", "b"))


def test_malformed_coordinates_are_alfalak_errors():
    try:
        PrayerTimes(
            ("a", "b"),
            DateComponents(2015, 7, 12),
            CalculationMethod.MUSLIM_WORLD_LEAGUE,
        )
    except AlFalakError:
        pass
    else:
        pytest.fail("expected AlFalakError")


def test_decimal_coordinates_normalized_to_float():
    # Coordinates accepts Decimal but downstream float arithmetic (Qibla,
    # SolarTime) cannot consume it; fields must be plain floats, never a
    # bare TypeError leaking through the AlFalakError contract.
    coords = Coordinates(Decimal("35.7750"), Decimal("-78.6336"))

    assert isinstance(coords.latitude, float)
    assert isinstance(coords.longitude, float)
    assert Qibla(
        (Decimal("35.7750"), Decimal("-78.6336"))
    ).direction == pytest.approx(Qibla((35.7750, -78.6336)).direction)


def test_coordinates_are_frozen():
    import dataclasses

    coords = Coordinates(35.7750, -78.6336)
    with pytest.raises(dataclasses.FrozenInstanceError):
        coords.latitude = 0.0  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        coords.longitude = 0.0  # type: ignore[misc]
    # Value unchanged after failed mutation attempts.
    assert (coords.latitude, coords.longitude) == (35.7750, -78.6336)


def test_makkah_singleton_cannot_be_mutated():
    import dataclasses

    from alfalak.data.Constants import MAKKAH

    with pytest.raises(dataclasses.FrozenInstanceError):
        MAKKAH.latitude = 0.0  # type: ignore[misc]
    assert MAKKAH.latitude == pytest.approx(21.4225241)
