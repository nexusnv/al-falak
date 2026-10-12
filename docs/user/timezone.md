---
title: Timezone Handling
description: Understand how al-falak handles timezones and DST transitions.
---

# Timezone Handling

Al-Falak returns timezone-aware UTC `datetime` objects by default. You can convert to any timezone using the `time_zone` parameter.

## Default behavior (UTC)

```python
from datetime import datetime
from alfalak import PrayerTimes, CalculationMethod

pt = PrayerTimes(
    (35.7750, -78.6336),
    datetime.now(),
    CalculationMethod.NORTH_AMERICA,
)
print(pt.fajr.tzinfo)  # UTC
```

## With a specific timezone

```python
from zoneinfo import ZoneInfo

tz = ZoneInfo("America/New_York")
pt = PrayerTimes(
    (35.7750, -78.6336),
    datetime.now(),
    CalculationMethod.NORTH_AMERICA,
    time_zone=tz,
)
print(pt.fajr.tzinfo)  # America/New_York
```

## Converting after creation

```python
from zoneinfo import ZoneInfo

pt = PrayerTimes(coordinates, datetime.now(), CalculationMethod.NORTH_AMERICA)
local_time = pt.fajr.astimezone(ZoneInfo("Europe/London"))
```

## DST transitions

Al-Falak handles DST correctly:

- All internal calculations use UTC
- Sunnah times use absolute elapsed time (not wall-clock subtraction)
- Returned datetimes carry the correct `ZoneInfo` with DST offset

```python
from zoneinfo import ZoneInfo

# US springs forward on 2025-03-09
tz = ZoneInfo("America/New_York")
pt = PrayerTimes(
    (35.7750, -78.6336),
    datetime(2025, 3, 9),
    CalculationMethod.MUSLIM_WORLD_LEAGUE,
    time_zone=tz,
)
sunnah = SunnahTimes(pt)
# Markers are correct despite the 1-hour DST jump
```

## Windows note

On Windows, install the `tzdata` package for IANA timezone support:

```bash
pip install tzdata
```

## Tested zones and DB pinning

The test suite pins `tzdata==2026.5` (dev/test only, never a runtime dependency) and runs with `PYTHONTZPATH=""` in CI to prefer the pinned IANA database. 

Key points:

- **CI configuration**: The pytest step sets `env: PYTHONTZPATH: ""` to constrain `zoneinfo` to the installed tzdata bundle.
- **Fallback behavior**: If `tzdata` is absent, tests skip via `pytest.importorskip("tzdata")`. Any diagnostic logging (such as `zoneinfo.TZPATH` or `importlib.metadata.version("tzdata")`) is for troubleshooting only and never asserted for equality.
- **Environment vs programmatic**: Using `PYTHONTZPATH` is preferred; if using `zoneinfo.reset_tzpath()` as a fallback, save and restore `TZPATH` in `try/finally`.
- **Coverage**: The timezone matrix exercises high-latitude cases (toward 60°+), modern political/DST changes (including zones with recent transitions), polar day/night, far-eastern zones, UTC across DST boundaries, and common regions like Europe/Paris and America/New_York. Behavior asserts verify correct offsets, ordering, and expected transition effects—not just absence of errors.
ensures deterministic behavior across DST transitions, rule changes, and
high-latitude edge cases.

The `zoneinfo` module first looks in directories given by `TZPATH`; setting
`PYTHONTZPATH=""` effectively disables the environment search path so the
distribution-provided (pinned) tzdata is used consistently. Windows end users
may need to install `tzdata` via `pip install tzdata` for the same IANA data.

> Note: diagnostics in tests may log `zoneinfo.TZPATH` and the `tzdata` version;
> these are for reproducibility only and are not asserted as exact values.

### Nonexistent local time policy

When converting UTC instants to local time across a spring-forward gap,
`zoneinfo` cannot represent the "missing" wall-clock minute; al-falak computes
times as UTC instants (with adjustments/rounding applied in UTC) and then uses
`astimezone()` at the output boundary. This means we never construct a wall time
inside a gap, and all returned datetimes are valid, correctly offset local times.

### Local date boundary note

Some zones with large offsets (e.g. +14) can shift the calendar date between UTC
and the local time. All comparisons and ordering checks are applied to the
returned aware datetimes (their actual instants/offsets), not to stringified
dates alone. High-latitude and polar cases remain subject to the polar circle
rules described in [Polar Regions](polar-regions/).

## See also

- [Sunnah Times](sunnah-times/) — DST-safe night markers
- [API Reference](api-reference/) — full API documentation

## Tested zones and DB pinning

- Pinned IANA database: `tzdata==2026.5` (dev/test only; not a runtime dependency).
- CI sets `PYTHONTZPATH=""` for the pytest step so the pinned `tzdata` package takes precedence over system zoneinfo.
- Environment fallback: `zoneinfo` uses the system database when `tzdata` is absent; the env-var approach is preferred over in-process `zoneinfo.reset_tzpath()` hacks.
- Windows users may need to install `tzdata` (the Python runtime does not ship full IANA data on Windows).
