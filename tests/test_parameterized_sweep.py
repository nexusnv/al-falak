"""Parameterized sweep (deterministic, stdlib-only fallback; promoted to the
permanent suite).

Boundary: PrayerTimes / Coordinates / CalculationParameters / Qibla /
SunnahTimes (public API in src/alfalak/__init__.py).
Seed: 20260929. Generator: random.Random (no Hypothesis in project deps;
reduced guarantees: finite witnesses, manual minimization only).
Budgets: <=200 cases total, <120s wall time, input scalars only.
Shared ordering helper lives in tests/support.py.
"""

import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from alfalak import (
    CalculationMethod,
    CalculationParameters,
    Coordinates,
    HighLatitudeRule,
    HijriDate,
    Madhab,
    PolarCircleRule,
    PrayerAdjustments,
    PrayerTimes,
    Qibla,
    SunnahTimes,
    TabularCalendar,
    ValidationError,
    get_calendar,
    gregorian_to_hijri,
)
from alfalak.calculation.MethodsParameters import METHODS_PARAMETERS
from alfalak.exceptions import AstronomicalError, ConfigurationError
from alfalak.util.DateComponents import DateComponents

SEED = 20260929

ALL_METHODS = list(CalculationMethod)
# CalculationMethod.NONE is a degenerate zero-angle/zero-interval config, not a
# real-world method: its fajr uses horizon-depression 0 while sunrise uses the
# -0.833 deg solar-altitude convention (SolarTime solar_altitude = -50/60), so
# fajr lands AFTER sunrise and isha lands BEFORE maghrib. P1/P2/P3/P6 generated
# batteries therefore quantify over documented methods only (recorded narrowing;
# NONE is covered by a dedicated characterization test instead).
REAL_METHODS = [m for m in ALL_METHODS if m != CalculationMethod.NONE]
ALL_HIGH_LAT = list(HighLatitudeRule)
ALL_POLAR = list(PolarCircleRule)

DATE_POOL = [
    DateComponents(2015, 7, 12),  # Raleigh golden date
    DateComponents(2024, 2, 29),  # leap day
    DateComponents(2024, 3, 20),  # March equinox
    DateComponents(2024, 6, 21),  # June solstice
    DateComponents(2024, 12, 21),  # December solstice
    DateComponents(2024, 3, 10),  # US DST spring forward
    DateComponents(2024, 11, 3),  # US DST fall back
    DateComponents(2024, 3, 31),  # EU DST spring forward
]

LAT_POOL = [-90.0, -66.5, -65.0, -33.8688, 0.0, 35.7750, 59.9094, 65.0, 66.5, 90.0]
LON_POOL = [-180.0, -78.6336, -0.1278, 0.0, 39.826168, 106.8456, 151.2093, 180.0]

PRAYER_ATTRS = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]


def make_params(
    method,
    madhab=Madhab.SHAFI,
    high_lat=HighLatitudeRule.MIDDLE_OF_THE_NIGHT,
    polar=PolarCircleRule.NEAREST_LATITUDE,
):
    p = CalculationParameters(method=method)
    p.madhab = madhab
    p.high_latitude_rule = high_lat
    p.polar_circle_rule = polar
    return p


def ordered_times(pt):
    return [getattr(pt, name) for name in PRAYER_ATTRS]


# ---------------------------------------------------------------------------
# Fixed examples (curated goldens from tests/test_prayer_times.py + README)
# ---------------------------------------------------------------------------


