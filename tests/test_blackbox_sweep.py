"""Black-box sweep (promoted to the permanent suite; pre-release al-falak 1.0.0).

Public seam only: ``alfalak`` root exports (PrayerTimes, Qibla, SunnahTimes,
CalculationMethod, CalculationParameters, HighLatitudeRule, Madhab,
PolarCircleRule, PrayerAdjustments, Coordinates, Prayer, exceptions) plus the
CLI consumer workflow (``alfalak.__main__.main`` / ``python -m alfalak``).
No private helpers, no internal state, no mocks, no call-order assertions.

Traceability: scenario IDs ``BB-*`` are defined inline — each test names its
oracle (contract golden / invariant / stable error / characterization).

NOTE on task wording: there is no ``SunnahTimes.from_prayer_times`` in 1.0.0;
the public seam is the ``SunnahTimes(prayer_times)`` constructor, which is
what BB-SUNNAH-* exercises.
"""

import subprocess
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from alfalak import (
    AlFalakError,
    AstronomicalError,
    CalculationMethod,
    CalculationParameters,
    ConfigurationError,
    Coordinates,
    HighLatitudeRule,
    HijriCalendar,
    HijriDate,
    MabimsCalendar,
    Madhab,
    OffsetStore,
    PolarCircleRule,
    Prayer,
    PrayerTimes,
    Qibla,
    SunnahTimes,
    TabularCalendar,
    UmmAlQuraCalendar,
    ValidationError,
    get_calendar,
    gregorian_to_hijri,
)
from alfalak.__main__ import main
from alfalak.Qibla import MAKKAH
from alfalak.util.DateComponents import DateComponents
from support import is_ordered as _ordered

RALEIGH = (35.7750, -78.6336)
OSLO = (59.9094, 10.7349)
TROMSO = (69.65, 18.96)
MID_DATE = datetime(2015, 7, 12, 12, 0, 0, tzinfo=timezone.utc)
WINTER_OSLO = DateComponents(2016, 1, 1)
WINTER_TROMSO = DateComponents(2015, 12, 21)
PRAYER_ATTRS = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")


def _all_utc(pt: PrayerTimes) -> bool:
    return all(getattr(pt, name).tzinfo is not None for name in PRAYER_ATTRS)


# ---------------------------------------------------------------------------
# BB-PT-METHOD-*: every CalculationMethod returns ordered, UTC-aware times.
# Oracle: differential invariant (fajr<sunrise<dhuhr<=asr<maghrib<isha, UTC).
# Label: contract (documented multi-method support + UTC guarantee).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method",
    [m for m in CalculationMethod if m is not CalculationMethod.NONE],
    ids=[m.name for m in CalculationMethod if m is not CalculationMethod.NONE],
)
def test_method_returns_ordered_utc_times(method):
    pt = PrayerTimes(RALEIGH, MID_DATE, calculation_method=method)
    assert _ordered(pt), method
    assert _all_utc(pt), method


def test_method_none_characterization():
    # BB-PT-METHOD-NONE-01. Oracle: characterization (no documented contract
    # for method NONE; angles default to 0). Observed 2026-09-29: NONE returns
    # tz-aware datetimes but inverts fajr/sunrise and maghrib/isha.
    pt = PrayerTimes(RALEIGH, MID_DATE, CalculationMethod.NONE)
    assert _all_utc(pt)
    assert pt.fajr > pt.sunrise  # 10:13 > 10:08 observed
    assert pt.isha < pt.maghrib  # 00:28 < 00:32 observed


# ---------------------------------------------------------------------------
# BB-PT-GOLDEN-*: exact outcomes from reviewed golden tests.
# Oracle: reviewed golden result (tests/test_prayer_times.py, test_cli.py).
# Label: contract.
# ---------------------------------------------------------------------------


