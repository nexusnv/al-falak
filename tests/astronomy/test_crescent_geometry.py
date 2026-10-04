from datetime import date

import pytest

from alfalak.astronomy.CrescentGeometry import crescent_geometry_at_sunset
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AstronomicalError


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


def test_polar_night_without_sunset_raises() -> None:
    # Tromso 2025-01-01 is deep polar night: SolarTime reports NaN for
    # both sunrise and sunset (verified live), so crescent geometry at
    # sunset is undefined. (2025-01-15 already has a sunset again and
    # must NOT be used as the polar-night fixture.)
    with pytest.raises(AstronomicalError, match="(?i)no sunset|does not set"):
        crescent_geometry_at_sunset(date(2025, 1, 1), Coordinates(69.6492, 18.9553))
