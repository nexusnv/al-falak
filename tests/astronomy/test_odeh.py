from alfalak.astronomy.Odeh import odeh_class, odeh_v
from alfalak.exceptions import ValidationError

import pytest


def test_odeh_danjon_floor():
    assert odeh_class(10.0, arcl_deg=5.0) == "D"


def test_odeh_class_boundaries():
    assert odeh_class(6.0, 10.0) == "A"
    assert odeh_class(3.0, 10.0) == "B"
    assert odeh_class(0.0, 10.0) == "C"
    assert odeh_class(-2.0, 10.0) == "D"


def test_odeh_v_monotonic():
    assert odeh_v(8.0, 0.4) > odeh_v(3.0, 0.1)


def test_odeh_v_rejects_negative_width():
    with pytest.raises(ValidationError, match="(?i)non-negative|width"):
        odeh_v(5.0, -10.0)


def test_odeh_v_zero_width_accepted():
    # Zero clamps to a 1e-6 arcmin epsilon, so allow the ~6e-6 shift.
    assert odeh_v(5.0, 0.0) == pytest.approx(5.0 - 7.1651, abs=1e-4)


def test_odeh_rejects_float_overflowing_huge_int():
    # Huge ints overflow float(): must raise ValidationError, not OverflowError.
    with pytest.raises(ValidationError, match="(?i)finite"):
        odeh_v(10**1000, 0.5)
    with pytest.raises(ValidationError, match="(?i)finite"):
        odeh_v(5.0, 10**1000)
    with pytest.raises(ValidationError, match="(?i)finite"):
        odeh_class(10**1000, 10.0)
