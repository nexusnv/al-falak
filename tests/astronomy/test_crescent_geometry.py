from datetime import date, datetime

import math

import pytest

from alfalak.astronomy.CrescentGeometry import (
    _moon_age_days,
    crescent_geometry_at_sunset,
)
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AstronomicalError, ValidationError


def test_kuala_lumpur_geometry_sane() -> None:
    geometry = crescent_geometry_at_sunset(
        date(2025, 2, 28), Coordinates(3.1390, 101.6869)
    )
    assert -5 < geometry.arcv_topo_deg < 15
    assert 0 <= geometry.arcl_deg < 20
    assert 0 <= geometry.illumination <= 1
    assert geometry.moon_age_days > 0
    assert geometry.used_delta_t_s == pytest.approx(74.77, abs=1.0)


def test_field_names_distinguish_frames() -> None:
    geometry = crescent_geometry_at_sunset(
        date(2025, 2, 28), Coordinates(3.1390, 101.6869)
    )
    assert isinstance(geometry.arcv_geo_deg, float)
    assert isinstance(geometry.arcv_topo_deg, float)


def test_altitude_fields_consistent_with_arcv() -> None:
    # ARCV is the Moon-minus-Sun altitude difference, so the stored
    # altitudes must reconstruct it exactly (no -0.833 deg proxy).
    geometry = crescent_geometry_at_sunset(
        date(2025, 2, 28), Coordinates(3.1390, 101.6869)
    )
    assert geometry.moon_alt_topo_deg - geometry.sun_alt_deg == pytest.approx(
        geometry.arcv_topo_deg, rel=1e-12
    )
    # Sun sits near (not exactly at) the -0.833 deg sunset depression:
    # the ephemeris runs at TT while sunset is defined at UTC.
    assert geometry.sun_alt_deg == pytest.approx(-50.0 / 60.0, abs=0.5)


def test_polar_night_without_sunset_raises() -> None:
    # Tromso 2025-01-01 is deep polar night: SolarTime reports NaN for
    # both sunrise and sunset (verified live), so crescent geometry at
    # sunset is undefined. (2025-01-15 already has a sunset again and
    # must NOT be used as the polar-night fixture.)
    with pytest.raises(AstronomicalError, match="(?i)no sunset|does not set"):
        crescent_geometry_at_sunset(date(2025, 1, 1), Coordinates(69.6492, 18.9553))


def test_moon_age_full_moon_spans_half_lunation() -> None:
    # 2025-03-14 is near full moon (ARCL ~178 deg): the previous
    # conjunction is ~half a synodic month back, not inside a 2-day
    # window. Guards the youngest-minimum search against a 2-day cap.
    geometry = crescent_geometry_at_sunset(
        date(2025, 3, 14), Coordinates(3.1390, 101.6869)
    )
    assert 10.0 < geometry.moon_age_days < 20.0


def test_moon_age_crescent_stays_young() -> None:
    # Ramadan-eve crescent over KL: conjunction the same morning, so
    # the youngest minimum is hours — not a lunation — back.
    geometry = crescent_geometry_at_sunset(
        date(2025, 2, 28), Coordinates(3.1390, 101.6869)
    )
    assert 0.1 <= geometry.moon_age_days < 2.0


def test_moon_age_eclipse_day_hits_floor() -> None:
    # Solar-eclipse new moon (2025-03-29): conjunction falls between
    # sunset and the first hourly sample, so the age reports the
    # 0.1-day floor rather than the previous lunation.
    geometry = crescent_geometry_at_sunset(
        date(2025, 3, 29), Coordinates(3.1390, 101.6869)
    )
    assert geometry.moon_age_days == pytest.approx(0.1)


def test_lag_negative_when_moon_sets_first() -> None:
    # Eclipse evening over KL: the Moon sets ~3 minutes before the Sun
    # (no evening visibility window). Must stay negative and not be
    # clamped to 0.0, which means "no moonset" below.
    geometry = crescent_geometry_at_sunset(
        date(2025, 3, 29), Coordinates(3.1390, 101.6869)
    )
    assert geometry.lag_hours < 0.0
    assert geometry.lag_hours == pytest.approx(-0.044, abs=0.05)


def test_lag_nan_when_moon_never_sets() -> None:
    # Tromso 2025-01-15 has a sunset but a circumpolar Moon (no
    # moonset that civil date): lag is NaN, distinct from any number.
    geometry = crescent_geometry_at_sunset(
        date(2025, 1, 15), Coordinates(69.6492, 18.9553)
    )
    assert math.isnan(geometry.lag_hours)


@pytest.mark.parametrize("bad_day", ["2025-02-28", None, 20250228])
def test_bad_day_rejected(bad_day: object) -> None:
    with pytest.raises(ValidationError, match="(?i)date"):
        crescent_geometry_at_sunset(bad_day, Coordinates(3.1390, 101.6869))  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_coords", [None, "3.1,101.6", (3.1390, 101.6869)])
def test_bad_coordinates_rejected(bad_coords: object) -> None:
    with pytest.raises(ValidationError, match="(?i)coordinates"):
        crescent_geometry_at_sunset(date(2025, 2, 28), bad_coords)  # type: ignore[arg-type]


def test_moon_age_conjunction_at_edge_reports_floor() -> None:
    # JD 2460763.951356 is the minute-scan minimum of geocentric ARCL at
    # the March 2025 conjunction (solar eclipse 2025-03-29): querying the
    # age exactly at the minimum must report the 0.1-day floor, not the
    # previous lunation (~29.4d) the interior-only search used to return.
    assert _moon_age_days(2460763.951356) == pytest.approx(0.1)


def test_moon_age_pre_conjunction_still_finds_older_minimum() -> None:
    # One day before that conjunction the Moon is waning toward a future
    # new moon: the forward-slope guard must NOT claim the floor, and the
    # search must still return the previous lunation's minimum.
    assert _moon_age_days(2460763.951356 - 1.0) == pytest.approx(
        28.416666666666927, rel=1e-6
    )


def test_datetime_uses_calendar_date() -> None:
    # A datetime is a date subclass: accepted, time component ignored.
    by_date = crescent_geometry_at_sunset(
        date(2025, 2, 28), Coordinates(3.1390, 101.6869)
    )
    by_datetime = crescent_geometry_at_sunset(
        datetime(2025, 2, 28, 23, 30), Coordinates(3.1390, 101.6869)
    )
    assert by_datetime == by_date
