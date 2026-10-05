"""Immutable Hijri date value type (rule-free; phase 5)."""

from dataclasses import dataclass

from alfalak.exceptions import ValidationError


@dataclass(frozen=True, order=True)
class HijriDate:
    """A Hijri calendar date without any calendar rule attached.

    The constructor enforces the universal bound (day 1..30); the exact
    month length (29 vs 30) depends on the calendar rule, so each calendar
    enforces it at conversion time.
    """

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        for label, value in (
            ("year", self.year),
            ("month", self.month),
            ("day", self.day),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"Hijri {label} must be an int, got {value!r}.")
        if self.year < 1:
            raise ValidationError(f"Hijri year must be >= 1, got {self.year}.")
        if not 1 <= self.month <= 12:
            raise ValidationError(
                f"Hijri month must be within [1, 12], got {self.month}."
            )
        if not 1 <= self.day <= 30:
            raise ValidationError(f"Hijri day must be within [1, 30], got {self.day}.")

    def isoformat(self) -> str:
        """Return the date as zero-padded "YYYY-MM-DD"."""
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
