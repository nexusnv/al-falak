"""Yallop crescent-visibility criterion (best-time q and zones A-F).

q measures how far the geocentric arc of vision (ARCV, in degrees)
lies above the width-dependent visibility limit curve, scaled by 10
(Yallop 1997, NAO TN No.69, eq. 6.1)::

    limit = -0.1018*w^3 + 0.7319*w^2 - 6.3226*w + 11.8371
    q = (arcv_geo_deg - limit) / 10

with ``w`` the topocentric crescent width in arcminutes. Positive q
favours visibility; the zone maps q to the Yallop visibility class
(A: easily visible ... F: not visible even with a telescope).
"""

from alfalak.exceptions import ValidationError
from alfalak.util.FloatUtil import require_finite_real


def yallop_q(arcv_geo_deg: float, width_arcmin: float) -> float:
    """Best-time Yallop q from geocentric ARCV (deg) and width (arcmin)."""
    arcv = require_finite_real(arcv_geo_deg, "arcv_geo_deg")
    width = require_finite_real(width_arcmin, "width_arcmin")
    if width < 0.0:
        raise ValidationError(
            f"width_arcmin must be non-negative, got {width_arcmin!r}."
        )
    w = max(width, 1e-6)
    limit = -0.1018 * w**3 + 0.7319 * w**2 - 6.3226 * w + 11.8371
    # Yallop (1997) eq. 6.1 scales q by 1/10 to confine it roughly to [-1, 1].
    return (arcv - limit) / 10.0


def yallop_zone(q: float) -> str:
    """Yallop visibility zone (A-F) for a q value."""
    q_value = require_finite_real(q, "q")
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