class TestFixedGoldens:
    """Domain: valid. Oracle: exact reviewed golden output."""

    def test_raleigh_second_precision(self):
        # Golden from test_prayer_times_second_precision_locked.
        date = DateComponents(2015, 7, 12)
        params = CalculationParameters(method=CalculationMethod.NORTH_AMERICA)
        params.madhab = Madhab.HANAFI
        pt = PrayerTimes((35.7750, -78.6336), date, calculation_parameters=params)
        assert pt.fajr.strftime("%H:%M:%S") == "08:42:00"
        assert pt.sunrise.strftime("%H:%M:%S") == "10:08:00"
        assert pt.dhuhr.strftime("%H:%M:%S") == "17:21:00"
        assert pt.asr.strftime("%H:%M:%S") == "22:22:00"
        assert pt.maghrib.strftime("%H:%M:%S") == "00:32:00"
        assert pt.isha.strftime("%H:%M:%S") == "01:57:00"

    def test_offsets_shift_exactly(self):
        # Golden from test_offsets (+10 min each prayer).
        date = DateComponents(2015, 12, 1)
        coords = (35.7750, -78.6336)
        base = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
        shifted = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
        shifted.adjustments = PrayerAdjustments(
            fajr=10, sunrise=10, dhuhr=10, asr=10, maghrib=10, isha=10
        )
        pt0 = PrayerTimes(coords, date, calculation_parameters=base)
        pt1 = PrayerTimes(coords, date, calculation_parameters=shifted)
        for name in PRAYER_ATTRS:
            assert getattr(pt1, name) - getattr(pt0, name) == timedelta(
                minutes=10
            ), name

    def test_oslo_moon_sighting_high_lat(self):
        params = CalculationParameters(method=CalculationMethod.MOON_SIGHTING_COMMITTEE)
        params.madhab = Madhab.HANAFI
        pt = PrayerTimes(
            (59.9094, 10.7349),
            DateComponents(2016, 1, 1),
            calculation_parameters=params,
        )
        tz = ZoneInfo("Europe/Oslo")
        assert pt.fajr.astimezone(tz).strftime("%I:%M %p") == "07:34 AM"
        assert pt.isha.astimezone(tz).strftime("%I:%M %p") == "05:02 PM"

    def test_umm_al_qura_isha_interval(self):
        params = CalculationParameters(method=CalculationMethod.UMM_AL_QURA)
        pt = PrayerTimes(
            (21.422510, 39.826168),
            DateComponents(2022, 8, 8),
            calculation_parameters=params,
        )
        assert (pt.isha - pt.maghrib).total_seconds() / 60 == params.isha_interval

    def test_zero_angle_ordering_characterization(self):
        # CHARACTERIZATION (open question, not a contract claim): with
        # fajr/isha angles of 0, PrayerTimes computes fajr at horizon
        # depression 0 but sunrise at the -0.833 deg solar-altitude
        # convention, so fajr lands AFTER sunrise; symmetrically isha lands
        # BEFORE maghrib. P1 therefore excludes the zero-angle config.
        params = CalculationParameters(fajr_angle=0.0, isha_angle=0.0)
        pt = PrayerTimes(
            (35.7750, -78.6336),
            DateComponents(2015, 7, 12),
            calculation_parameters=params,
        )
        assert pt.fajr.strftime("%H:%M") == "10:13"
        assert pt.sunrise.strftime("%H:%M") == "10:08"
        assert pt.fajr > pt.sunrise
        assert pt.isha < pt.maghrib

    def test_sunnah_golden(self):
        pt = PrayerTimes(
            (35.7750, -78.6336),
            DateComponents(2015, 7, 12),
            CalculationMethod.MUSLIM_WORLD_LEAGUE,
        )
        st = SunnahTimes(pt)
        assert st.middle_of_the_night == datetime(
            2015, 7, 13, 4, 28, tzinfo=timezone.utc
        )
        assert st.last_third_of_the_night == datetime(
            2015, 7, 13, 5, 46, tzinfo=timezone.utc
        )

    def test_sunnah_dst_transition(self):
        tz = ZoneInfo("America/New_York")
        pt = PrayerTimes(
            (35.7750, -78.6336),
            DateComponents(2015, 3, 7),
            CalculationMethod.MUSLIM_WORLD_LEAGUE,
            time_zone=tz,
        )
        st = SunnahTimes(pt)
        assert st.middle_of_the_night == datetime(2015, 3, 7, 23, 43, tzinfo=tz)
        assert st.last_third_of_the_night == datetime(2015, 3, 8, 1, 32, tzinfo=tz)