def test_golden_north_america_hanafi_second_precision():
    # BB-PT-GOLDEN-NA-01. Source: test_prayer_times_second_precision_locked.
    params = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
    params.madhab = Madhab.HANAFI
    pt = PrayerTimes(
        RALEIGH, DateComponents(2015, 7, 12), calculation_parameters=params
    )
    assert pt.fajr.strftime("%H:%M:%S") == "08:42:00"
    assert pt.sunrise.strftime("%H:%M:%S") == "10:08:00"
    assert pt.dhuhr.strftime("%H:%M:%S") == "17:21:00"
    assert pt.asr.strftime("%H:%M:%S") == "22:22:00"
    assert pt.maghrib.strftime("%H:%M:%S") == "00:32:00"
    assert pt.isha.strftime("%H:%M:%S") == "01:57:00"


def test_golden_moon_sighting_committee():
    # BB-PT-GOLDEN-MOON-01. Source: test_moon_sighting_method (NY wall clock).
    tz = ZoneInfo("America/New_York")
    pt = PrayerTimes(
        RALEIGH,
        DateComponents(2016, 1, 31),
        CalculationMethod.MOON_SIGHTING_COMMITTEE,
    )
    fmt = "%I:%M %p"
    assert pt.fajr.astimezone(tz).strftime(fmt) == "05:48 AM"
    assert pt.sunrise.astimezone(tz).strftime(fmt) == "07:16 AM"
    assert pt.dhuhr.astimezone(tz).strftime(fmt) == "12:33 PM"
    assert pt.asr.astimezone(tz).strftime(fmt) == "03:20 PM"
    assert pt.maghrib.astimezone(tz).strftime(fmt) == "05:43 PM"
    assert pt.isha.astimezone(tz).strftime(fmt) == "07:05 PM"


# ---------------------------------------------------------------------------
# BB-PT-MADHAB-01: Hanafi Asr is later than Shafi Asr, all else equal.
# Oracle: documented madhab rule (README + Madhab.get_shadow_length DOUBLE).
# Label: contract.
# ---------------------------------------------------------------------------


def test_madhab_hanafi_asr_later_than_shafi():
    def asr(madhab):
        params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
        params.madhab = madhab
        return PrayerTimes(
            RALEIGH, DateComponents(2015, 7, 12), calculation_parameters=params
        )

    shafi, hanafi = asr(Madhab.SHAFI), asr(Madhab.HANAFI)
    assert hanafi.asr > shafi.asr
    for name in ("fajr", "sunrise", "dhuhr", "maghrib", "isha"):
        assert getattr(hanafi, name) == getattr(shafi, name)


# ---------------------------------------------------------------------------
# BB-PT-HLR-*: HighLatitudeRule variants stay ordered at high latitude.
# Oracle: invariant (documented high-latitude support). Label: contract.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rule", list(HighLatitudeRule), ids=[r.name for r in HighLatitudeRule]
)
def test_high_latitude_rules_stay_ordered(rule):
    # BB-PT-HLR-01..03. Oslo 2016-01-01 mirrors test_moon_sighting_method_high_lat.
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.high_latitude_rule = rule
    pt = PrayerTimes(OSLO, WINTER_OSLO, calculation_parameters=params)
    assert _ordered(pt), rule
    assert _all_utc(pt), rule


# ---------------------------------------------------------------------------
# BB-PT-POLAR-*: PolarCircleRule strategies at Tromso (polar night/summer).
# Oracles: stable error (NONE) / invariant + documented rule behavior.
# Label: contract.
# ---------------------------------------------------------------------------


def test_polar_none_raises_astronomical_error():
    # BB-PT-POLAR-01. Source: test_polar_night_error_message.
    params = CalculationParameters(
        method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
        polar_circle_rule=PolarCircleRule.NONE,
    )
    with pytest.raises(AstronomicalError, match="(?i)undefined|polar"):
        PrayerTimes(TROMSO, WINTER_TROMSO, calculation_parameters=params)


