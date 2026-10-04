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
