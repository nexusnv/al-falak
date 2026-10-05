"""MABIMS moon-sighting presets (1992 rule and Neo-MABIMS 2021).

The 1992 MABIMS rule deems the crescent visible when the Moon is high
and elongated enough at sunset (altitude >= 2 degrees and elongation
>= 3 degrees) or when the Moon is sufficiently old (age >= 8 hours).
Neo-MABIMS (2021) tightens both sunset thresholds: altitude >= 3
degrees and elongation >= 6.4 degrees.
"""

from alfalak.util.FloatUtil import require_finite_real


def is_neo_mabims_2021(alt_deg: float, elong_deg: float) -> bool:
    """Neo-MABIMS 2021 visibility: altitude >= 3 deg and elongation >= 6.4 deg."""
    alt = require_finite_real(alt_deg, "alt_deg")
    elong = require_finite_real(elong_deg, "elong_deg")
    return alt >= 3.0 and elong >= 6.4


def is_mabims_1992(alt_deg: float, elong_deg: float, age_hours: float) -> bool:
    """1992 MABIMS visibility: (alt >= 2 and elong >= 3) or age >= 8 hours.

    ``age_hours`` is the Moon's age at moonset (use
    ``CrescentGeometry.moon_age_at_moonset_days * 24``); the sunset age is
    up to ~1 h younger. Only apply the age branch post-conjunction: on a
    pre-conjunction evening the age still counts from the *previous* new
    moon (~29 days) and fires for a Moon with no evening window — check
    ``lag_hours`` first (small positive lag, growing elongation).
    """
    alt = require_finite_real(alt_deg, "alt_deg")
    elong = require_finite_real(elong_deg, "elong_deg")
    age = require_finite_real(age_hours, "age_hours")
    return (alt >= 2.0 and elong >= 3.0) or (age >= 8.0)