def test_polar_nearest_latitude_clamps_equatorward():
    # BB-PT-POLAR-02. Source: test_default_assumes_nearest_latitude.
    pt = PrayerTimes(
        TROMSO,
        WINTER_TROMSO,
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )
    assert _ordered(pt)
    assert 60 < pt.coordinates.latitude < TROMSO[0]
    assert pt.coordinates.longitude == TROMSO[1]


def test_polar_nearest_day_keeps_location_shifts_date():
    # BB-PT-POLAR-03. Source: test_nearest_day_keeps_location_but_shifts_date.
    pt = PrayerTimes(
        TROMSO,
        WINTER_TROMSO,
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
            polar_circle_rule=PolarCircleRule.NEAREST_DAY,
        ),
    )
    assert _ordered(pt)
    assert pt.coordinates.latitude == TROMSO[0]
    assert pt.fajr.date() != datetime(2015, 12, 21, tzinfo=timezone.utc).date()


def test_polar_makkah_matches_makkah_schedule():
    # BB-PT-POLAR-04. Source: test_makkah_rule_matches_makkah_schedule.
    params = CalculationParameters(
        method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
        polar_circle_rule=PolarCircleRule.MAKKAH,
    )
    polar = PrayerTimes(TROMSO, WINTER_TROMSO, calculation_parameters=params)
    makkah = PrayerTimes(
        (MAKKAH.latitude, MAKKAH.longitude),
        WINTER_TROMSO,
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
            polar_circle_rule=PolarCircleRule.MAKKAH,
        ),
    )
    assert polar.coordinates.latitude == MAKKAH.latitude
    for name in PRAYER_ATTRS:
        assert getattr(polar, name) == getattr(makkah, name)


def test_polar_rules_do_not_change_normal_days():
    # BB-PT-POLAR-05. Source: test_no_rule_change_on_normal_days.
    default = PrayerTimes(
        RALEIGH,
        DateComponents(2015, 7, 12),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ),
    )
    none = PrayerTimes(
        RALEIGH,
        DateComponents(2015, 7, 12),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
            polar_circle_rule=PolarCircleRule.NONE,
        ),
    )
    for name in PRAYER_ATTRS:
        assert getattr(default, name) == getattr(none, name)


# ---------------------------------------------------------------------------
# BB-PT-ADJ-*: PrayerAdjustments minute offsets.
# Oracle: exact shift arithmetic + reviewed golden (test_offsets).
# Label: contract (BB-PT-ADJ-03 also regression for the Asr clamp).
# ---------------------------------------------------------------------------


def test_adjustments_plus_ten_shifts_all_by_ten():
    # BB-PT-ADJ-01. Source: test_offsets (Raleigh 2015-12-01, MWL).
    method = CalculationMethod.MUSLIM_WORLD_LEAGUE
    base = PrayerTimes(
        RALEIGH,
        DateComponents(2015, 12, 1),
        calculation_parameters=CalculationParameters(method=method),
    )
    shifted_params = CalculationParameters(method=method)
    for name in PRAYER_ATTRS:
        setattr(shifted_params.adjustments, name, 10)
    shifted = PrayerTimes(
        RALEIGH, DateComponents(2015, 12, 1), calculation_parameters=shifted_params
    )
    for name in PRAYER_ATTRS:
        delta = (getattr(shifted, name) - getattr(base, name)).total_seconds() / 60
        assert delta == 10.0, name


def test_adjustments_negative_shifts_back():
    # BB-PT-ADJ-02. Oracle: exact shift arithmetic (symmetric to BB-PT-ADJ-01).
    method = CalculationMethod.MUSLIM_WORLD_LEAGUE
    base = PrayerTimes(
        RALEIGH,
        DateComponents(2015, 12, 1),
        calculation_parameters=CalculationParameters(method=method),
    )
    params = CalculationParameters(method=method)
    params.adjustments.fajr = -15
    params.adjustments.isha = -15
    shifted = PrayerTimes(
        RALEIGH, DateComponents(2015, 12, 1), calculation_parameters=params
    )
    assert (shifted.fajr - base.fajr).total_seconds() / 60 == -15.0
    assert (shifted.isha - base.isha).total_seconds() / 60 == -15.0
    assert _ordered(shifted)


