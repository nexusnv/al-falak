import pytest
from alfalak.astronomy.LunarCoordinates import LunarCoordinates


def test_meeus_example_47a():
    # Meeus 2nd ed. Ex.47.a: JDE 2448724.5 (= 1992-04-12 0h TT)
    moon = LunarCoordinates(2448724.5)
    assert moon.longitude == pytest.approx(133.167265, abs=0.02)
    assert moon.latitude == pytest.approx(-3.229126, abs=0.02)
    assert moon.distance_km == pytest.approx(368409.7, abs=500.0)


def test_ra_dec_in_range():
    moon = LunarCoordinates(2448724.5)
    assert 0.0 <= moon.right_ascension < 360.0
    assert -90.0 <= moon.declination <= 90.0
