import math

import pytest
from alfalak import Qibla
from alfalak.data.Constants import EARTH_MEAN_RADIUS_KM
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import ConfigurationError, ValidationError
from alfalak.Qibla import MAKKAH


@pytest.mark.parametrize(
    "latitude, longitude, expected",
    [
        (35.7750, -78.6336, 55.825),  # Raleigh, US
        (40.7128, -74.0060, 58.482),  # New York, US
        (51.5074, -0.1278, 118.987),  # London, UK
        (30.0444, 31.2357, 136.137),  # Cairo, EG
        (3.1390, 101.6869, 292.538),  # Kuala Lumpur, MY
        (-6.2088, 106.8456, 295.152),  # Jakarta, ID
        (-33.8688, 151.2093, 277.500),  # Sydney, AU
    ],
)
def test_qibla_direction(latitude, longitude, expected):
    # formula ported from upstream adhan (adhan-kotlin QiblaUtil);
    # cross-checked against published qibla bearings and WGS84 geodesics
    assert Qibla((latitude, longitude)).direction == pytest.approx(expected, abs=1e-2)


def test_qibla_accepts_coordinates_object():
    assert Qibla(Coordinates(35.7750, -78.6336)).direction == pytest.approx(
        Qibla((35.7750, -78.6336)).direction
    )


def test_qibla_direction_in_range():
    for latitude, longitude in [(35.7750, -78.6336), (-33.8688, 151.2093)]:
        assert 0 <= Qibla((latitude, longitude)).direction < 360


@pytest.mark.parametrize("coordinates", [None, 35.7, (), (35.7,)])
def test_qibla_malformed_coordinates_rejected(coordinates):
    with pytest.raises(ValidationError, match="(?i)coordinates|real number"):
        Qibla(coordinates)


def test_qibla_makkah_self_bearing_no_raise():
    direction = Qibla((MAKKAH.latitude, MAKKAH.longitude)).direction
    assert 0 <= direction < 360
    assert not math.isnan(direction)


# Exact antipode of the stored Makkah coordinate (derived, not literal, so a
# future re-canonicalization of MAKKAH keeps testing the true antipode).
ANTIPODE_OF_MAKKAH = (-MAKKAH.latitude, MAKKAH.longitude - 180)


def test_qibla_true_antipode_bearing_no_raise():
    direction = Qibla(ANTIPODE_OF_MAKKAH).direction
    assert 0 <= direction < 360
    assert not math.isnan(direction)


@pytest.mark.parametrize(
    "latitude, longitude, expected",
    [
        (35.7750, -78.6336, 10944),  # Raleigh, US
        (40.7128, -74.0060, 10306),  # New York, US
        (3.1390, 101.6869, 6974),  # Kuala Lumpur, MY
        (-33.8688, 151.2093, 13236),  # Sydney, AU
    ],
)
def test_qibla_distance_to_makkah_km(latitude, longitude, expected):
    # Spherical great-circle with R = 6371.0088 km, cross-checked via an
    # independent vector dot-product computation (agreement <0.02 km);
    # +/-10 km documents the radius-convention tolerance, not precision.
    assert Qibla((latitude, longitude)).distance_to_makkah_km == pytest.approx(
        expected, abs=10.0
    )


def test_qibla_distance_self_is_zero():
    assert Qibla(
        (MAKKAH.latitude, MAKKAH.longitude)
    ).distance_to_makkah_km == pytest.approx(0.0, abs=1e-6)


def test_qibla_distance_antipode_near_half_circumference():
    distance = Qibla(ANTIPODE_OF_MAKKAH).distance_to_makkah_km
    assert distance == pytest.approx(math.pi * EARTH_MEAN_RADIUS_KM, abs=1.0)
    assert not math.isnan(distance)


def test_qibla_default_method_is_spherical():
    qibla = Qibla((35.7750, -78.6336))
    assert qibla.method == "spherical"
    assert qibla.direction == pytest.approx(55.825, abs=1e-2)


@pytest.mark.parametrize(
    "latitude, longitude, expected_direction, expected_distance",
    [
        # Ellipsoidal goldens: GeographicLib 2.1, generated 2026-10-03.
        (35.7750, -78.6336, 55.739246718, 10961.845992),
        (3.1390, 101.6869, 292.442376339, 6979.153497),
        (-33.8688, 151.2093, 277.318844347, 13236.950907),
    ],
)
def test_qibla_ellipsoidal_opt_in(
    latitude, longitude, expected_direction, expected_distance
):
    qibla = Qibla((latitude, longitude), method="ellipsoidal")
    assert qibla.method == "ellipsoidal"
    assert qibla.direction == pytest.approx(expected_direction, abs=1e-6)
    assert qibla.distance_to_makkah_km == pytest.approx(expected_distance, abs=1e-3)