def test_adjustments_extreme_dhuhr_saturates_asr():
    # BB-PT-ADJ-03. Source: test_extreme_adjustments_saturate_asr_to_dhuhr.
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.adjustments.dhuhr = 180
    pt = PrayerTimes(
        RALEIGH, DateComponents(2015, 12, 1), calculation_parameters=params
    )
    assert pt.asr == pt.dhuhr
    assert _ordered(pt)


# ---------------------------------------------------------------------------
# BB-PT-ISHA-01: isha_interval contract (Umm al-Qura: Maghrib + 90 min).
# Oracle: exact duration (test_prayer_times_with_method_with_isha_interval).
# Label: contract.
# ---------------------------------------------------------------------------


def test_isha_interval_equals_maghrib_plus_interval():
    params = CalculationParameters(method=CalculationMethod.UMM_AL_QURA)
    pt = PrayerTimes(
        (21.422510, 39.826168),
        DateComponents(2022, 8, 8),
        calculation_parameters=params,
    )
    assert (pt.isha - pt.maghrib).total_seconds() / 60 == params.isha_interval == 90


# ---------------------------------------------------------------------------
# BB-PT-TZ-*: timezone behavior. Oracle: contract matcher (UTC-aware by
# default) + golden conversion (test_prayer_times_timezone_conversion).
# Label: contract.
# ---------------------------------------------------------------------------


def test_default_times_are_utc_aware():
    # BB-PT-TZ-01.
    pt = PrayerTimes(RALEIGH, MID_DATE, CalculationMethod.MUSLIM_WORLD_LEAGUE)
    assert _all_utc(pt)
    assert pt.fajr.utcoffset() == timedelta(0)


def test_timezone_conversion_london_winter_summer():
    # BB-PT-TZ-02. Source: test_prayer_times_timezone_conversion.
    tz = ZoneInfo("Europe/London")
    coords = (51.49799827422162, -0.1358135027951458)
    method = CalculationMethod.MOON_SIGHTING_COMMITTEE
    fmt = "%I:%M %p"
    winter = PrayerTimes(
        coords, DateComponents(2022, 1, 1), calculation_method=method, time_zone=tz
    )
    assert winter.fajr.strftime(fmt) == "06:25 AM"
    summer_utc = PrayerTimes(
        coords, DateComponents(2022, 8, 1), calculation_method=method
    )
    assert summer_utc.fajr.strftime(fmt) == "02:37 AM"
    summer_local = PrayerTimes(
        coords, DateComponents(2022, 8, 1), calculation_method=method, time_zone=tz
    )
    assert summer_local.fajr.strftime(fmt) == "03:37 AM"


# ---------------------------------------------------------------------------
# BB-PT-TIMEFOR-*: Prayer enum dispatch. Oracle: contract matcher + stable
# error. Label: contract.
# ---------------------------------------------------------------------------


def test_time_for_prayer_matches_attributes():
    # BB-PT-TIMEFOR-01. Source: test_time_for_prayer_matches_attributes.
    pt = PrayerTimes(
        RALEIGH,
        DateComponents(2015, 7, 12),
        calculation_parameters=CalculationParameters(
            method=CalculationMethod.NORTH_AMERICA
        ),
    )
    for prayer, name in [
        (Prayer.IMSAK, "imsak"),
        (Prayer.FAJR, "fajr"),
        (Prayer.SUNRISE, "sunrise"),
        (Prayer.SYURUK, "syuruk"),
        (Prayer.ISHRAQ, "ishraq"),
        (Prayer.DHUHA, "dhuha"),
        (Prayer.DHUHR, "dhuhr"),
        (Prayer.ASR, "asr"),
        (Prayer.MAGHRIB, "maghrib"),
        (Prayer.ISHA, "isha"),
    ]:
        assert pt.time_for_prayer(prayer) == getattr(pt, name)


