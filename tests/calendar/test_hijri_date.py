"""Tests for HijriDate: validation, isoformat, ordering (phase-5 task 1)."""

import dataclasses

import pytest

from alfalak.calendar import HijriDate
from alfalak.exceptions import ValidationError


def test_hijri_date_rejects_month_13_and_day_31() -> None:
    with pytest.raises(ValidationError):
        HijriDate(1446, 13, 1)
    with pytest.raises(ValidationError):
        HijriDate(1446, 1, 31)


@pytest.mark.parametrize(
    ("year", "month", "day"),
    [
        (0, 1, 1),
        (-5, 1, 1),
        (1446, 0, 1),
        (1446, 13, 1),
        (1446, 1, 0),
        (1446, 1, 31),
    ],
)
def test_hijri_date_rejects_out_of_range(year: int, month: int, day: int) -> None:
    with pytest.raises(ValidationError):
        HijriDate(year, month, day)


def test_hijri_date_rejects_bool_fields() -> None:
    with pytest.raises(ValidationError):
        HijriDate(True, 1, 1)  # type: ignore[arg-type]


def test_hijri_date_isoformat_zero_padded() -> None:
    assert HijriDate(1446, 9, 1).isoformat() == "1446-09-01"
    assert HijriDate(1, 1, 1).isoformat() == "0001-01-01"
    assert HijriDate(1446, 12, 30).isoformat() == "1446-12-30"


def test_hijri_date_ordering_and_equality() -> None:
    assert HijriDate(1446, 9, 1) == HijriDate(1446, 9, 1)
    assert HijriDate(1446, 9, 1) < HijriDate(1446, 9, 2)
    assert HijriDate(1446, 9, 29) < HijriDate(1446, 10, 1)
    assert HijriDate(1446, 12, 30) < HijriDate(1447, 1, 1)
    assert HijriDate(1447, 1, 1) > HijriDate(1446, 9, 1)
    assert sorted(
        [HijriDate(1447, 1, 1), HijriDate(1446, 9, 2), HijriDate(1446, 9, 1)]
    ) == [
        HijriDate(1446, 9, 1),
        HijriDate(1446, 9, 2),
        HijriDate(1447, 1, 1),
    ]


def test_hijri_date_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        HijriDate(1446, 9, 1).day = 2  # type: ignore[misc]
