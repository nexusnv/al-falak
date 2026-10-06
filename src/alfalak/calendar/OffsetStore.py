"""JSON delta-offset overrides for Hijri months (phase 5).

An :class:`OffsetStore` wraps ``dict[str, int]`` mapping ``"YYYY-MM"`` of
the *computed* Hijri month to a shift in ``{-2, -1, 1, 2}``. The bridge
applies it last, after ``calendar.from_gregorian``.

Shifting is Hijri-day arithmetic: step day-by-day using the same
calendar's ``month_length`` (day 30 of a 29-day month rolls to day 1 of
the next month; day 1 minus 1 rolls to the last day of the previous
month, whose length is looked up on that month). This is intentionally
not ``to_gregorian(h) + N days`` followed by ``from_gregorian``: the
Gregorian round-trip would re-run the observational predicate and could
double-apply month-start logic. The shift applies once; the shifted
date's month entry is never re-looked-up.

``to_gregorian`` ignores the store entirely: offsets are a
Gregorian-to-Hijri display correction only, so the reverse direction is
always the unshifted calendar rule.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from alfalak.calendar.HijriCalendar import HijriCalendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.exceptions import ConfigurationError, ValidationError

_ALLOWED_SHIFTS = frozenset({-2, -1, 1, 2})

_KEY_RE = re.compile(r"^(\d{4})-(\d{2})$")


def _check_key(key: object) -> tuple[int, int]:
    """Validate an offset key, returning ``(year, month)``.

    Raises :class:`ConfigurationError` naming the offending key.
    """
    if not isinstance(key, str) or (match := _KEY_RE.match(key)) is None:
        raise ConfigurationError(
            f"Invalid offset key {key!r}: expected 'YYYY-MM' with month 01-12."
        )
    year, month = int(match.group(1)), int(match.group(2))
    if year < 1 or not 1 <= month <= 12:
        raise ConfigurationError(
            f"Invalid offset key {key!r}: expected 'YYYY-MM' with month 01-12."
        )
    return year, month


def _check_value(key: str, value: object) -> int:
    """Validate an offset value, returning it as ``int``.

    Rejects bools explicitly (``isinstance(True, int)`` trap) and
    anything outside ``{-2, -1, 1, 2}`` — including 0, which is a
    config smell (a no-op entry that should simply be absent).
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"Invalid offset for key {key!r}: expected an int in "
            f"{{-2, -1, 1, 2}}, got {value!r}."
        )
    if value not in _ALLOWED_SHIFTS:
        raise ConfigurationError(
            f"Invalid offset for key {key!r}: expected an int in "
            f"{{-2, -1, 1, 2}}, got {value!r}."
        )
    return value


def _validate_mapping(data: dict[Any, Any]) -> dict[str, int]:
    """Validate a raw mapping, returning a clean ``dict[str, int]`` copy."""
    clean: dict[str, int] = {}
    for key, value in data.items():
        _check_key(key)
        assert isinstance(key, str)
        clean[key] = _check_value(key, value)
    return clean


class OffsetStore:
    """Per-month Hijri-day shifts loaded from JSON."""

    def __init__(self, offsets: dict[str, int] | None = None) -> None:
        if offsets is not None and not isinstance(offsets, dict):
            raise ConfigurationError(
                f"OffsetStore needs a dict[str, int] mapping, got {offsets!r}."
            )
        raw: dict[Any, Any] = dict(offsets) if offsets is not None else {}
        self._offsets: dict[str, int] = _validate_mapping(raw)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> OffsetStore:
        """Build a store from an in-memory mapping."""
        if not isinstance(data, dict):
            raise ConfigurationError(
                "Offset data must be a JSON object mapping 'YYYY-MM' to "
                f"an int in {{-2, -1, 1, 2}}, got {data!r}."
            )
        return cls(dict(data))

    @classmethod
    def from_json(cls, path: str | os.PathLike[str]) -> OffsetStore:
        """Load a store from a JSON file at ``path``."""
        path_str = os.fspath(path)
        try:
            with open(path_str, encoding="utf-8") as fh:
                data = json.load(fh)
        except OSError as exc:
            raise ConfigurationError(
                f"Invalid offset file {path_str!r}: cannot read file ({exc})."
            ) from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"Invalid offset file {path_str!r}: unparseable JSON ({exc})."
            ) from exc
        except UnicodeDecodeError as exc:
            raise ConfigurationError(
                f"Invalid offset file {path_str!r}: not valid UTF-8 ({exc})."
            ) from exc
        if not isinstance(data, dict):
            raise ConfigurationError(
                f"Invalid offset file {path_str!r}: top level must be a JSON "
                f"object mapping 'YYYY-MM' to an int, got {data!r}."
            )
        try:
            return cls.from_dict(data)
        except ConfigurationError as exc:
            raise ConfigurationError(
                f"Invalid offset file {path_str!r}: {exc}"
            ) from exc

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> OffsetStore:
        """Alias of :meth:`from_json`."""
        return cls.from_json(path)

    def apply(self, hijri: HijriDate, calendar: HijriCalendar) -> HijriDate:
        """Shift ``hijri`` by its computed-month entry, once, no re-lookup."""
        if not isinstance(hijri, HijriDate):
            raise ValidationError(
                f"OffsetStore.apply needs a HijriDate, got {hijri!r}."
            )
        shift = self._offsets.get(f"{hijri.year:04d}-{hijri.month:02d}")
        if shift is None:
            return hijri
        year, month, day = hijri.year, hijri.month, hijri.day
        step = 1 if shift > 0 else -1
        for _ in range(abs(shift)):
            day += step
            if day > calendar.month_length(year, month):
                if month == 12:
                    year, month, day = year + 1, 1, 1
                else:
                    month, day = month + 1, 1
            elif day < 1:
                if month == 1:
                    year, month = year - 1, 12
                else:
                    month -= 1
                day = calendar.month_length(year, month)
        return HijriDate(year, month, day)
