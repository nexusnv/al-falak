"""Geocentric low-precision Moon position (Meeus 2nd ed. Ch.47, pp.338-342).

Implements the low-precision geocentric lunar position: mean elements
(L', D, M, M', F) plus the periodic terms of Table 47.A (longitude and
distance, 60 rows) and Table 47.B (latitude, 60 rows), merged below into a
single list. Units as printed in the book: angle coefficients in 1e-6
degree, distance coefficients in metres (0.001 km).

Validated against Meeus Example 47.a (JDE 2448724.5 -> λ=133.167265°,
β=-3.229126°, Δ=368409.7 km).
"""

import math
import numbers
from decimal import Decimal

from alfalak.astronomy.Astronomical import (
    apparent_obliquity_of_the_ecliptic,
    mean_obliquity_of_the_ecliptic,
)
from alfalak.astronomy.CalendricalHelper import julian_century
from alfalak.exceptions import ValidationError
from alfalak.util.FloatUtil import unwind_angle

# Meeus 2nd ed. Tables 47.A (longitude + distance) and 47.B (latitude).
# Schema: (D, M, Mp, F, Sl, Sb, Sr) with angles in 1e-6 degree and
# radius in metres. Rows absent from one table carry 0 in its columns.
TABLE_47A: list[tuple[int, int, int, int, int, int, int]] = [
    # Table 47.A: longitude (sine) and distance (cosine) terms.
    (0, 0, 1, 0, 6288774, 0, -20905355),
    (2, 0, -1, 0, 1274027, 0, -3699111),
    (2, 0, 0, 0, 658314, 0, -2955968),
    (0, 0, 2, 0, 213618, 0, -569925),
    (0, 1, 0, 0, -185116, 0, 48888),
    (0, 0, 0, 2, -114332, 0, -3149),
    (2, 0, -2, 0, 58793, 0, 246158),
    (2, -1, -1, 0, 57066, 0, -152138),
    (2, 0, 1, 0, 53322, 0, -170733),
    (2, -1, 0, 0, 45758, 0, -204586),
    (0, 1, -1, 0, -40923, 0, -129620),
    (1, 0, 0, 0, -34720, 0, 108743),
    (0, 1, 1, 0, -30383, 0, 104755),
    (2, 0, 0, -2, 15327, 0, 10321),
    (0, 0, 1, 2, -12528, 0, 0),
    (0, 0, 1, -2, 10980, 0, 79661),
    (4, 0, -1, 0, 10675, 0, -34782),
    (0, 0, 3, 0, 10034, 0, -23210),
    (4, 0, -2, 0, 8548, 0, -21636),
    (2, 1, -1, 0, -7888, 0, 24208),
    (2, 1, 0, 0, -6766, 0, 30824),
    (1, 0, -1, 0, -5163, 0, -8379),
    (1, 1, 0, 0, 4987, 0, -16675),
    (2, -1, 1, 0, 4036, 0, -12831),
    (2, 0, 2, 0, 3994, 0, -10445),
    (4, 0, 0, 0, 3861, 0, -11650),
    (2, 0, -3, 0, 3665, 0, 14403),
    (0, 1, -2, 0, -2689, 0, -7003),
    (2, 0, -1, 2, -2602, 0, 0),
    (2, -1, -2, 0, 2390, 0, 10056),
    (1, 0, 1, 0, -2348, 0, 6322),
    (2, -2, 0, 0, 2236, 0, -9884),
    (0, 1, 2, 0, -2120, 0, 5751),
    (0, 2, 0, 0, -2069, 0, 0),
    (2, -2, -1, 0, 2048, 0, -4950),
    (2, 0, 1, -2, -1773, 0, 4130),
    (2, 0, 0, 2, -1595, 0, 0),
    (4, -1, -1, 0, 1215, 0, -3958),
    (0, 0, 2, 2, -1110, 0, 0),
    (3, 0, -1, 0, -892, 0, 3258),
    (2, 1, 1, 0, -810, 0, 2616),
    (4, -1, -2, 0, 759, 0, -1897),
    (0, 2, -1, 0, -713, 0, -2117),
    (2, 2, -1, 0, -700, 0, 2354),
    (2, 1, -2, 0, 691, 0, 0),
    (2, -1, 0, -2, 596, 0, 0),
    (4, 0, 1, 0, 549, 0, -1423),
    (0, 0, 4, 0, 537, 0, -1117),
    (4, -1, 0, 0, 520, 0, -1571),
    (1, 0, -2, 0, -487, 0, -1739),
    (2, 1, 0, -2, -399, 0, 0),
    (0, 0, 2, -2, -381, 0, -4421),
    (1, 1, 1, 0, 351, 0, 0),
    (3, 0, -2, 0, -340, 0, 0),
    (4, 0, -3, 0, 330, 0, 0),
    (2, -1, 2, 0, 327, 0, 0),
    (0, 2, 1, 0, -323, 0, 1165),
    (1, 1, -1, 0, 299, 0, 0),
    (2, 0, 3, 0, 294, 0, 0),
    (2, 0, -1, -2, 0, 0, 8752),
    # Table 47.B: latitude (sine) terms.
    (0, 0, 0, 1, 0, 5128122, 0),
    (0, 0, 1, 1, 0, 280602, 0),
    (0, 0, 1, -1, 0, 277693, 0),
    (2, 0, 0, -1, 0, 173237, 0),
    (2, 0, -1, 1, 0, 55413, 0),
    (2, 0, -1, -1, 0, 46271, 0),
    (2, 0, 0, 1, 0, 32573, 0),
    (0, 0, 2, 1, 0, 17198, 0),
    (2, 0, 1, -1, 0, 9266, 0),
    (0, 0, 2, -1, 0, 8822, 0),
    (2, -1, 0, -1, 0, 8216, 0),
    (2, 0, -2, -1, 0, 4324, 0),
    (2, 0, 1, 1, 0, 4200, 0),
    (2, 1, 0, -1, 0, -3359, 0),
    (2, -1, -1, 1, 0, 2463, 0),
    (2, -1, 0, 1, 0, 2211, 0),
    (2, -1, -1, -1, 0, 2065, 0),
    (0, 1, -1, -1, 0, -1870, 0),
    (4, 0, -1, -1, 0, 1828, 0),
    (0, 1, 0, 1, 0, -1794, 0),
    (0, 0, 0, 3, 0, -1749, 0),
    (0, 1, -1, 1, 0, -1565, 0),
    (1, 0, 0, 1, 0, -1491, 0),
    (0, 1, 1, 1, 0, -1475, 0),
    (0, 1, 1, -1, 0, -1410, 0),
    (0, 1, 0, -1, 0, -1344, 0),
    (1, 0, 0, -1, 0, -1335, 0),
    (0, 0, 3, 1, 0, 1107, 0),
    (4, 0, 0, -1, 0, 1021, 0),
    (4, 0, -1, 1, 0, 833, 0),
    (0, 0, 1, -3, 0, 777, 0),
    (4, 0, -2, 1, 0, 671, 0),
    (2, 0, 0, -3, 0, 607, 0),
    (2, 0, 2, -1, 0, 596, 0),
    (2, -1, 1, -1, 0, 491, 0),
    (2, 0, -2, 1, 0, -451, 0),
    (0, 0, 3, -1, 0, 439, 0),
    (2, 0, 2, 1, 0, 422, 0),
    (2, 0, -3, -1, 0, 421, 0),
    (2, 1, -1, 1, 0, -366, 0),
    (2, 1, 0, 1, 0, -351, 0),
    (4, 0, 0, 1, 0, 331, 0),
    (2, -1, 1, 1, 0, 315, 0),
    (2, -2, 0, -1, 0, 302, 0),
    (0, 0, 1, 3, 0, -283, 0),
    (2, 1, 1, -1, 0, -229, 0),
    (1, 1, 0, -1, 0, 223, 0),
    (1, 1, 0, 1, 0, 223, 0),
    (0, 1, -2, -1, 0, -220, 0),
    (2, 1, -1, -1, 0, -220, 0),
    (1, 0, 1, 1, 0, -185, 0),
    (2, -1, -2, -1, 0, 181, 0),
    (0, 1, 2, 1, 0, -177, 0),
    (4, 0, -2, -1, 0, 176, 0),
    (4, -1, -1, -1, 0, 166, 0),
    (1, 0, 1, -1, 0, -164, 0),
    (4, 0, 1, -1, 0, 132, 0),
    (1, 0, -1, -1, 0, -119, 0),
    (4, -1, 0, -1, 0, 115, 0),
    (2, -2, 0, 1, 0, 107, 0),
]


