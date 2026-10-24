from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
from zoneinfo import ZoneInfo

import pytest

from alfalak import PrayerTimes, SunnahTimes, ValidationError
from alfalak.calculation import (
    CalculationMethod,
    CalculationParameters,
    PrayerAdjustments,
)
from alfalak.util.DateComponents import DateComponents


def _prayer_times():
    return PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        CalculationMethod.MUSLIM_WORLD_LEAGUE,
    )


def test_sunnah_times():
    prayer_times = _prayer_times()
    sunnah_times = SunnahTimes(prayer_times)

    assert sunnah_times.middle_of_the_night == datetime(
        2015, 7, 13, 4, 28, tzinfo=timezone.utc
    )
    assert sunnah_times.first_third_of_the_night == datetime(
        2015, 7, 13, 3, 9, tzinfo=timezone.utc
    )
    assert sunnah_times.last_third_of_the_night == datetime(
        2015, 7, 13, 5, 46, tzinfo=timezone.utc
    )


def test_first_third_ordering_within_night():
    prayer_times = _prayer_times()
    sunnah_times = SunnahTimes(prayer_times)
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 13),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )

    assert prayer_times.maghrib < sunnah_times.first_third_of_the_night
    assert sunnah_times.first_third_of_the_night < sunnah_times.middle_of_the_night
    assert sunnah_times.middle_of_the_night < sunnah_times.last_third_of_the_night
    assert sunnah_times.last_third_of_the_night < tomorrow.fajr


def test_night_fraction_wrappers_equal_generic():
    sunnah_times = SunnahTimes(_prayer_times())

    assert sunnah_times.night_fraction(1 / 2) == sunnah_times.middle_of_the_night
    assert sunnah_times.night_fraction(1 / 3) == sunnah_times.first_third_of_the_night
    assert sunnah_times.night_fraction(2 / 3) == sunnah_times.last_third_of_the_night
    # Quarter fractions stay strictly inside the night and bracket the thirds.
    quarter = sunnah_times.night_fraction(1 / 4)
    three_quarters = sunnah_times.night_fraction(3 / 4)
    assert quarter < sunnah_times.first_third_of_the_night
    assert quarter < sunnah_times.middle_of_the_night
    assert sunnah_times.middle_of_the_night < three_quarters
    assert sunnah_times.last_third_of_the_night < three_quarters


@pytest.mark.parametrize(
    "fraction", [0, 1, -0.5, 1.5, float("nan"), float("inf"), True, "0.5", None]
)
def test_night_fraction_invalid_raises_validation_error(fraction):
    sunnah_times = SunnahTimes(_prayer_times())
    with pytest.raises(ValidationError, match=r"(?i)fraction|interval"):
        sunnah_times.night_fraction(fraction)


def test_night_fraction_explicit_anchors_match_default():
    prayer_times = _prayer_times()
    sunnah_times = SunnahTimes(prayer_times)
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 13),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )

    assert (
        sunnah_times.night_fraction(
            1 / 2, start=prayer_times.maghrib, end=tomorrow.fajr
        )
        == sunnah_times.middle_of_the_night
    )


def test_night_fraction_isha_anchored_school():
    # Isha-anchored night (Isha -> next-day Fajr) is shorter, so its
    # midpoint lands after the Maghrib-anchored midpoint.
    prayer_times = _prayer_times()
    sunnah_times = SunnahTimes(prayer_times)

    isha_half = sunnah_times.night_fraction(1 / 2, start=prayer_times.isha)
    assert isha_half > sunnah_times.middle_of_the_night
    assert isha_half == datetime(2015, 7, 13, 5, 17, tzinfo=timezone.utc)
    assert prayer_times.isha < isha_half


def test_night_fraction_accepts_decimal_and_fraction():
    sunnah_times = SunnahTimes(_prayer_times())

    assert (
        sunnah_times.night_fraction(Decimal("0.5")) == sunnah_times.middle_of_the_night
    )
    assert (
        sunnah_times.night_fraction(Fraction(1, 2)) == sunnah_times.middle_of_the_night
    )
    assert sunnah_times.night_fraction(Decimal("0.25")) == sunnah_times.night_fraction(
        1 / 4
    )


