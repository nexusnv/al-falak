"""Abstract Hijri calendar contract plus the factory registry (phase 5)."""

from abc import ABC, abstractmethod
from datetime import date

from alfalak.calendar.HijriDate import HijriDate
from alfalak.exceptions import ConfigurationError


class HijriCalendar(ABC):
    """Contract every Hijri calendar rule implements.

    Date-only calendars speak ``date``: civil Gregorian dates in,
    civil Gregorian dates out. Datetime/sunset handling lives in the
    bridge (a later increment), not here.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Registry key of this calendar ("tabular", "uqu", "mabims")."""
        raise NotImplementedError

    @abstractmethod
    def from_gregorian(self, d: date) -> HijriDate:
        """Convert a Gregorian civil date to a Hijri date."""
        raise NotImplementedError

    @abstractmethod
    def to_gregorian(self, h: HijriDate) -> date:
        """Convert a Hijri date to a Gregorian civil date."""
        raise NotImplementedError

    @abstractmethod
    def month_length(self, year: int, month: int) -> int:
        """Return the length (29 or 30) of a Hijri month."""
        raise NotImplementedError


class _DeferredCalendar(HijriCalendar):
    """Provisional stand-in for a registered key whose rule module has not
    landed yet (observational calendars arrive in later increments).

    Resolution through :func:`get_calendar` already works (name and
    sentinel validation are stable); only conversion raises. Not exported.
    """

    def __init__(self, key: str) -> None:
        self._key = key

    @property
    def name(self) -> str:
        return self._key

    def from_gregorian(self, d: date) -> HijriDate:
        raise ConfigurationError(
            f"Calendar {self._key!r} is registered but its conversion rule "
            "is not implemented by this version of al-falak."
        )

    def to_gregorian(self, h: HijriDate) -> date:
        raise ConfigurationError(
            f"Calendar {self._key!r} is registered but its conversion rule "
            "is not implemented by this version of al-falak."
        )

    def month_length(self, year: int, month: int) -> int:
        raise ConfigurationError(
            f"Calendar {self._key!r} is registered but its conversion rule "
            "is not implemented by this version of al-falak."
        )


_KNOWN_KEYS = ("tabular", "uqu", "mabims")


def get_calendar(
    name: str, *, country: str | None = None, adjustment_days: int = 0
) -> HijriCalendar:
    """Resolve a calendar key to a calendar instance.

    Sentinel semantics: ``country`` is only valid for ``"mabims"``
    (required there); ``adjustment_days`` is only valid for ``"tabular"``.
    The defaults (``country=None``, ``adjustment_days=0``) are accepted
    everywhere and ignored outside their owning calendar. Unknown keys
    and any other misuse raise ``ConfigurationError``.
    """
    if not isinstance(name, str) or name not in _KNOWN_KEYS:
        raise ConfigurationError(
            f"Unknown calendar {name!r}. Expected one of {list(_KNOWN_KEYS)}."
        )
    if name != "mabims" and country is not None:
        raise ConfigurationError(
            f"Calendar {name!r} does not accept 'country'; "
            "it is only valid for 'mabims'."
        )
    if name == "mabims" and country is None:
        raise ConfigurationError(
            "Calendar 'mabims' requires a 'country' " "(one of MY, ID, BN, SG)."
        )
    if name != "tabular" and adjustment_days != 0:
        raise ConfigurationError(
            f"Calendar {name!r} does not accept 'adjustment_days'; "
            "it is only valid for 'tabular'."
        )
    if name == "tabular":
        from alfalak.calendar.TabularCalendar import TabularCalendar

        return TabularCalendar(adjustment_days=adjustment_days)
    if name == "uqu":
        try:
            # Module lands in a later increment; drop the ignores when it
            # does. (type: ignore must sit on the import line itself.)
            from alfalak.calendar.UmmAlQuraCalendar import (  # type: ignore[import-not-found]
                UmmAlQuraCalendar,
            )
        except ImportError:
            return _DeferredCalendar("uqu")
        return UmmAlQuraCalendar()
    try:
        from alfalak.calendar.MabimsCalendar import (  # type: ignore[import-not-found]
            MabimsCalendar,
        )
    except ImportError:
        return _DeferredCalendar("mabims")
    return MabimsCalendar(country=country)


# Registry imports sit at the bottom (not the top) because the concrete
# calendars import this module for the ABC; importing them any earlier
# would be circular. Function-level imports inside get_calendar stay lazy
# so later increments wire up without touching this file.
from alfalak.calendar.MabimsCalendar import MabimsCalendar  # noqa: E402
from alfalak.calendar.TabularCalendar import TabularCalendar  # noqa: E402

CALENDARS: dict[str, type[HijriCalendar]] = {
    "tabular": TabularCalendar,
    # Provisional entries: replaced by the real rule classes when their
    # modules land; keys are stable so registry-driven consumers
    # (factory, CLI choices) need no changes.
    "uqu": _DeferredCalendar,
    "mabims": MabimsCalendar,
}
