"""Yallop crescent-visibility criterion (best-time q and zones A-F).

q measures how far the geocentric arc of vision (ARCV, in degrees)
lies above the width-dependent visibility limit curve::

    limit = -0.1018*w^3 + 0.7319*w^2 - 6.3226*w + 11.8371
    q = arcv_geo_deg - limit

with ``w`` the topocentric crescent width in arcminutes. Positive q
favours visibility; the zone maps q to the Yallop visibility class
(A: easily visible ... F: not visible even with a telescope).
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


def yallop_q(arcv_geo_deg: float, width_arcmin: float) -> float:
    """Best-time Yallop q from geocentric ARCV (deg) and width (arcmin)."""
    arcv = _require_finite_real(arcv_geo_deg, "arcv_geo_deg")
    width = _require_finite_real(width_arcmin, "width_arcmin")
    w = max(width, 1e-6)
    limit = -0.1018 * w**3 + 0.7319 * w**2 - 6.3226 * w + 11.8371
    return arcv - limit


def yallop_zone(q: float) -> str:
    """Yallop visibility zone (A-F) for a q value."""
    q_value = _require_finite_real(q, "q")
    if q_value > 0.216:
        return "A"
    if q_value > -0.014:
        return "B"
    if q_value > -0.160:
        return "C"
    if q_value > -0.232:
        return "D"
    if q_value > -0.293:
        return "E"
    return "F"