def test_qibla_ellipsoidal_self_and_antipode_no_raise():
    sel = Qibla((MAKKAH.latitude, MAKKAH.longitude), method="ellipsoidal")
    assert 0 <= sel.direction < 360
    assert sel.distance_to_makkah_km == pytest.approx(0.0, abs=1e-9)
    anti = Qibla(ANTIPODE_OF_MAKKAH, method="ellipsoidal")
    assert 0 <= anti.direction < 360
    assert not math.isnan(anti.direction)
    assert not math.isnan(anti.distance_to_makkah_km)


def test_qibla_self_both_models_return_180():
    # Degenerate self point: both models return 180.0 by construction
    # (spherical atan2(0, ~0) and the ellipsoidal meridian path); any
    # bearing is equally valid there, contract is float in [0, 360).
    for method in ("spherical", "ellipsoidal"):
        direction = Qibla(
            (MAKKAH.latitude, MAKKAH.longitude), method=method
        ).direction
        assert direction == pytest.approx(180.0, abs=1e-6)
        assert 0 <= direction < 360


def test_qibla_ellipsoidal_stays_within_documented_bound_of_spherical():
    for latitude, longitude in [
        (35.7750, -78.6336),
        (40.7128, -74.0060),
        (51.5074, -0.1278),
        (30.0444, 31.2357),
        (3.1390, 101.6869),
        (-6.2088, 106.8456),
        (-33.8688, 151.2093),
    ]:
        spherical = Qibla((latitude, longitude)).direction
        ellipsoidal = Qibla((latitude, longitude), method="ellipsoidal").direction
        delta = abs((ellipsoidal - spherical + 180) % 360 - 180)
        assert delta < 0.35


def test_qibla_unknown_method_rejected():
    with pytest.raises(ConfigurationError, match="(?i)method"):
        Qibla((35.7750, -78.6336), method="bogus")


def test_qibla_magnetic_east_declination_subtracts():
    # NOAA sign convention: east positive ("east is least").
    qibla = Qibla((51.5074, -0.1278))  # London, true 118.987
    assert qibla.magnetic_direction(3.0) == pytest.approx(115.987, abs=1e-2)


def test_qibla_magnetic_west_declination_adds():
    # West is passed negative; Raleigh true 55.825, synthetic -8.0
    # (west-negative convention check, not a Raleigh model lookup).
    qibla = Qibla((35.7750, -78.6336))
    assert qibla.magnetic_direction(-8.0) == pytest.approx(63.825, abs=1e-2)


def test_qibla_magnetic_zero_declination_is_identity():
    qibla = Qibla((35.7750, -78.6336))
    assert qibla.magnetic_direction(0.0) == pytest.approx(qibla.direction, abs=1e-9)


def test_qibla_magnetic_wraps_into_range():
    qibla = Qibla((51.5074, -0.1278))  # true 118.987
    assert qibla.magnetic_direction(120.0) == pytest.approx(358.987, abs=1e-2)
    assert qibla.magnetic_direction(-240.0) == pytest.approx(358.987, abs=1e-2)


def test_qibla_magnetic_follows_ellipsoidal_direction():
    qibla = Qibla((35.7750, -78.6336), method="ellipsoidal")
    assert qibla.magnetic_direction(-8.0) == pytest.approx(63.739246718, abs=1e-6)


def test_qibla_magnetic_accepts_int_and_decimal():
    from decimal import Decimal
    from fractions import Fraction

    qibla = Qibla((35.7750, -78.6336))  # true 55.825
    assert qibla.magnetic_direction(8) == pytest.approx(47.825, abs=1e-2)
    assert qibla.magnetic_direction(Decimal("12.5")) == pytest.approx(43.325, abs=1e-2)
    assert qibla.magnetic_direction(Fraction(1, 2)) == pytest.approx(55.325, abs=1e-2)


def test_qibla_magnetic_huge_finite_stays_in_range():
    # unwind_angle's floor form cancels catastrophically past ~1e290;
    # the fmod reduction must keep every finite input in [0, 360).
    qibla = Qibla((35.7750, -78.6336))
    for declination in (9.99e305, -9.99e305, 1.5e308, -1.5e308, 7.77e307):
        result = qibla.magnetic_direction(declination)
        assert 0 <= result < 360
        assert not math.isnan(result)


@pytest.mark.parametrize(
    "declination",
    [None, "10", True, False, float("nan"), float("inf"), -float("inf"), 10**1000],
    ids=["none", "string", "bool", "false-bool", "nan", "inf", "neg-inf", "huge-int"],
)
def test_qibla_magnetic_rejects_bad_declination(declination):
    with pytest.raises(ValidationError, match="(?i)declination|finite|real"):
        Qibla((35.7750, -78.6336)).magnetic_direction(declination)
