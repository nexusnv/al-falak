"""Tests for the calendar factory / registry sentinels (phase-5 task 1)."""

import pytest

from alfalak.calendar import (
    CALENDARS,
    HijriCalendar,
    TabularCalendar,
    get_calendar,
)
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