def test_night_fraction_exact_tiny_and_near_one_accepted():
    # Values valid in (0, 1) that underflow to 0.0 or round to 1.0 as
    # binary floats must not be rejected.
    prayer_times = _prayer_times()
    sunnah_times = SunnahTimes(prayer_times)
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 13),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )

    assert sunnah_times.night_fraction(Fraction(1, 10**400)) == prayer_times.maghrib
    assert sunnah_times.night_fraction(Decimal("1E-400")) == prayer_times.maghrib
    assert sunnah_times.night_fraction(Fraction(10**400 - 1, 10**400)) == tomorrow.fajr


def test_night_fraction_decimal_nan_signaling_raises_validation_error():
    sunnah_times = SunnahTimes(_prayer_times())
    with pytest.raises(ValidationError, match=r"(?i)fraction"):
        sunnah_times.night_fraction(Decimal("NaN"))
    with pytest.raises(ValidationError, match=r"(?i)fraction"):
        sunnah_times.night_fraction(Decimal("sNaN"))


def test_night_fraction_sub_minute_anchors_round_half_up():
    # A 59 s interval starting at .9 s: half is .4 s past :30, so
    # half-up minute rounding must round up. Truncating the offset to
    # whole seconds first would land at :29.9 and round down instead.
    sunnah_times = SunnahTimes(_prayer_times())
    start = datetime(2015, 7, 13, 0, 0, 0, 900000, tzinfo=timezone.utc)
    end = start + timedelta(seconds=59)
    assert sunnah_times.night_fraction(1 / 2, start=start, end=end) == datetime(
        2015, 7, 13, 0, 1, tzinfo=timezone.utc
    )


def test_night_fraction_end_only_and_fully_custom():
    prayer_times = _prayer_times()
    sunnah_times = SunnahTimes(prayer_times)
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 13),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )

    # End-only: start falls back to Maghrib, so pushing the end out by
    # one hour pushes the midpoint out by exactly half an hour.
    custom_end = tomorrow.fajr + timedelta(hours=1)
    assert sunnah_times.night_fraction(
        1 / 2, end=custom_end
    ) == sunnah_times.middle_of_the_night + timedelta(minutes=30)

    # Fully explicit pair, independent of prayer times.
    start = datetime(2015, 7, 12, 22, 0, tzinfo=timezone.utc)
    end = datetime(2015, 7, 13, 6, 0, tzinfo=timezone.utc)
    assert sunnah_times.night_fraction(1 / 2, start=start, end=end) == datetime(
        2015, 7, 13, 2, 0, tzinfo=timezone.utc
    )
    assert sunnah_times.night_fraction(1 / 4, start=start, end=end) == datetime(
        2015, 7, 13, 0, 0, tzinfo=timezone.utc
    )


def test_sunnah_times_degenerate_night_raises():
    # Maghrib +500 min lands after next-day Fajr, so the default night
    # interval is inverted and construction must fail fast.
    parameters = CalculationParameters(
        method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
        adjustments=PrayerAdjustments(maghrib=500),
    )
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 12),
        calculation_parameters=parameters,
    )
    with pytest.raises(ValidationError, match="(?i)after start|interval"):
        SunnahTimes(prayer_times)


def test_night_fraction_anchor_validation():
    sunnah_times = SunnahTimes(_prayer_times())
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 13),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )

    with pytest.raises(ValidationError, match="(?i)datetime|anchor"):
        sunnah_times.night_fraction(1 / 2, start="maghrib")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="(?i)aware|anchor"):
        sunnah_times.night_fraction(1 / 2, start=datetime(2015, 7, 13, 0, 32))
    with pytest.raises(ValidationError, match="(?i)after start|interval"):
        sunnah_times.night_fraction(1 / 2, start=tomorrow.fajr, end=tomorrow.fajr)
    with pytest.raises(ValidationError, match="(?i)after start|interval"):
        sunnah_times.night_fraction(
            1 / 2,
            start=tomorrow.fajr,
            end=SunnahTimes(_prayer_times()).night_fraction(1 / 2),
        )


def test_tahajjud_window_endpoints():
    prayer_times = _prayer_times()
    sunnah_times = SunnahTimes(prayer_times)
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 13),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )

    start, end = sunnah_times.tahajjud_window
    assert start == sunnah_times.last_third_of_the_night
    assert end == tomorrow.fajr
    assert start < end
    assert end == datetime(2015, 7, 13, 8, 23, tzinfo=timezone.utc)


def test_sunnah_times_ordering():
    prayer_times = _prayer_times()
    sunnah_times = SunnahTimes(prayer_times)
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 7, 13),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )

    assert prayer_times.maghrib < sunnah_times.middle_of_the_night
    assert sunnah_times.middle_of_the_night < sunnah_times.last_third_of_the_night
    assert sunnah_times.last_third_of_the_night < tomorrow.fajr