QIBLA_GOLDENS = [
    (35.7750, -78.6336, 55.825),
    (40.7128, -74.0060, 58.482),
    (51.5074, -0.1278, 118.987),
    (30.0444, 31.2357, 136.137),
    (3.1390, 101.6869, 292.538),
    (-6.2088, 106.8456, 295.152),
    (-33.8688, 151.2093, 277.500),
]


@pytest.mark.parametrize("lat,lon,expected", QIBLA_GOLDENS)
def test_qibla_goldens(lat, lon, expected):
    """Domain: valid. Oracle: reviewed golden bearings (abs tol 1e-2)."""
    assert Qibla((lat, lon)).direction == pytest.approx(expected, abs=1e-2)


class TestFixedRejections:
    """Domains: invalid / unsupported. Oracle: documented stable error."""

    def test_polar_night_none_raises(self):
        params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
        params.polar_circle_rule = PolarCircleRule.NONE
        with pytest.raises(AstronomicalError, match="(?i)polar"):
            PrayerTimes(
                (68.35, 18.83),
                DateComponents(2015, 12, 21),
                calculation_parameters=params,
            )

    def test_both_method_and_params_raises(self):
        with pytest.raises(ConfigurationError, match="Only one of"):
            PrayerTimes(
                DateComponents(2015, 7, 12) and (35.7750, -78.6336),
                DateComponents(2015, 7, 12),
                CalculationMethod.NORTH_AMERICA,
                CalculationParameters(method=CalculationMethod.NORTH_AMERICA),
            )

    def test_none_madhab_raises(self):
        params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
        params.madhab = None
        with pytest.raises(ConfigurationError, match="(?i)madhab"):
            PrayerTimes(
                (35.7750, -78.6336),
                DateComponents(2015, 7, 12),
                calculation_parameters=params,
            )

    @pytest.mark.parametrize(
        "lat,lon", [(90.1, 0), (-90.1, 0), (0, 180.1), (0, -180.1)]
    )
    def test_out_of_range_coords_rejected(self, lat, lon):
        with pytest.raises(ValidationError, match="(?i)latitude|longitude"):
            Coordinates(lat, lon)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"fajr_angle": -1},
            {"fajr_angle": 91},
            {"isha_angle": -1},
            {"isha_angle": 91},
            {"isha_interval": -5},
        ],
    )
    def test_out_of_range_params_rejected(self, kwargs):
        with pytest.raises(ValidationError, match="(?i)angle|interval"):
            CalculationParameters(**kwargs)


# ---------------------------------------------------------------------------
# Generated witnesses (seeded, bounded)
# ---------------------------------------------------------------------------


