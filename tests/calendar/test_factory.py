"""Tests for the calendar factory / registry sentinels (phase-5 task 1)."""

import sys
from datetime import date

import pytest

from alfalak.calendar import (
    CALENDARS,
    HijriCalendar,
    TabularCalendar,
    get_calendar,
)
from alfalak.calendar.HijriCalendar import _DeferredCalendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.exceptions import ConfigurationError, ValidationError


def test_factory_sentinels_default_never_raises() -> None:
    tabular = get_calendar("tabular")
    assert isinstance(tabular, TabularCalendar)
    assert tabular.name == "tabular"
    # The 'uqu' key resolves with defaults even though its observational
    # rule lands in a later increment; only misuse raises.
    uqu = get_calendar("uqu")
    assert isinstance(uqu, HijriCalendar)
    assert uqu.name == "uqu"


def test_factory_explicit_defaults_accepted_everywhere() -> None:
    get_calendar("tabular", country=None, adjustment_days=0)
    get_calendar("uqu", country=None, adjustment_days=0)


def test_factory_mabims_with_country_resolves() -> None:
    assert get_calendar("mabims", country="MY").name == "mabims"


def test_factory_misuse_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        get_calendar("tabular", country="MY")
    with pytest.raises(ConfigurationError):
        get_calendar("uqu", country="MY")
    with pytest.raises(ConfigurationError):
        get_calendar("uqu", adjustment_days=-2)
    with pytest.raises(ConfigurationError):
        get_calendar("mabims")
    with pytest.raises(ConfigurationError):
        get_calendar("mabims", country="MY", adjustment_days=2)


def test_factory_unknown_name_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        get_calendar("no-such-calendar")
    with pytest.raises(ConfigurationError):
        get_calendar(None)  # type: ignore[arg-type]


def test_factory_tabular_adjustment_range_checked() -> None:
    # Non-zero in-range adjustments are legal for tabular; out-of-range
    # values surface as ValidationError from the calendar itself.
    assert isinstance(get_calendar("tabular", adjustment_days=1), TabularCalendar)
    with pytest.raises(ValidationError):
        get_calendar("tabular", adjustment_days=3)


def test_calendars_registry_keys() -> None:
    assert {"tabular", "uqu", "mabims"} <= set(CALENDARS)
    assert CALENDARS["tabular"] is TabularCalendar
    assert issubclass(CALENDARS["uqu"], HijriCalendar)
    assert issubclass(CALENDARS["mabims"], HijriCalendar)


class _BareCalendar(HijriCalendar):
    """Minimal subclass delegating to the ABC bodies (covers them)."""

    @property
    def name(self) -> str:
        return super().name

    def from_gregorian(self, d: date) -> HijriDate:
        return super().from_gregorian(d)

    def to_gregorian(self, h: HijriDate) -> date:
        return super().to_gregorian(h)

    def month_length(self, year: int, month: int) -> int:
        return super().month_length(year, month)


def test_abstract_bodies_raise_not_implemented() -> None:
    bare = _BareCalendar()
    with pytest.raises(NotImplementedError):
        _ = bare.name
    with pytest.raises(NotImplementedError):
        bare.from_gregorian(date(2025, 3, 1))
    with pytest.raises(NotImplementedError):
        bare.to_gregorian(HijriDate(1446, 9, 1))
    with pytest.raises(NotImplementedError):
        bare.month_length(1446, 9)


def test_deferred_calendar_reports_registered_but_unimplemented() -> None:
    cal = _DeferredCalendar("mabims")
    assert cal.name == "mabims"
    with pytest.raises(ConfigurationError, match="not implemented"):
        cal.from_gregorian(date(2025, 3, 1))
    with pytest.raises(ConfigurationError, match="not implemented"):
        cal.to_gregorian(HijriDate(1446, 9, 1))
    with pytest.raises(ConfigurationError, match="not implemented"):
        cal.month_length(1446, 9)


def test_factory_mabims_rule_missing_returns_deferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "alfalak.calendar.MabimsCalendar", None)
    cal = get_calendar("mabims", country="MY")
    assert isinstance(cal, _DeferredCalendar)
    assert cal.name == "mabims"
    with pytest.raises(ConfigurationError, match="not implemented"):
        cal.from_gregorian(date(2025, 3, 1))
