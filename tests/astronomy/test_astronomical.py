"""Astronomical-algorithm goldens.

Two-tier accuracy policy for the independent-reference goldens (spec §3.3):

- **Transit / equation-of-time full-chain**: ±10 s. The transit case is a
  chain-consistency lock derived from published Meeus examples (Ex.25.a α and
  Ex.28.a E for 1992-10-13), not an independent physical truth; the EoT
  case keeps its existing ±10.2 s bar.
- **USNO rise/set**: ±60 s, matching the resolution of the published one-day
  tables (see ``test_solar_time.py``).
- **Takwim / e-solat**: minute agreement plus a documented numeric
  administrative delta (JAKIM applies minute-level adjustments); see
  ``tests/test_prayer_times.py``.

Unchanged tighter bars that must not be weakened: Ex.25.a right ascension
``abs=1e-5`` deg and the equation-of-time ``abs=0.17`` min (±10.2 s) chain
golden.
"""

import math
import pytest
import alfalak.astronomy.Astronomical as Astronomical
import alfalak.util.FloatUtil as FloatUtil
import alfalak.astronomy.CalendricalHelper as CalendricalHelper
from alfalak.astronomy.SolarCoordinates import SolarCoordinates
from alfalak.astronomy.SolarTime import SolarTime
from alfalak.data.Coordinates import Coordinates
from alfalak.util.DateComponents import DateComponents


def test_solar_coordinates():

    # values from Astronomical Algorithms page 165
    jd = CalendricalHelper.julian_day(1992, 10, 13)
    solar = SolarCoordinates(jd)
    T = CalendricalHelper.julian_century(jd)

    L0 = Astronomical.mean_solar_longitude(T)
    ε0 = Astronomical.mean_obliquity_of_the_ecliptic(T)
    εapp = Astronomical.apparent_obliquity_of_the_ecliptic(T, ε0)
    M = Astronomical.mean_solar_anomaly(T)
    C = Astronomical.solar_equation_of_the_center(T, M)
    λ = Astronomical.apparent_solar_longitude(T, L0)
    δ = solar.declination
    α = FloatUtil.unwind_angle(solar.right_ascension)

    assert T == pytest.approx(-0.072183436, abs=1e-11)
    assert L0 == pytest.approx(201.80720, abs=1e-5)
    assert ε0 == pytest.approx(23.44023, abs=1e-5)
    assert εapp == pytest.approx(23.43999, abs=1e-5)
    assert M == pytest.approx(278.99397, abs=1e-5)
    assert C == pytest.approx(-1.89732, abs=1e-5)

    # lower accuracy than desired
    assert λ == pytest.approx(199.90895, abs=2e-5)
    assert δ == pytest.approx(-7.78507, abs=1e-5)
    assert α == pytest.approx(198.38083, abs=1e-5)

    # values from Astronomical Algorithms page 88
    jd = CalendricalHelper.julian_day(1987, 4, 10)
    solar = SolarCoordinates(jd)
    T = CalendricalHelper.julian_century(jd)

    θ0 = Astronomical.mean_sidereal_time(T)
    θapp = solar.apparent_sidereal_time
    Ω = Astronomical.ascending_lunar_node_longitude(T)
    ε0 = Astronomical.mean_obliquity_of_the_ecliptic(T)
    L0 = Astronomical.mean_solar_longitude(T)
    Lp = Astronomical.mean_lunar_longitude(T)
    ΔΨ = Astronomical.nutation_in_longitude(L0, Lp, Ω)
    Δε = Astronomical.nutation_in_obliquity(L0, Lp, Ω)
    ε = ε0 + Δε

    assert θ0 == pytest.approx(197.693195, abs=1e-6)
    assert θapp == pytest.approx(197.6922295833, abs=1e-4)

    # values from Astronomical Algorithms page 148
    assert Ω == pytest.approx(11.2531, abs=1e-4)
    assert ΔΨ == pytest.approx(-0.0010522, abs=1e-4)
    assert Δε == pytest.approx(0.0026230556, abs=1e-5)
    assert ε0 == pytest.approx(23.4409463889, abs=1e-6)
    assert ε == pytest.approx(23.4435694444, abs=1e-5)


def test_altitude_of_celestial_body():
    φ = 38 + (55 / 60.0) + (17.0 / 3600)
    δ = -6 - (43 / 60.0) - (11.61 / 3600)
    H = 64.352133
    h = Astronomical.altitude_of_celestial_body(φ, δ, H)
    assert h == pytest.approx(15.1249, abs=1e-4)


def test_transit_and_hour_angle():
    # alues from Astronomical Algorithms page 103
    longitude = -71.0833
    Θ = 177.74208
    α1 = 40.68021
    α2 = 41.73129
    α3 = 42.78204
    m0 = Astronomical.approximate_transit(longitude, Θ, α2)

    assert m0 == pytest.approx(0.81965, abs=1e-5)

    transit = Astronomical.corrected_transit(m0, longitude, Θ, α2, α1, α3) / 24

    assert transit == pytest.approx(0.81980, abs=1e-5)

    δ1 = 18.04761
    δ2 = 18.44092
    δ3 = 18.82742

    rise = (
        Astronomical.corrected_hour_angle(
            m0,
            -0.5667,
            Coordinates(42.3333, longitude),
            False,
            Θ,
            α2,
            α1,
            α3,
            δ2,
            δ1,
            δ3,
        )
        / 24
    )
    assert rise == pytest.approx(0.51766, abs=1e-5)


