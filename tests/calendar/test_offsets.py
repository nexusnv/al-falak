"""Tests for OffsetStore JSON overrides (phase-5 task 5)."""

import json
from datetime import datetime, timezone

import pytest

from alfalak.calendar.HijriDate import HijriDate
from alfalak.calendar.OffsetStore import OffsetStore
from alfalak.calendar.TabularCalendar import TabularCalendar
from alfalak.calendar.bridge import gregorian_to_hijri
from alfalak.exceptions import ConfigurationError, ValidationError


def test_offsets_plus1_minus2_month_boundary_carry() -> None:
    cal = TabularCalendar()
    # Tabular rule is deterministic: odd months 30 days, even months 29
    # (month 12 depends on leap). Pin the witnesses.
    assert cal.month_length(1446, 2) == 29
    assert cal.month_length(1446, 3) == 30

    # Forward +1 across a 29-day month-end rolls to day 1 of next month.
    plus1 = OffsetStore.from_dict({"1446-02": 1})
    assert plus1.apply(HijriDate(1446, 2, 29), cal) == HijriDate(1446, 3, 1)
    # Non-boundary forward step stays in-month.
    assert plus1.apply(HijriDate(1446, 2, 15), cal) == HijriDate(1446, 2, 16)

    # Backward -1 across month-start rolls to the previous month's last day.
    minus1 = OffsetStore.from_dict({"1446-03": -1})
    assert minus1.apply(HijriDate(1446, 3, 1), cal) == HijriDate(1446, 2, 29)

    # Backward -2 across month-start steps day-by-day into the prior month.
    minus2 = OffsetStore.from_dict({"1446-03": -2})
    assert minus2.apply(HijriDate(1446, 3, 1), cal) == HijriDate(1446, 2, 28)
    assert minus2.apply(HijriDate(1446, 3, 2), cal) == HijriDate(1446, 2, 29)

    # Year-boundary carry: 1446 % 30 == 6 (not a leap year) so Dhu al-Hijjah
    # has 29 days; +1 rolls into the next year.
    assert cal.month_length(1446, 12) == 29
    year_end = OffsetStore.from_dict({"1446-12": 1})
    assert year_end.apply(HijriDate(1446, 12, 29), cal) == HijriDate(1447, 1, 1)
    year_start = OffsetStore.from_dict({"1447-01": -1})
    assert year_start.apply(HijriDate(1447, 1, 1), cal) == HijriDate(1446, 12, 29)


def test_offsets_unknown_key_and_zero_raise() -> None:
    cal = TabularCalendar()
    # Unknown month key is simply unused — no raise, date passes through.
    store = OffsetStore.from_dict({"1446-02": 1})
    untouched = HijriDate(1446, 3, 15)
    assert store.apply(untouched, cal) == untouched

    # Value 0 is rejected as a config smell.
    with pytest.raises(ConfigurationError):
        OffsetStore.from_dict({"1446-02": 0})

    # File-backed zero entry names the path and the offending key.
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "offsets.json"
        path.write_text(json.dumps({"1446-02": 0}), encoding="utf-8")
        with pytest.raises(ConfigurationError) as excinfo:
            OffsetStore.from_json(path)
        message = str(excinfo.value)
        assert str(path) in message
        assert "1446-02" in message


@pytest.mark.parametrize(
    "key",
    ["1446-2", "1446/02", "abcd", "1446-13", "1446-00", "46-02", "1446-02-01", ""],
)
def test_offsets_bad_key_format_raises(key: str) -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        OffsetStore.from_dict({key: 1})
    assert key in str(excinfo.value)


@pytest.mark.parametrize("value", [3, -3, 2.0, "1", None, [1], True, False])
def test_offsets_bad_value_raises(value: object) -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        OffsetStore.from_dict({"1446-02": value})  # type: ignore[dict-item]
    assert "1446-02" in str(excinfo.value)


def test_offsets_non_object_json_raises(tmp_path: object) -> None:
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    path = tmp_path / "offsets.json"
    path.write_text(json.dumps([{"1446-02": 1}]), encoding="utf-8")
    with pytest.raises(ConfigurationError) as excinfo:
        OffsetStore.from_json(path)
    message = str(excinfo.value)
    assert str(path) in message


def test_offsets_unparseable_json_raises(tmp_path: object) -> None:
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    path = tmp_path / "offsets.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ConfigurationError) as excinfo:
        OffsetStore.from_json(path)
    assert str(path) in str(excinfo.value)


def test_offsets_precedence_over_computed() -> None:
    cal = TabularCalendar()
    # Ramadan (month 9, odd) has 30 tabular days; pin the witness.
    assert cal.month_length(1446, 9) == 30
    # Both the source and the destination months carry entries: the shift
    # must apply exactly once (no re-lookup of the shifted date's month).
    store = OffsetStore.from_dict({"1446-09": 1, "1446-10": 1})
    assert store.apply(HijriDate(1446, 9, 30), cal) == HijriDate(1446, 10, 1)

    # Lookup keys on the *computed* month only: a store holding just the
    # destination month leaves a source-month date untouched.
    dest_only = OffsetStore.from_dict({"1446-10": 1})
    assert dest_only.apply(HijriDate(1446, 9, 30), cal) == HijriDate(1446, 9, 30)


def test_offsets_bridge_integration_applies_last() -> None:
    cal = TabularCalendar()
    dt = datetime(2025, 3, 1, 12, 0, tzinfo=timezone.utc)
    computed = cal.from_gregorian(dt.date())
    key = f"{computed.year:04d}-{computed.month:02d}"
    store = OffsetStore.from_dict({key: 1})

    without = gregorian_to_hijri(dt, calendar=cal, offsets=None)
    assert without == computed

    with_offsets = gregorian_to_hijri(dt, calendar=cal, offsets=store)
    assert with_offsets == store.apply(computed, cal)
    assert with_offsets != computed


def test_offsets_from_file_alias_matches_from_json(tmp_path: object) -> None:
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    path = tmp_path / "offsets.json"
    path.write_text(json.dumps({"1446-02": -2}), encoding="utf-8")
    via_json = OffsetStore.from_json(path)
    via_file = OffsetStore.from_file(path)
    cal = TabularCalendar()
    hijri = HijriDate(1446, 2, 15)
    assert via_json.apply(hijri, cal) == via_file.apply(hijri, cal)


def test_offsets_from_dict_rejects_non_dict() -> None:
    with pytest.raises(ConfigurationError):
        OffsetStore.from_dict(["1446-02"])  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        OffsetStore.from_dict("1446-02")  # type: ignore[arg-type]


def test_offsets_non_utf8_file_raises(tmp_path: object) -> None:
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    path = tmp_path / "offsets.json"
    path.write_bytes(b'{"1446-02": \xff}')
    with pytest.raises(ConfigurationError) as excinfo:
        OffsetStore.from_json(path)
    assert str(path) in str(excinfo.value)


def test_offsets_apply_rejects_non_hijri() -> None:
    store = OffsetStore.from_dict({"1446-02": 1})
    with pytest.raises(ValidationError):
        store.apply("1446-02-15", TabularCalendar())  # type: ignore[arg-type]