def test_sunnah_times_across_dst_transition():
    # US springs forward on 2015-03-08 (02:00 EST -> 03:00 EDT); duration
    # math must use absolute elapsed time, not wall-clock subtraction
    tz = ZoneInfo("America/New_York")
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 3, 7),
        CalculationMethod.MUSLIM_WORLD_LEAGUE,
        time_zone=tz,
    )
    sunnah_times = SunnahTimes(prayer_times)

    assert sunnah_times.middle_of_the_night == datetime(2015, 3, 7, 23, 43, tzinfo=tz)
    assert sunnah_times.first_third_of_the_night == datetime(
        2015, 3, 7, 21, 54, tzinfo=tz
    )
    assert sunnah_times.last_third_of_the_night == datetime(
        2015, 3, 8, 1, 32, tzinfo=tz
    )
    assert sunnah_times.night_fraction(1 / 3) == sunnah_times.first_third_of_the_night
    window_start, window_end = sunnah_times.tahajjud_window
    assert window_start == sunnah_times.last_third_of_the_night
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 3, 8),
        CalculationMethod.MUSLIM_WORLD_LEAGUE,
        time_zone=tz,
    )
    assert window_end == tomorrow.fajr
    assert (
        prayer_times.maghrib
        < sunnah_times.first_third_of_the_night
        < sunnah_times.middle_of_the_night
        < sunnah_times.last_third_of_the_night
        < tomorrow.fajr
    )


def test_sunnah_times_across_fall_back_transition():
    # US falls back on 2015-11-01 (02:00 EDT -> 01:00 EST); the night of
    # 2015-10-31 spans the extra hour. UTC duration (11.83 h) exceeds the
    # wall-clock difference (10.83 h); markers must follow UTC.
    tz = ZoneInfo("America/New_York")
    prayer_times = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 10, 31),
        CalculationMethod.MUSLIM_WORLD_LEAGUE,
        time_zone=tz,
    )
    sunnah_times = SunnahTimes(prayer_times)
    tomorrow = PrayerTimes(
        (35.7750, -78.6336),
        DateComponents(2015, 11, 1),
        CalculationMethod.MUSLIM_WORLD_LEAGUE,
        time_zone=tz,
    )

    assert sunnah_times.first_third_of_the_night == datetime(
        2015, 10, 31, 22, 17, tzinfo=tz
    )
    assert sunnah_times.middle_of_the_night == datetime(2015, 11, 1, 0, 15, tzinfo=tz)
    assert sunnah_times.last_third_of_the_night == datetime(
        2015, 11, 1, 1, 13, tzinfo=tz
    )
    assert sunnah_times.last_third_of_the_night.fold == 1
    assert sunnah_times.night_fraction(1 / 2) == sunnah_times.middle_of_the_night
    assert sunnah_times.night_fraction(1 / 3) == sunnah_times.first_third_of_the_night
    assert sunnah_times.night_fraction(2 / 3) == sunnah_times.last_third_of_the_night

    window_start, window_end = sunnah_times.tahajjud_window
    assert window_start == sunnah_times.last_third_of_the_night
    assert window_end == tomorrow.fajr
    assert (
        prayer_times.maghrib
        < sunnah_times.first_third_of_the_night
        < sunnah_times.middle_of_the_night
        < sunnah_times.last_third_of_the_night
        < tomorrow.fajr
    )

    maghrib_utc = prayer_times.maghrib.astimezone(timezone.utc)
    fajr_utc = tomorrow.fajr.astimezone(timezone.utc)
    absolute_hours = (fajr_utc - maghrib_utc).total_seconds() / 3600
    assert absolute_hours == pytest.approx(11.83, abs=0.01)
    wall_hours = (
        tomorrow.fajr.replace(tzinfo=None) - prayer_times.maghrib.replace(tzinfo=None)
    ).total_seconds() / 3600
    assert wall_hours == pytest.approx(absolute_hours - 1.0, abs=0.01)
    expected_middle_utc = maghrib_utc + timedelta(
        seconds=int((fajr_utc - maghrib_utc).total_seconds() / 2)
    )
    assert sunnah_times.middle_of_the_night.astimezone(timezone.utc).replace(
        second=0, microsecond=0
    ) == expected_middle_utc.replace(second=0, microsecond=0)