def test_interpolation():
    # values from Astronomical Algorithms page 25
    interpolated_value_1 = Astronomical.interpolate(
        0.877366, 0.884226, 0.870531, 4.35 / 24
    )
    interpolated_value_2 = Astronomical.interpolate(1, -1, 3, 0.6)

    assert interpolated_value_1 == pytest.approx(0.876125, abs=1e-6)
    assert interpolated_value_2 == pytest.approx(2.2, abs=1e-6)


def test_angle_interpolation():
    i1 = Astronomical.interpolate_angles(1, -1, 3, 0.6)
    assert i1 == pytest.approx(2.2, abs=1e-6)

    i2 = Astronomical.interpolate_angles(1, 359, 3, 0.6)
    assert i2 == pytest.approx(2.2, abs=1e-6)


def test_corrected_hour_angle_returns_nan_for_impossible_altitude():
    # an altitude the sun can never reach (e.g. polar night geometry)
    # must yield NaN so callers can fall back instead of crashing
    impossible = Astronomical.corrected_hour_angle(
        0.81965,
        -36,
        Coordinates(42.3333, -71.0833),
        True,
        177.74208,
        41.73129,
        40.68021,
        42.78204,
        18.44092,
        18.04761,
        18.82742,
    )

    assert math.isnan(impossible)


def test_solar_declination_wrapper():
    # Same Ex.25.a anchor as test_solar_coordinates (1992-10-13, p.165):
    # delta = -7d47'06" = -7.78507deg. Wrapper must equal SolarCoordinates.
    jd = CalendricalHelper.julian_day(1992, 10, 13)
    solar = SolarCoordinates(jd)

    assert Astronomical.solar_declination(jd) == pytest.approx(
        solar.declination, abs=1e-12
    )
    assert Astronomical.solar_declination(jd) == pytest.approx(-7.78507, abs=1e-5)


def test_equation_of_time_full_chain():
    # Meeus Ch.28 (p.183): E = L0 - 0.0057183 - alpha + Δψ·cos ε, in minutes.
    # Full-chain golden for 1992-10-13 (same anchor as Ex.25.a: L0 = 201.80720,
    # alpha = 198.38083): E ≈ +13.699 min, pinned here within ±10 s.
    jd = CalendricalHelper.julian_day(1992, 10, 13)

    assert Astronomical.equation_of_time(jd) == pytest.approx(13.699, abs=0.17)


def test_equation_of_time_curve_spots():
    # Coarse curve checks (±60 s): February minimum ~-14.2, November maximum
    # ~+16.4, near-zero crossings mid-April / mid-June / early September.
    spots = [
        ((2025, 2, 11), -14.2),
        ((2025, 11, 3), 16.4),
        ((2025, 4, 15), 0.0),
        ((2025, 6, 13), 0.0),
        ((2025, 9, 1), 0.0),
    ]
    for (year, month, day), expected in spots:
        jd = CalendricalHelper.julian_day(year, month, day)
        assert Astronomical.equation_of_time(jd) == pytest.approx(expected, abs=1.0)


def test_equation_of_time_agrees_with_transit():
    # Characterization: the Ch.28 direct EoT path and the Ch.15 interpolated
    # transit path agree. For Greenwich (lon 0): transit ≈ 12:00 − E/60.
    for year, month, day in [(1992, 10, 13), (2025, 2, 11), (2025, 11, 3)]:
        jd = CalendricalHelper.julian_day(year, month, day)
        eot_hours = Astronomical.equation_of_time(jd) / 60.0
        transit = SolarTime(
            DateComponents(year, month, day), Coordinates(51.5, 0.0)
        ).transit
        assert transit == pytest.approx(12.0 - eot_hours, abs=30 / 3600)


def test_greenwich_solar_transit_chain_consistency():
    # Chain-consistency lock (spec §3.3 fallback), NOT independent physical
    # truth: an independent Meeus Ch.15 hand-work needs the apparent sidereal
    # time Theta0 for 1992-10-13, which the cited examples do not publish, so
    # it would have to come from this repo (circular). Instead the expected
    # value is derived from published examples only:
    #   Meeus 2nd ed. Ex.25.a (p.165): apparent RA for 1992-10-13 (0h TD),
    #     alpha = 198.38083 deg = 13h13m31.4s;
    #   Meeus 2nd ed. Ex.28.a (p.183): E = +13m42s for the same date.
    # For the Sun at Greenwich, H = 0 gives transit = 12h - E:
    #   12:00:00 - 0:13:42 = 11:46:18 UT.
    # The independent transit truth is the USNO spot rows in test_solar_time.py;
    # this case locks the second-level chain. Expected value is not taken from
    # this repo's corrected_transit.
    transit = SolarTime(DateComponents(1992, 10, 13), Coordinates(51.4779, 0.0)).transit
    assert transit == pytest.approx(11 + 46 / 60 + 18 / 3600, abs=10 / 3600)
