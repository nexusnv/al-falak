"""Isolated Delta-T provider (TT minus UT1, in seconds).

Default is the Espenak polynomial for 2005-2050: ``62.92 + 0.32217*t +
0.005589*t*t`` with ``t = year - 2000.0``. Historical multi-century fits
such as Morrison/Stephenson cover the far past/future but diverge from
recent observed values; for modern dates prefer IERS-observed Delta-T
(passed via ``override``) over any long-range polynomial.

The prayer path (SolarTime/PrayerTimes) never calls this; it is reserved
for the future lunar/moon-sighting path. Known limitation: this
polynomial runs ~5-6s high vs IERS observed values by 2024-2025 (e.g.
74.77 vs ~69.2 at 2025.5); pass override= with an IERS value when
absolute-time accuracy matters — CrescentGeometry records
used_delta_t_s.
"""

import math
import numbers
from decimal import Decimal

from alfalak.exceptions import ValidationError


def _require_finite_real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (numbers.Real, Decimal)):
        raise ValidationError(f"{name} must be a real number, got {value!r}.")
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError(f"{name} must be finite, got {value!r}.")
    return result


def delta_t(year: float, override: float | None = None) -> float:
    """Return Delta-T (TT minus UT1) in seconds for a decimal year."""
    if override is not None:
        return _require_finite_real(override, "override")
    year_value = _require_finite_real(year, "year")
    t = year_value - 2000.0
    return 62.92 + 0.32217 * t + 0.005589 * t * t
