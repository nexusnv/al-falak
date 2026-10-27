"""Seeded end-to-end fuzz for the public prayer-time seam (Phase 6.6).

Contract under test: on every day where the pipeline produces a schedule
(``PolarCircleRule.NONE`` means undefined days raise ``AstronomicalError``),
the public fields satisfy

    fajr <= sunrise <= dhuhr <= asr <= maghrib <= isha

and every field is a finite, UTC-aware instant. This is the public-seam
counterpart to the curated polar/boundary goldens: it explores latitude,
longitude, date, elevation and display zone together, but never imports a
private helper or calls a private setter.

Determinism: stdlib ``random.Random(SEED)`` only. The seed and a fixed input
tuple (including a tuple of zones, not a set/dict, whose iteration order
depends on ``PYTHONHASHSEED``) make two runs byte-identical.
"""

import math
import random
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from alfalak import (
    CalculationMethod,
    CalculationParameters,
    Coordinates,
    Madhab,
    PolarCircleRule,
    PrayerTimes,
)
from alfalak.exceptions import AstronomicalError
from alfalak.util.DateComponents import DateComponents

SEED = 20261012
N = 2000
DATE_START = date(2020, 1, 1)
DATE_SPAN_DAYS = 2192  # through 2025-12-31
ZONES = (
    None,
    ZoneInfo("UTC"),
    ZoneInfo("America/New_York"),
    ZoneInfo("Europe/London"),
    ZoneInfo("Asia/Kuala_Lumpur"),
    ZoneInfo("Pacific/Kiritimati"),
)
PRAYERS = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")


def _cases():
    rng = random.Random(SEED)
    for _ in range(N):
        latitude = rng.uniform(-89.9, 89.9)
        longitude = rng.uniform(-180.0, 180.0)
        day = DATE_START + timedelta(days=rng.randrange(DATE_SPAN_DAYS))
        elevation = rng.uniform(0.0, 3000.0)
        zone = ZONES[rng.randrange(len(ZONES))]
        yield latitude, longitude, day, elevation, zone


def _build_case(latitude, longitude, day, elevation, zone):
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.madhab = Madhab.SHAFI
    params.polar_circle_rule = PolarCircleRule.NONE
    params.elevation_m = elevation
    return PrayerTimes(
        Coordinates(latitude, longitude),
        DateComponents(day.year, day.month, day.day),
        calculation_parameters=params,
        time_zone=zone,
    )


def test_fuzz_case_generation_is_deterministic():
    assert list(_cases()) == list(_cases())


def test_public_prayer_ordering_across_seeded_cases():
    evaluated = 0
    undefined = 0
    for index, (latitude, longitude, day, elevation, zone) in enumerate(_cases()):
        case = (
            f"index={index} seed={SEED} lat={latitude:.6f} "
            f"lon={longitude:.6f} date={day.isoformat()} "
            f"elevation={elevation:.3f} tz={zone}"
        )
        try:
            prayer_times = _build_case(latitude, longitude, day, elevation, zone)
        except AstronomicalError:
            undefined += 1
            continue
        evaluated += 1

        values = [getattr(prayer_times, prayer) for prayer in PRAYERS]
        for prayer, value in zip(PRAYERS, values):
            assert value.tzinfo is not None, f"naive {prayer}: {case}"
            assert math.isfinite(value.timestamp()), f"non-finite {prayer}: {case}"

        assert (
            values[0] <= values[1] <= values[2] <= values[3] <= values[4] <= values[5]
        ), f"ordering violated: {case} " + " ".join(
            f"{prayer}={value.isoformat()}" for prayer, value in zip(PRAYERS, values)
        )

    # The generator must actually exercise the seam; a regression that turns
    # most cases into AstronomicalError would make the ordering checks
    # vacuous. The fixed seed currently evaluates 1670 of 2000 cases.
    assert evaluated >= 4 * N // 5, f"only {evaluated}/{N} cases evaluated"
    assert undefined > 0, "sweep never exercised the polar/AstronomicalError branch"
    assert evaluated + undefined == N
