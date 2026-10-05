"""Odeh crescent-visibility criterion (V value and classes A-D).

V measures how far the airless topocentric arc of vision (ARCV, in
degrees) lies above the width-dependent visibility limit curve::

    limit = -0.1018*w^3 + 0.7319*w^2 - 6.3226*w + 7.1651
    V = arcv_topo_deg - limit

with ``w`` the topocentric crescent width in arcminutes. Positive V
favours visibility; the class maps V (and elongation ARCL) to the Odeh
visibility class (A: easily visible ... D: invisible). An elongation
below 6.4 degrees (Danjon floor) is class D regardless of V.
"""

from alfalak.exceptions import ValidationError
from alfalak.util.FloatUtil import require_finite_real


def odeh_v(arcv_topo_deg: float, width_arcmin: float) -> float:
    """Odeh V from airless topocentric ARCV (deg) and width (arcmin)."""
    arcv = require_finite_real(arcv_topo_deg, "arcv_topo_deg")
    width = require_finite_real(width_arcmin, "width_arcmin")
    if width < 0.0:
        raise ValidationError(
            f"width_arcmin must be non-negative, got {width_arcmin!r}."
        )
    w = max(width, 1e-6)
    limit = -0.1018 * w**3 + 0.7319 * w**2 - 6.3226 * w + 7.1651
    return arcv - limit


def odeh_class(v: float, arcl_deg: float) -> str:
    """Odeh visibility class (A-D) for a V value and elongation (deg)."""
    v_value = require_finite_real(v, "v")
    arcl = require_finite_real(arcl_deg, "arcl_deg")
    if arcl < 6.4:
        return "D"
    if v_value >= 5.65:
        return "A"
    if v_value >= 2.0:
        return "B"
    if v_value >= -0.96:
        return "C"
    return "D"