def gen_ordering_cases(n=48):
    rng = random.Random(SEED)
    cases = []
    for i in range(n):
        lat = rng.choice(LAT_POOL) if i % 3 else rng.uniform(-66.0, 66.0)
        lon = rng.choice(LON_POOL) if i % 3 else rng.uniform(-180.0, 180.0)
        method = REAL_METHODS[i % len(REAL_METHODS)]
        madhab = Madhab.HANAFI if i % 2 else Madhab.SHAFI
        high_lat = ALL_HIGH_LAT[(i // 2) % len(ALL_HIGH_LAT)]
        date = DATE_POOL[i % len(DATE_POOL)]
        cases.append((f"G-ORD-{i:03d}", lat, lon, method, madhab, high_lat, date))
    return cases


class TestGeneratedOrdering:
    """Property P1: fajr<=sunrise<=dhuhr<=asr<=maghrib<=isha for valid
    non-polar-resolved inputs with zero adjustments; outputs UTC minute-aligned."""

    @pytest.mark.parametrize(
        "case_id,lat,lon,method,madhab,high_lat,date", gen_ordering_cases()
    )
    def test_ordering(self, case_id, lat, lon, method, madhab, high_lat, date):
        pt = PrayerTimes(
            (lat, lon),
            date,
            calculation_parameters=make_params(method, madhab, high_lat),
        )
        times = ordered_times(pt)
        assert times == sorted(times), case_id
        for t in times:
            assert t.tzinfo == timezone.utc, case_id
            assert t.second == 0 and t.microsecond == 0, case_id


def gen_madhab_cases(n=20):
    rng = random.Random(SEED + 1)
    cases = []
    for i in range(n):
        lat = rng.uniform(-60.0, 60.0)
        lon = rng.uniform(-180.0, 180.0)
        method = rng.choice(REAL_METHODS)
        date = rng.choice(DATE_POOL)
        cases.append((f"G-MAD-{i:03d}", lat, lon, method, date))
    return cases


class TestGeneratedMadhab:
    """Property P2 (metamorphic): Hanafi Asr >= Shafi Asr, all else equal."""

    @pytest.mark.parametrize("case_id,lat,lon,method,date", gen_madhab_cases())
    def test_hanafi_asr_not_earlier(self, case_id, lat, lon, method, date):
        asr_s = PrayerTimes(
            (lat, lon), date, calculation_parameters=make_params(method, Madhab.SHAFI)
        ).asr
        asr_h = PrayerTimes(
            (lat, lon), date, calculation_parameters=make_params(method, Madhab.HANAFI)
        ).asr
        assert asr_h >= asr_s, case_id


def gen_adjustment_cases(n=20):
    rng = random.Random(SEED + 2)
    cases = []
    for i in range(n):
        lat = rng.uniform(-60.0, 60.0)
        lon = rng.uniform(-180.0, 180.0)
        method = rng.choice(
            [m for m in REAL_METHODS if m != CalculationMethod.MOON_SIGHTING_COMMITTEE]
        )
        prayer = PRAYER_ATTRS[i % len(PRAYER_ATTRS)]
        delta = rng.choice([d for d in range(-60, 61) if d != 0])
        date = rng.choice(DATE_POOL)
        cases.append((f"G-ADJ-{i:03d}", lat, lon, method, prayer, delta, date))
    return cases


class TestGeneratedAdjustments:
    """Property P3 (metamorphic): adjusting prayer X by k minutes shifts X by
    exactly k minutes and leaves the other five prayers unchanged."""

    @pytest.mark.parametrize(
        "case_id,lat,lon,method,prayer,delta,date", gen_adjustment_cases()
    )
    def test_single_adjustment_exact(
        self, case_id, lat, lon, method, prayer, delta, date
    ):
        pt0 = PrayerTimes((lat, lon), date, calculation_parameters=make_params(method))
        adj = PrayerAdjustments(**{prayer: delta})
        changed = make_params(method)
        changed.adjustments = adj
        pt1 = PrayerTimes((lat, lon), date, calculation_parameters=changed)
        for name in PRAYER_ATTRS:
            diff = getattr(pt1, name) - getattr(pt0, name)
            if name == prayer:
                assert diff == timedelta(minutes=delta), (case_id, name)
            else:
                assert diff == timedelta(0), (case_id, name)


def gen_qibla_cases(n=24):
    rng = random.Random(SEED + 3)
    cases = []
    for i in range(n):
        if i % 4 == 0:
            lat = rng.choice([-90.0, -66.5, 0.0, 66.5, 90.0])
            lon = rng.choice([-180.0, 0.0, 180.0])
        else:
            lat = rng.uniform(-90.0, 90.0)
            lon = rng.uniform(-180.0, 180.0)
        cases.append((f"G-QIB-{i:03d}", lat, lon))
    return cases


class TestGeneratedQibla:
    """Property P5 (invariant): Qibla direction in [0, 360)."""

    @pytest.mark.parametrize("case_id,lat,lon", gen_qibla_cases())
    def test_qibla_in_range(self, case_id, lat, lon):
        d = Qibla((lat, lon)).direction
        assert 0.0 <= d < 360.0, case_id

    def test_qibla_accepts_coordinates_object(self):
        assert Qibla(Coordinates(35.7750, -78.6336)).direction == pytest.approx(
            Qibla((35.7750, -78.6336)).direction
        )


def gen_sunnah_cases(n=16):
    rng = random.Random(SEED + 4)
    cases = []
    for i in range(n):
        lat = rng.uniform(-55.0, 55.0)
        lon = rng.uniform(-180.0, 180.0)
        method = rng.choice(REAL_METHODS)
        date = rng.choice(DATE_POOL)
        cases.append((f"G-SUN-{i:03d}", lat, lon, method, date))
    return cases


class TestGeneratedSunnah:
    """Property P6: maghrib < middle < last_third < tomorrow fajr, and
    (last_third - middle) == night/6 within minute-rounding tolerance."""

    @pytest.mark.parametrize("case_id,lat,lon,method,date", gen_sunnah_cases())
    def test_sunnah_derivation(self, case_id, lat, lon, method, date):
        pt = PrayerTimes((lat, lon), date, calculation_parameters=make_params(method))
        st = SunnahTimes(pt)
        tomorrow = PrayerTimes(
            (lat, lon),
            datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
            + timedelta(days=1),
            calculation_parameters=make_params(method),
        )
        assert pt.maghrib < st.middle_of_the_night, case_id
        assert st.middle_of_the_night < st.last_third_of_the_night, case_id
        assert st.last_third_of_the_night < tomorrow.fajr, case_id
        night = (tomorrow.fajr - pt.maghrib).total_seconds()
        gap = (st.last_third_of_the_night - st.middle_of_the_night).total_seconds()
        assert abs(gap - night / 6.0) <= 60.0, (case_id, gap, night)


def gen_polar_cases():
    cases = []
    i = 0
    for lat, lon in [(78.2232, 15.6267), (68.35, 18.83), (-77.85, 166.67), (90.0, 0.0)]:
        for date in [DateComponents(2024, 6, 21), DateComponents(2024, 12, 21)]:
            for rule in ALL_POLAR:
                # Exact-pole NEAREST_DAY is known-defect D1 (xfail below).
                if rule == PolarCircleRule.NEAREST_DAY and abs(lat) == 90.0:
                    continue
                cases.append((f"G-POL-{i:03d}", lat, lon, date, rule))
                i += 1
    return cases


class TestGeneratedPolar:
    """Env-dependent domain: polar day/night. Oracle: NONE -> AstronomicalError;
    resolution rules -> full ordering holds."""

    @pytest.mark.parametrize("case_id,lat,lon,date,rule", gen_polar_cases())
    def test_polar_rule_behavior(self, case_id, lat, lon, date, rule):
        params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
        params.polar_circle_rule = rule
        if rule == PolarCircleRule.NONE:
            with pytest.raises(AstronomicalError, match="(?i)polar"):
                PrayerTimes((lat, lon), date, calculation_parameters=params)
        else:
            pt = PrayerTimes((lat, lon), date, calculation_parameters=params)
            times = ordered_times(pt)
            assert times == sorted(times), case_id


INVALID_NUMERIC = [
    ("G-INV-000", 90.1, 0.0),
    ("G-INV-001", -90.1, 0.0),
    ("G-INV-002", 0.0, 180.1),
    ("G-INV-003", 0.0, -180.1),
    ("G-INV-004", 200.0, 400.0),
    ("G-INV-005", float("nan"), 0.0),
    ("G-INV-006", 0.0, float("nan")),
    ("G-INV-007", float("inf"), 0.0),
    ("G-INV-008", 0.0, float("-inf")),
]

INVALID_PARAMS = [
    ("G-INV-009", {"fajr_angle": -1}),
    ("G-INV-010", {"fajr_angle": 91}),
    ("G-INV-011", {"isha_angle": -1}),
    ("G-INV-012", {"isha_angle": 91}),
    ("G-INV-013", {"isha_interval": -5}),
    ("G-INV-014", {"fajr_angle": float("nan")}),
]

# Malformed (wrong-type) inputs: contract fixed — all raise ValidationError
# (AlFalakError), not builtin TypeError/ValueError.
MALFORMED = [
    ("G-MAL-000", ("35.7", "-78.6"), ValidationError),
    ("G-MAL-001", None, ValidationError),
    ("G-MAL-002", (35.0,), ValidationError),
    ("G-MAL-003", "35.775,-78.6336", ValidationError),
]


class TestGeneratedInvalid:
    """Property P4: numeric out-of-range -> ValidationError with no global
    state mutation (method templates + fresh-instance behavior unchanged)."""

    @pytest.mark.parametrize("case_id,lat,lon", INVALID_NUMERIC)
    def test_bad_coords_rejected(self, case_id, lat, lon):
        with pytest.raises(ValidationError, match="(?i)latitude|longitude"):
            Coordinates(lat, lon)
        with pytest.raises(ValidationError, match="(?i)latitude|longitude"):
            PrayerTimes(
                (lat, lon),
                DateComponents(2015, 7, 12),
                CalculationMethod.MUSLIM_WORLD_LEAGUE,
            )

    @pytest.mark.parametrize("case_id,kwargs", INVALID_PARAMS)
    def test_bad_params_rejected(self, case_id, kwargs):
        with pytest.raises(ValidationError, match="(?i)angle|interval"):
            CalculationParameters(**kwargs)

    @pytest.mark.parametrize("case_id,coords,exc", MALFORMED)
    def test_malformed_coords_characterization(self, case_id, coords, exc):
        # Contract: wrong-type input is rejected with ValidationError
        # (fixed F-VAL-03; previously builtin TypeError/ValueError leaked).
        with pytest.raises(exc, match="(?i)coordinates|real number"):
            PrayerTimes(
                coords,
                DateComponents(2015, 7, 12),
                CalculationMethod.MUSLIM_WORLD_LEAGUE,
            )

    def test_no_state_mutation_after_rejections(self):
        def snapshot():
            snap = {}
            for m in ALL_METHODS:
                p = CalculationParameters(method=m)
                snap[m] = (
                    p.fajr_angle,
                    p.isha_angle,
                    p.isha_interval,
                    p.madhab,
                    p.high_latitude_rule,
                    p.polar_circle_rule,
                    tuple(sorted(vars(p.method_adjustments).items())),
                    tuple(sorted(vars(p.adjustments).items())),
                )
            return snap

        def template_snapshot():
            snap = {}
            for m, d in METHODS_PARAMETERS.items():
                snap[m] = tuple(
                    sorted(
                        (
                            k,
                            (
                                getattr(v, "fajr", v)
                                if not hasattr(v, "__dict__")
                                else tuple(sorted(vars(v).items()))
                            ),
                        )
                        for k, v in d.items()
                    )
                )
            return snap

        before, before_tpl = snapshot(), template_snapshot()
        for _, lat, lon in INVALID_NUMERIC:
            try:
                Coordinates(lat, lon)
            except ValidationError:
                pass
        for _, kwargs in INVALID_PARAMS:
            try:
                CalculationParameters(**kwargs)
            except ValidationError:
                pass
        after, after_tpl = snapshot(), template_snapshot()
        assert before == after
        assert before_tpl == after_tpl

        # Fresh instances behave identically before/after the rejection storm.
        def mk() -> PrayerTimes:
            return PrayerTimes(
                (35.7750, -78.6336),
                DateComponents(2015, 7, 12),
                CalculationMethod.MUSLIM_WORLD_LEAGUE,
            )

        assert ordered_times(mk()) == ordered_times(mk())


@pytest.mark.parametrize("lat", [90.0, -90.0])
@pytest.mark.parametrize(
    "date", [DateComponents(2024, 6, 21), DateComponents(2024, 12, 21)]
)
def test_nearest_day_exact_pole_known_defect(lat, date):
    """D1 documented limitation: exact pole + NEAREST_DAY has no numerically
    valid date (cos-latitude singularity). Must raise AstronomicalError with
    actionable message (use NEAREST_LATITUDE/MAKKAH instead)."""
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.polar_circle_rule = PolarCircleRule.NEAREST_DAY
    with pytest.raises(AstronomicalError, match="(?i)exact.*pole|NEAREST_LATITUDE"):
        PrayerTimes((lat, 0.0), date, calculation_parameters=params)


def test_asr_spill_past_maghrib_known_defect():
    """D2 regression (fixed): near the polar boundary the shadow-length hour
    angle spilled past sunset (asr 22:12 > maghrib 21:22 on 2024-03-19 at
    89.1N). Asr now saturates to Maghrib, mirroring the Asr<Dhuhr clamp."""
    pt = PrayerTimes(
        (89.1, 0.0), DateComponents(2024, 3, 19), CalculationMethod.MUSLIM_WORLD_LEAGUE
    )
    assert pt.asr == pt.maghrib
    assert pt.maghrib.strftime("%H:%M") == "21:22"
    assert ordered_times(pt) == sorted(ordered_times(pt))


def gen_angle_cases(n=12):
    rng = random.Random(SEED + 5)
    cases = []
    for i in range(n):
        # Lower bound 1.0 deg: below the -0.833 deg sunrise convention the
        # zero-angle inversion applies (see characterization test).
        fajr_angle = round(rng.uniform(1.0, 30.0), 2)
        isha_angle = round(rng.uniform(1.0, 30.0), 2)
        lat = rng.uniform(-60.0, 60.0)
        lon = rng.uniform(-180.0, 180.0)
        cases.append((f"G-ANG-{i:03d}", lat, lon, fajr_angle, isha_angle))
    return cases


class TestGeneratedAngles:
    """Custom fajr/isha angles in [0, 30] (method NONE): ordering holds and
    larger fajr angle never yields a later fajr (monotonicity)."""

    @pytest.mark.parametrize("case_id,lat,lon,fajr_angle,isha_angle", gen_angle_cases())
    def test_custom_angles(self, case_id, lat, lon, fajr_angle, isha_angle):
        date = DateComponents(2024, 6, 21)
        pt = PrayerTimes(
            (lat, lon),
            date,
            calculation_parameters=CalculationParameters(
                fajr_angle=fajr_angle, isha_angle=isha_angle
            ),
        )
        assert ordered_times(pt) == sorted(ordered_times(pt)), case_id
        pt_wide = PrayerTimes(
            (lat, lon),
            date,
            calculation_parameters=CalculationParameters(
                fajr_angle=min(90.0, fajr_angle + 5.0), isha_angle=isha_angle
            ),
        )
        assert pt_wide.fajr <= pt.fajr, case_id


HIJRI_SEED = SEED + 10
HIJRI_START = datetime(1900, 1, 1, tzinfo=timezone.utc)
HIJRI_END = datetime(2100, 12, 31, tzinfo=timezone.utc)


def gen_hijri_tabular_cases(n=24):
    rng = random.Random(HIJRI_SEED)
    span = (HIJRI_END - HIJRI_START).days
    cases = []
    for i in range(n):
        day = HIJRI_START + timedelta(days=rng.randrange(span + 1))
        cases.append((f"G-HIJ-{i:03d}", day))
    return cases


class TestGeneratedHijriTabular:
    """Property P7 (tabular Hijri, Type IIa): Gregorian -> Hijri ->
    Gregorian round-trips; leap pattern holds (11 leaps per 30-year
    cycle); fixed anchors pin the epoch and a modern month start."""

    @pytest.mark.parametrize("case_id,day", gen_hijri_tabular_cases())
    def test_tabular_roundtrip(self, case_id, day):
        cal = TabularCalendar()
        hijri = cal.from_gregorian(day.date())
        assert cal.to_gregorian(hijri) == day.date(), case_id
        assert gregorian_to_hijri(day, calendar=cal) == hijri, case_id

    def test_tabular_leap_pattern(self):
        cal = TabularCalendar()
        expected = {2, 5, 7, 10, 13, 16, 18, 21, 24, 26, 29}
        for cycle_start in (1, 31, 1411):
            leaps = {
                year - cycle_start + 1
                for year in range(cycle_start, cycle_start + 30)
                if cal.month_length(year, 12) == 30
            }
            assert leaps == expected

    def test_tabular_anchors(self):
        cal = TabularCalendar()
        assert cal.from_gregorian(datetime(622, 7, 19).date()) == HijriDate(1, 1, 1)
        assert gregorian_to_hijri(
            datetime(2025, 3, 1, tzinfo=timezone.utc), calendar=cal
        ) == HijriDate(1446, 9, 1)

    def test_tabular_factory_identity(self):
        assert isinstance(get_calendar("tabular"), TabularCalendar)
