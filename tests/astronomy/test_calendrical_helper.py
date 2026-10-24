import pytest
import alfalak.astronomy.CalendricalHelper as CalendricalHelper


@pytest.mark.parametrize(
    "year, month, day, expected",
    [
        (2010, 1, 2, 2455198.500000),
        (2011, 2, 4, 2455596.500000),
        (2012, 3, 6, 2455992.500000),
        (2013, 4, 8, 2456390.500000),
        (2014, 5, 10, 2456787.500000),
        (2015, 6, 12, 2457185.500000),
        (2016, 7, 14, 2457583.500000),
        (2017, 8, 16, 2457981.500000),
        (2018, 9, 18, 2458379.500000),
        (2019, 10, 20, 2458776.500000),
        (2020, 11, 22, 2459175.500000),
        (2021, 12, 24, 2459572.500000),
    ],
)
def test_julian_day(year, month, day, expected):
    # Comparison values generated from http://aa.usno.navy.mil/data/docs/JulianDate.php

    assert CalendricalHelper.julian_day(year, month, day) == pytest.approx(
        expected, abs=1e-5
    )


def test_julian_day_with_hours_and_minutes():
    # Comparison values generated from http://aa.usno.navy.mil/data/docs/JulianDate.php

    jdVal = 2457215.67708333
    assert CalendricalHelper.julian_day(2015, 7, 12, 4.25) == pytest.approx(
        jdVal, abs=1e-6
    )
    assert CalendricalHelper.julian_day(2015, 7, 12, 4, 15) == pytest.approx(
        jdVal, abs=1e-6
    )
    assert CalendricalHelper.julian_day(2015, 7, 12, 8.0) == pytest.approx(
        2457215.833333, abs=1e-6
    )
    assert CalendricalHelper.julian_day(1992, 10, 13, 0.0) == pytest.approx(
        2448908.5, abs=1e-6
    )


def test_julian_hours():
    j1 = CalendricalHelper.julian_day(2010, 1, 3)
    j2 = CalendricalHelper.julian_day(2010, 1, 1, 48)

    assert j1 == pytest.approx(j2, abs=1e-7)


def test_julian_day_j2000_anchor():
    # Slice 1.1 golden: Meeus, Astronomical Algorithms 2nd ed., Ch.7
    # (Example 7.a). J2000.0 is JD 2451545.0 TT = 2000-01-01 12:00 TT.
    assert CalendricalHelper.julian_day(2000, 1, 1, 12.0) == pytest.approx(
        2451545.0, abs=1e-9
    )
    assert CalendricalHelper.julian_century(2451545.0) == pytest.approx(0.0, abs=1e-12)


def test_julian_day_gregorian_only_reform_boundary():
    # Slice 1.1 documented limitation: no Julian-calendar branch (Meeus Ch.7
    # uses B = 0 for Julian dates; this implementation always applies the
    # Gregorian B = floor(2 - A + A/4)). The reform gap 1582-10-04 Julian ->
    # 1582-10-15 Gregorian is therefore computed as continuous proleptic
    # Gregorian (11 days, no 10-day jump). Correct for prayer use -- all
    # operational dates are centuries past the reform -- but asserted here
    # so the limitation is a decision, not a latent quirk.
    assert CalendricalHelper.julian_day(1582, 10, 15) - CalendricalHelper.julian_day(
        1582, 10, 4
    ) == pytest.approx(11.0)
    # Historical Julian-calendar JD of 1582-10-04 is 2299159.5; the
    # proleptic-Gregorian value differs by exactly the 10 omitted days.
    assert CalendricalHelper.julian_day(1582, 10, 4) == pytest.approx(
        2299159.5 - 10.0, abs=1e-9
    )
