"""MABIMS moon-sighting presets (1992 rule and Neo-MABIMS 2021).

The 1992 MABIMS rule deems the crescent visible when the Moon is high
and elongated enough at sunset (altitude >= 2 degrees and elongation
>= 3 degrees) or when the Moon is sufficiently old (age >= 8 hours).
Neo-MABIMS (2021) tightens both sunset thresholds: altitude >= 3
degrees and elongation >= 6.4 degrees.
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


def is_neo_mabims_2021(alt_deg: float, elong_deg: float) -> bool:
    """Neo-MABIMS 2021 visibility: altitude >= 3 deg and elongation >= 6.4 deg."""
    alt = _require_finite_real(alt_deg, "alt_deg")
    elong = _require_finite_real(elong_deg, "elong_deg")
    return alt >= 3.0 and elong >= 6.4


def is_mabims_1992(alt_deg: float, elong_deg: float, age_hours: float) -> bool:
    """1992 MABIMS visibility: (alt >= 2 and elong >= 3) or age >= 8 hours."""
    alt = _require_finite_real(alt_deg, "alt_deg")
    elong = _require_finite_real(elong_deg, "elong_deg")
    age = _require_finite_real(age_hours, "age_hours")
    return (alt >= 2.0 and elong >= 3.0) or (age >= 8.0)