def test_time_for_prayer_rejects_none():
    # BB-PT-TIMEFOR-02. Source: test_time_for_prayer_rejects_none.
    pt = PrayerTimes(
        RALEIGH, DateComponents(2015, 7, 12), CalculationMethod.NORTH_AMERICA
    )
    with pytest.raises(ConfigurationError, match="(?i)prayer"):
        pt.time_for_prayer(Prayer.NONE)


# ---------------------------------------------------------------------------
# BB-PT-CFG-*: configuration errors. Oracle: stable error type + message
# fragment. Label: contract.
# ---------------------------------------------------------------------------


def test_both_method_and_params_raises():
    # BB-PT-CFG-01.
    with pytest.raises(ConfigurationError, match="Only one of"):
        PrayerTimes(
            RALEIGH,
            DateComponents(2015, 7, 12),
            CalculationMethod.NORTH_AMERICA,
            CalculationParameters(method=CalculationMethod.NORTH_AMERICA),
        )


def test_neither_method_nor_params_raises():
    # BB-PT-CFG-02.
    with pytest.raises(ConfigurationError, match="Only one of"):
        PrayerTimes(RALEIGH, DateComponents(2015, 7, 12))


def test_invalid_madhab_raises_configuration_error():
    # BB-PT-CFG-03. Source: test_invalid_madhab_raises_configuration_error.
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.madhab = None
    with pytest.raises(ConfigurationError, match="(?i)madhab"):
        PrayerTimes(RALEIGH, DateComponents(2015, 7, 12), calculation_parameters=params)


def test_invalid_high_latitude_rule_raises():
    # BB-PT-CFG-04. Oracle: stable ConfigurationError for unknown rule.
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.high_latitude_rule = "bogus"
    with pytest.raises(ConfigurationError, match="(?i)high latitude"):
        PrayerTimes(RALEIGH, DateComponents(2015, 7, 12), calculation_parameters=params)


def test_invalid_polar_rule_raises():
    # BB-PT-CFG-05. Covers construction-time and compute-time rejection.
    with pytest.raises(ConfigurationError, match="(?i)polar"):
        CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE, polar_circle_rule="bogus"
        )
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.polar_circle_rule = "bogus"
    with pytest.raises(ConfigurationError, match="(?i)polar"):
        PrayerTimes(TROMSO, WINTER_TROMSO, calculation_parameters=params)


# ---------------------------------------------------------------------------
# BB-PT-VAL-*: validation errors. Oracle: stable ValidationError + fragment.
# Label: contract (except BB-PT-VAL-03, suspicious current behavior).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("coords", [(91, 0), (0, 181)], ids=["lat-91", "lon-181"])
def test_out_of_range_coordinates_rejected(coords):
    # BB-PT-VAL-01. Source: test_out_of_range_tuple_rejected_by_prayer_times.
    with pytest.raises(ValidationError, match="(?i)latitude|longitude"):
        PrayerTimes(
            coords, DateComponents(2015, 7, 12), CalculationMethod.MUSLIM_WORLD_LEAGUE
        )


@pytest.mark.parametrize(
    "kwargs",
    [{"fajr_angle": 91}, {"isha_angle": -1}, {"isha_interval": -5}],
    ids=["fajr-91", "isha-minus-1", "interval-minus-5"],
)
def test_out_of_range_parameters_rejected(kwargs):
    # BB-PT-VAL-02. Source: test_out_of_range_parameters_rejected.
    with pytest.raises(ValidationError, match="(?i)angle|interval"):
        CalculationParameters(**kwargs)


