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
    # Zero clamps to a 1e-6 arcmin epsilon, so allow the ~6e-6 shift.
    assert yallop_q(5.0, 0.0) == pytest.approx(5.0 - 11.8371, abs=1e-4)
