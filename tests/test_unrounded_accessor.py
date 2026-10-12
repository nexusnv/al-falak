"""Round-trip invariants for the second-precision accessors (Phase 6.4).

Anchors:
- default UTC build + an explicit ``time_zone`` build (DST-safe);
- both Asr clamp sites (test_polar_circle.py:103/:127 fixtures);
- adjustment-bearing methods (offsets are inside the unrounded value);
- derived markers (imsak/ishraq/dhuha) and the syuruk alias.
"""

import pytest
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from alfalak import (
    CalculationMethod, CalculationParameters, PolarCircleRule, Prayer,
    PrayerTimes, SunnahTimes,
)
from alfalak.exceptions import ConfigurationError, ValidationError
from alfalak.util.CalendarUtil import rounded_minute
from alfalak.util.DateComponents import DateComponents

ALL = (Prayer.IMSAK, Prayer.FAJR, Prayer.SUNRISE, Prayer.SYURUK,
       Prayer.ISHRAQ, Prayer.DHUHA, Prayer.DHUHR, Prayer.ASR,
       Prayer.MAGHRIB, Prayer.ISHA)


def _pt(time_zone=None):
    return PrayerTimes(
        (35.7750, -78.6336), DateComponents(2015, 7, 12),
        calculation_method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
        time_zone=time_zone,
    )


def _none_rule_params():
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.polar_circle_rule = PolarCircleRule.NONE
    return params


@pytest.mark.parametrize("tz", [None, ZoneInfo("America/New_York")])
def test_unrounded_round_trips_every_prayer(tz):
    pt = _pt(tz)
    display = tz or timezone.utc
    for prayer in ALL:
        assert (rounded_minute(pt.time_for_prayer_unrounded(prayer))
                .astimezone(display) == pt.time_for_prayer(prayer)), prayer


def test_unrounded_includes_offsets():
    base = _pt()
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.adjustments.fajr = 5
    shifted = PrayerTimes((35.7750, -78.6336), DateComponents(2015, 7, 12),
                          calculation_parameters=params)
    assert (shifted.time_for_prayer_unrounded(Prayer.FAJR)
            - base.time_for_prayer_unrounded(Prayer.FAJR)
            == timedelta(minutes=5))


def test_unrounded_syuruk_aliases_sunrise():
    pt = _pt()
    assert (pt.time_for_prayer_unrounded(Prayer.SYURUK)
            == pt.time_for_prayer_unrounded(Prayer.SUNRISE))


def test_unrounded_asr_clamp_dhuhr():
    pt = PrayerTimes((66.4, 18.96), DateComponents(2015, 12, 21),
                     calculation_parameters=_none_rule_params())
    assert pt.asr == pt.dhuhr
    assert pt.time_for_prayer_unrounded(Prayer.ASR) == pt.dhuhr


def test_unrounded_asr_clamp_maghrib():
    pt = PrayerTimes((89.1, 0.0), DateComponents(2024, 3, 19),
                     calculation_parameters=_none_rule_params())
    assert pt.asr == pt.maghrib
    assert pt.time_for_prayer_unrounded(Prayer.ASR) == pt.maghrib


def test_unrounded_rejects_none_and_non_prayer():
    pt = _pt()
    for bad in (Prayer.NONE, "fajr", None):
        with pytest.raises(ConfigurationError):
            pt.time_for_prayer_unrounded(bad)


def test_night_fraction_unrounded_round_trips():
    pt = _pt(ZoneInfo("America/New_York"))
    st = SunnahTimes(pt)
    for f in (1 / 3, 2 / 3, 0.5):
        assert (rounded_minute(st.night_fraction_unrounded(f))
                .astimezone(timezone.utc)
                == st.night_fraction(f).astimezone(timezone.utc))


def test_night_fraction_unrounded_explicit_anchors():
    pt = _pt()
    st = SunnahTimes(pt)
    assert (rounded_minute(st.night_fraction_unrounded(1 / 3, start=pt.isha))
            == st.night_fraction(1 / 3, start=pt.isha))


@pytest.mark.parametrize("bad", [0, 1, -0.1, 1.1, True, "x", None])
def test_night_fraction_unrounded_rejects_invalid_fraction(bad):
    st = SunnahTimes(_pt())
    with pytest.raises(ValidationError):
        st.night_fraction_unrounded(bad)