def test_non_numeric_coordinates_raise_alfalak_error():
    # BB-PT-VAL-03. Oracle: ARCHITECTURE.md promises all errors are
    # AlFalakError subclasses; non-numeric input must not leak bare TypeError.
    # Label: suspicious current behavior (minimized reproducer; see report).
    with pytest.raises(AlFalakError, match="(?i)real number"):
        PrayerTimes(
            ("a", "b"),
            DateComponents(2015, 7, 12),
            CalculationMethod.MUSLIM_WORLD_LEAGUE,
        )


# ---------------------------------------------------------------------------
# BB-PT-INPUT-*: accepted input shapes. Oracle: equivalence (tuple ==
# Coordinates object; datetime == DateComponents). Label: contract.
# ---------------------------------------------------------------------------


def test_coordinates_object_equivalent_to_tuple():
    # BB-PT-INPUT-01. Source: test_prayer_times_accepts_coordinates_object.
    params = lambda: CalculationParameters(  # noqa: E731
        method=CalculationMethod.NORTH_AMERICA
    )  # noqa: E731
    from_tuple = PrayerTimes(
        RALEIGH, DateComponents(2015, 7, 12), calculation_parameters=params()
    )
    from_object = PrayerTimes(
        Coordinates(*RALEIGH),
        DateComponents(2015, 7, 12),
        calculation_parameters=params(),
    )
    assert from_object.fajr == from_tuple.fajr
    assert from_object.isha == from_tuple.isha


def test_datetime_equivalent_to_date_components():
    # BB-PT-INPUT-02. Source: test_prayer_times_accepts_datetime_and_date_components.
    params = lambda: CalculationParameters(  # noqa: E731
        method=CalculationMethod.NORTH_AMERICA
    )  # noqa: E731
    from_datetime = PrayerTimes(
        RALEIGH,
        datetime(2015, 7, 12, tzinfo=timezone.utc),
        calculation_parameters=params(),
    )
    from_components = PrayerTimes(
        RALEIGH, DateComponents(2015, 7, 12), calculation_parameters=params()
    )
    assert from_components.fajr == from_datetime.fajr
    assert from_components.isha == from_datetime.isha


# ---------------------------------------------------------------------------
# BB-QIBLA-*: Qibla bearings. Oracle: reviewed goldens (test_qibla.py,
# cross-checked against published bearings/WGS84) + [0, 360) matcher.
# Label: contract (BB-QIBLA-SELF is characterization).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lat, lon, expected",
    [
        (35.7750, -78.6336, 55.825),
        (40.7128, -74.0060, 58.482),
        (51.5074, -0.1278, 118.987),
        (30.0444, 31.2357, 136.137),
        (3.1390, 101.6869, 292.538),
        (-6.2088, 106.8456, 295.152),
        (-33.8688, 151.2093, 277.500),
    ],
    ids=["raleigh", "new-york", "london", "cairo", "kuala-lumpur", "jakarta", "sydney"],
)
def test_qibla_bearings(lat, lon, expected):
    # BB-QIBLA-01..07.
    assert Qibla((lat, lon)).direction == pytest.approx(expected, abs=1e-2)
    assert Qibla(Coordinates(lat, lon)).direction == pytest.approx(expected, abs=1e-2)


def test_qibla_at_makkah_self_characterization():
    # BB-QIBLA-SELF-01. Oracle: characterization — bearing from Makkah to
    # itself is degenerate (atan2(0, ~0)); observed 180.0 on 2026-09-29.
    # Any direction is defensible; the contract is only that a float in
    # [0, 360) is returned without raising.
    direction = Qibla((MAKKAH.latitude, MAKKAH.longitude)).direction
    assert direction == pytest.approx(180.0, abs=1e-6)
    assert 0 <= direction < 360


@pytest.mark.parametrize(
    "coords",
    [(0, 0), (90, 0), (-90, 0), (0, 180)],
    ids=["equator-prime", "north-pole", "south-pole", "antimeridian"],
)
def test_qibla_cardinal_points_in_range(coords):
    # BB-QIBLA-EDGE-01..04. Oracle: [0, 360) range matcher.
    assert 0 <= Qibla(coords).direction < 360


