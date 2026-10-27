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

The test suite pins `tzdata==2026.5` (dev/test only, never a runtime
dependency) and runs with `PYTHONTZPATH=""` in CI so the pinned IANA database
wins over the system copy.

- **CI configuration**: the pytest step sets `env: PYTHONTZPATH: ""`, which
  constrains `zoneinfo` to the installed `tzdata` bundle.
- **Environment vs programmatic**: the environment-variable approach is
  preferred; if `zoneinfo.reset_tzpath()` is used instead, save and restore
  `TZPATH` in `try/finally`.
- **Diagnostics**: tests may log `zoneinfo.TZPATH` and the installed `tzdata`
  version for troubleshooting; these values are never asserted for equality.
- **Coverage**: the timezone matrix exercises high-latitude cases (69.6°N,
  including polar day/night resolution and the `PolarCircleRule.NONE` error
  path), modern political/DST changes (Mexico City's 2022 DST abolition,
  Europe/Paris and America/New_York spring-forward dates), far-eastern zones
  (Tokyo and Pacific/Kiritimati, including the +14 date shift), and UTC
  offsets. Assertions verify offsets, ordering, and date/transition effects —
  not merely absence of errors.

The `zoneinfo` module first looks in directories given by `TZPATH`; setting
`PYTHONTZPATH=""` disables that search path so the distribution-provided
(pinned) `tzdata` is used consistently. Windows end users may need to install
`tzdata` via `pip install tzdata` for the same IANA data.

### Nonexistent local time policy

When converting UTC instants to local time across a spring-forward gap,
`zoneinfo` cannot represent the "missing" wall-clock minute; al-falak computes
times as UTC instants (with adjustments and rounding applied in UTC) and then
uses `astimezone()` at the output boundary. This means we never construct a
wall time inside a gap, and all returned datetimes are valid, correctly offset
local times.

### Local date boundary note

Some zones with large offsets (e.g. +14) can shift the calendar date between
UTC and the local time. All comparisons and ordering checks are applied to the
returned aware datetimes (their actual instants/offsets), not to stringified
dates alone. High-latitude and polar cases remain subject to the polar circle
rules described in [Polar Regions](polar-regions/).

## See also

- [Sunnah Times](sunnah-times/) — DST-safe night markers
- [API Reference](api-reference/) — full API documentation