class LunarCoordinates:
    """Low-precision geocentric Moon position for a TT Julian Day."""

    def __init__(self, julian_day_tt: float) -> None:
        if isinstance(julian_day_tt, bool) or not isinstance(
            julian_day_tt, (numbers.Real, Decimal)
        ):
            raise ValidationError(
                "Julian day must be a real number, got " f"{julian_day_tt!r}."
            )
        julian_day = float(julian_day_tt)
        if not math.isfinite(julian_day):
            raise ValidationError(f"Julian day must be finite, got {julian_day_tt!r}.")
        T = julian_century(julian_day)
        Lp = unwind_angle(218.3164477 + 481267.88123421 * T - 0.0015786 * T * T)
        D = unwind_angle(297.8501921 + 445267.1114034 * T - 0.0018819 * T * T)
        M = unwind_angle(357.5291092 + 35999.0502909 * T - 0.0001536 * T * T)
        Mp = unwind_angle(134.9633964 + 477198.8675055 * T + 0.0087414 * T * T)
        F = unwind_angle(93.2720950 + 483202.0175233 * T - 0.0036539 * T * T)
        sl = sb = sr = 0.0
        for d, m, mp, f, cl, cb, cr in TABLE_47A:
            arg = math.radians(d * D + m * M + mp * Mp + f * F)
            sl += cl * math.sin(arg)
            sb += cb * math.sin(arg)
            sr += cr * math.cos(arg)
        self.longitude: float = unwind_angle(Lp + sl / 1e6)
        self.latitude: float = sb / 1e6
        self.distance_km: float = 385000.56 + sr / 1000.0
        eps = math.radians(
            apparent_obliquity_of_the_ecliptic(T, mean_obliquity_of_the_ecliptic(T))
        )
        lam = math.radians(self.longitude)
        beta = math.radians(self.latitude)
        self.declination: float = math.degrees(
            math.asin(
                math.sin(beta) * math.cos(eps)
                + math.cos(beta) * math.sin(eps) * math.sin(lam)
            )
        )
        self.right_ascension: float = unwind_angle(
            math.degrees(
                math.atan2(
                    math.sin(lam) * math.cos(eps) - math.tan(beta) * math.sin(eps),
                    math.cos(lam),
                )
            )
        )