# ---------------------------------------------------------------------------
# BB-SUNNAH-*: SunnahTimes(prayer_times). Oracle: reviewed goldens
# (test_sunnah_times.py) + ordering invariant. Label: contract.
# ---------------------------------------------------------------------------


def _mw_l_raleigh_mid_july():
    return PrayerTimes(
        RALEIGH, DateComponents(2015, 7, 12), CalculationMethod.MUSLIM_WORLD_LEAGUE
    )


def test_sunnah_middle_and_last_third_golden():
    # BB-SUNNAH-01. Source: test_sunnah_times.
    sunnah = SunnahTimes(_mw_l_raleigh_mid_july())
    assert sunnah.middle_of_the_night == datetime(
        2015, 7, 13, 4, 28, tzinfo=timezone.utc
    )
    assert sunnah.last_third_of_the_night == datetime(
        2015, 7, 13, 5, 46, tzinfo=timezone.utc
    )


def test_sunnah_night_markers_ordered():
    # BB-SUNNAH-02. Source: test_sunnah_times_ordering (public seam only:
    # tomorrow rebuilt from a public datetime, no _prayer_date access).
    pt = _mw_l_raleigh_mid_july()
    sunnah = SunnahTimes(pt)
    tomorrow = PrayerTimes(
        RALEIGH,
        datetime(2015, 7, 13, tzinfo=timezone.utc),
        CalculationMethod.MUSLIM_WORLD_LEAGUE,
    )
    assert pt.maghrib < sunnah.middle_of_the_night
    assert sunnah.middle_of_the_night < sunnah.last_third_of_the_night
    assert sunnah.last_third_of_the_night < tomorrow.fajr


def test_sunnah_across_dst_transition():
    # BB-SUNNAH-03. Source: test_sunnah_times_across_dst_transition.
    tz = ZoneInfo("America/New_York")
    pt = PrayerTimes(
        RALEIGH,
        DateComponents(2015, 3, 7),
        CalculationMethod.MUSLIM_WORLD_LEAGUE,
        time_zone=tz,
    )
    sunnah = SunnahTimes(pt)
    assert sunnah.middle_of_the_night == datetime(2015, 3, 7, 23, 43, tzinfo=tz)
    assert sunnah.last_third_of_the_night == datetime(2015, 3, 8, 1, 32, tzinfo=tz)


# ---------------------------------------------------------------------------
# BB-CLI-*: CLI consumer workflow. Oracle: exact stdout goldens (test_cli.py)
# + argparse exit-status contract (2 = usage error). Label: contract
# (BB-CLI-07 is characterization: domain-error exit mapping is unspecified).
# ---------------------------------------------------------------------------


def test_cli_happy_path_prints_iso_times(capsys):
    # BB-CLI-01. Source: test_cli_prints_iso_times.
    main(
        [
            "prayer",
            "--latitude",
            "35.7750",
            "--longitude",
            "-78.6336",
            "--date",
            "2015-07-12",
            "--method",
            "NORTH_AMERICA",
        ]
    )
    lines = dict(
        line.split("=", 1) for line in capsys.readouterr().out.strip().splitlines()
    )
    assert set(lines) == {
        "imsak",
        "fajr",
        "sunrise",
        "syuruk",
        "ishraq",
        "dhuha",
        "dhuhr",
        "asr",
        "maghrib",
        "isha",
    }
    assert lines["fajr"] == "2015-07-12T08:42:00+00:00"
    for value in lines.values():  # every line parses as an aware ISO datetime
        assert datetime.fromisoformat(value).tzinfo is not None


def test_cli_module_entry_point_subprocess():
    # BB-CLI-02. Source: test_cli_module_entry_point. Adapter: subprocess with
    # arg array (no shell), explicit timeout; ambient interpreter/PYTHONPATH
    # per project-native convention (see evidence report).
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alfalak",
            "prayer",
            "--latitude",
            "35",
            "--longitude",
            "-78",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "fajr=" in result.stdout


