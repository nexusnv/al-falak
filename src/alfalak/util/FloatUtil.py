import math
import numbers
from decimal import Decimal

from alfalak.exceptions import ValidationError


def normalize_with_bound(value: float, max: float) -> float:
    return value - (max * (math.floor(value / max)))


def unwind_angle(value: float) -> float:
    return normalize_with_bound(value, 360)


def closest_angle(angle: float) -> float:
    if angle >= -180 and angle <= 180:
        return angle

    return angle - (360 * round(angle / 360))


def require_finite_real(value: object, name: str) -> float:
    """Coerce a real number to float, rejecting bools and non-finite values."""
    if isinstance(value, bool) or not isinstance(value, (numbers.Real, Decimal)):
        raise ValidationError(f"{name} must be a real number, got {value!r}.")
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError(f"{name} must be finite, got {value!r}.")
    return result
