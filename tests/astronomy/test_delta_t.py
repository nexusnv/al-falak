import math

import pytest

from alfalak.astronomy.DeltaT import delta_t
from alfalak.exceptions import ValidationError


def test_delta_t_polynomial_2025_matches_espenak():
    # Espenak 2005-2050 polynomial at 2025.5: 62.92+0.32217*25.5+0.005589*25.5**2 = 74.76958225.
    # Known ~5.6s high vs IERS observed ~69.2s (drift documented in DeltaT docstring);
    # callers needing observed values pass override= (recorded in geometry output).
    assert delta_t(2025.5) == pytest.approx(74.76958225, rel=1e-9)


def test_delta_t_override_covers_observed_band():
    assert delta_t(2025.5, override=69.184) == pytest.approx(69.184)


def test_delta_t_bad_input_rejected():
    with pytest.raises(ValidationError):
        delta_t(2025.5, override=math.nan)
    with pytest.raises(ValidationError):
        delta_t(math.inf)


def test_delta_t_year_validated_even_with_override():
    # The override replaces the polynomial, not the year validation:
    # a non-real year is caller error either way.
    with pytest.raises(ValidationError):
        delta_t("garbage", override=69.184)  # type: ignore[arg-type]


def test_delta_t_out_of_range_warns_but_returns_value():
    # Calibrated for 2005-2050; outside that the polynomial extrapolates.
    with pytest.warns(UserWarning, match="(?i)2005.*2050|extrapolat"):
        value = delta_t(1900.0)
    assert math.isfinite(value)
    with pytest.warns(UserWarning, match="(?i)2005.*2050|extrapolat"):
        delta_t(2100.0)
    # The override path never touches the polynomial, so no warning there.
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert delta_t(1900.0, override=69.184) == pytest.approx(69.184)


def test_delta_t_in_range_silent():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert delta_t(2025.5) == pytest.approx(74.76958225, rel=1e-9)
        assert delta_t(2005.0) is not None
        assert delta_t(2050.0) is not None


def test_delta_t_rejects_float_overflowing_huge_int():
    # Huge ints overflow float(): must raise ValidationError, not OverflowError.
    with pytest.raises(ValidationError, match="(?i)finite"):
        delta_t(10**1000)
    with pytest.raises(ValidationError, match="(?i)finite"):
        delta_t(2025.5, override=10**1000)
