from alfalak.astronomy.Yallop import yallop_q, yallop_zone
from alfalak.exceptions import ValidationError

import pytest


def test_yallop_zone_boundaries():
    assert yallop_zone(0.3) == "A"
    assert yallop_zone(0.216) == "B"
    assert yallop_zone(0.0) == "B"
    assert yallop_zone(-0.014) == "C"
    assert yallop_zone(-0.16) == "D"
    assert yallop_zone(-0.232) == "E"
    assert yallop_zone(-0.293) == "F"
    assert yallop_zone(-1.0) == "F"


def test_yallop_q_sign():
    assert yallop_q(10.0, 0.5) > yallop_q(2.0, 0.05)


def test_yallop_q_rejects_negative_width():
    with pytest.raises(ValidationError, match="(?i)non-negative|width"):
        yallop_q(5.0, -10.0)


def test_yallop_q_zero_width_accepted():
    # Zero clamps to a 1e-6 arcmin epsilon, so allow the ~6e-7 shift
    # after the /10 scaling of Yallop (1997) eq. 6.1.
    assert yallop_q(5.0, 0.0) == pytest.approx((5.0 - 11.8371) / 10.0, abs=1e-4)


def test_yallop_q_scale_matches_zone_thresholds():
    # Yallop (1997) eq. 6.1: q is scaled by 1/10 to sit roughly in
    # [-1, 1] where the A-F zone boundaries (+0.216 .. -0.293) live.
    # Without the scaling every evening crescent would collapse to A/F.
    assert yallop_q(10.0, 0.5) == pytest.approx(
        (10.0 - (-0.1018 * 0.5**3 + 0.7319 * 0.5**2 - 6.3226 * 0.5 + 11.8371))
        / 10.0,
        rel=1e-12,
    )
