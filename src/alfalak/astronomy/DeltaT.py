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
used_delta_t_s. Years outside 2005-2050 extrapolate beyond the
calibration range and emit a ``UserWarning``; the value is still
returned so historical queries keep working.
"""

import warnings

from alfalak.util.FloatUtil import require_finite_real

_DELTA_T_VALID_MIN_YEAR: float = 2005.0
_DELTA_T_VALID_MAX_YEAR: float = 2050.0


def delta_t(year: float, override: float | None = None) -> float:
    """Return Delta-T (TT minus UT1) in seconds for a decimal year."""
    year_value = require_finite_real(year, "year")
    if override is not None:
        return require_finite_real(override, "override")
    if not _DELTA_T_VALID_MIN_YEAR <= year_value <= _DELTA_T_VALID_MAX_YEAR:
        warnings.warn(
            f"delta_t polynomial is calibrated for 2005-2050; year {year_value} "
            "extrapolates beyond that range — pass override= with an IERS "
            "value when accuracy matters.",
            UserWarning,
            stacklevel=2,
        )
    t = year_value - 2000.0
    return 62.92 + 0.32217 * t + 0.005589 * t * t