@pytest.mark.parametrize(
    "argv",
    [
        ["prayer", "--latitude", "35", "--longitude", "-78", "--method", "BOGUS"],
        ["prayer", "--latitude", "35", "--longitude", "-78", "--date", "not-a-date"],
        [
            "prayer",
            "--latitude",
            "35",
            "--longitude",
            "-78",
            "--date",
            "2015-07-12T00:00:00",
        ],
        ["prayer", "--latitude", "35"],
    ],
    ids=["unknown-method", "bad-date", "datetime-date", "missing-coords"],
)
def test_cli_rejects_bad_arguments(argv):
    # BB-CLI-03..06. Oracle: argparse usage-error exit status 2.
    with pytest.raises(SystemExit) as excinfo:
        main(argv)
    assert excinfo.value.code == 2


def test_cli_domain_error_characterization():
    # BB-CLI-07. Oracle: characterization — out-of-range latitude raises the
    # public ValidationError inside the CLI, which the CLI maps to a usage
    # error (exit 2) with the message on stderr (no traceback).
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alfalak",
            "prayer",
            "--latitude",
            "91",
            "--longitude",
            "0",
            "--date",
            "2015-07-12",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 2
    assert "Latitude" in result.stderr


# ---------------------------------------------------------------------------
# BB-HIJRI-*: Hijri public seam (phase 5 task 6). Oracle: reviewed anchors
# (tests/calendar/test_tabular.py) + factory error contract
# (HijriCalendar.get_calendar) + CLI two-line contract. Label: contract.
# ---------------------------------------------------------------------------


def test_hijri_root_exports_resolve():
    # BB-HIJRI-01. The eight Hijri names are importable from the root and
    # listed in __all__.
    import alfalak

    assert alfalak.HijriDate is HijriDate
    assert alfalak.HijriCalendar is HijriCalendar
    assert alfalak.TabularCalendar is TabularCalendar
    assert alfalak.UmmAlQuraCalendar is UmmAlQuraCalendar
    assert alfalak.MabimsCalendar is MabimsCalendar
    assert alfalak.OffsetStore is OffsetStore
    assert alfalak.gregorian_to_hijri is gregorian_to_hijri
    assert alfalak.get_calendar is get_calendar
    for name in (
        "HijriDate",
        "HijriCalendar",
        "TabularCalendar",
        "UmmAlQuraCalendar",
        "MabimsCalendar",
        "OffsetStore",
        "gregorian_to_hijri",
        "get_calendar",
    ):
        assert name in alfalak.__all__, name


def test_hijri_tabular_anchor_via_bridge():
    # BB-HIJRI-02. Source: test_tabular_ramadan_1446_anchor_is_tabular_value.
    hijri = gregorian_to_hijri(
        datetime(2025, 3, 1, tzinfo=timezone.utc), calendar=TabularCalendar()
    )
    assert hijri == HijriDate(1446, 9, 1)


def test_hijri_factory_rejects_misuse():
    # BB-HIJRI-03. Oracle: get_calendar ConfigurationError contract.
    with pytest.raises(ConfigurationError):
        get_calendar("bogus")
    with pytest.raises(ConfigurationError, match="(?i)country"):
        get_calendar("mabims")
    with pytest.raises(ConfigurationError, match="(?i)country"):
        get_calendar("tabular", country="MY")
    with pytest.raises(ConfigurationError, match="(?i)adjustment"):
        get_calendar("uqu", adjustment_days=1)


def test_hijri_cli_subprocess_two_lines():
    # BB-HIJRI-04. Oracle: CLI two-line contract (hijri=/calendar=).
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alfalak",
            "hijri",
            "--date",
            "2025-03-01",
            "--calendar",
            "tabular",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert result.stdout == "hijri=1446-09-01\ncalendar=tabular\n"
