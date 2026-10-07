---
title: Sunnah Times
description: Calculate Sunnah night markers — thirds, halves, and the Tahajjud window.
slug: v1.1.0/sunnah-times
---

# Sunnah Times

Sunnah times are recommended times for night prayer (Qiyam/Tahajjud), derived from the period between Maghrib and Fajr.

## Basic usage

```python
from datetime import datetime
from alfalak import PrayerTimes, SunnahTimes, CalculationMethod

prayer_times = PrayerTimes(
    (35.7750, -78.6336),
    datetime.now(),
    CalculationMethod.MUSLIM_WORLD_LEAGUE,
)
sunnah = SunnahTimes(prayer_times)

print(f"First third: {sunnah.first_third_of_the_night}")
print(f"Middle of the night: {sunnah.middle_of_the_night}")
print(f"Last third: {sunnah.last_third_of_the_night}")
print(f"Tahajjud window: {sunnah.tahajjud_window}")
print(f"Quarter: {sunnah.night_fraction(0.25)}")
```

## What are Sunnah times?

| Marker | Meaning |
|---|---|
| `first_third_of_the_night` | One third into the night (Maghrib + 1/3) |
| `middle_of_the_night` | Midpoint between Maghrib and Fajr (Maghrib + 1/2) |
| `last_third_of_the_night` | Start of the last third of the night, recommended for Qiyam (Maghrib + 2/3) |
| `tahajjud_window` | `(last_third_of_the_night, next-day Fajr)` tuple — the Qiyam window |
| `night_fraction(f)` | Maghrib + `f` of the night for any `0 < f < 1` |

`middle_of_the_night`, `first_third_of_the_night`, and
`last_third_of_the_night` are thin wrappers around
`night_fraction(1/2)`, `night_fraction(1/3)`, and `night_fraction(2/3)`.

## Night definition

The night is **Maghrib to next-day Fajr** — not same-day sunset-to-Fajr.
Concretely, `SunnahTimes(prayer_times)` rebuilds tomorrow's `PrayerTimes`
with the same coordinates, parameters, and timezone, then splits the
interval from today's Maghrib to tomorrow's Fajr.

Offset inclusion: Maghrib and Fajr already carry every configured offset
(per-prayer `PrayerAdjustments`, method offsets, and high-latitude caps),
so the night length — and every marker — includes them. There is a single
"half" (the midpoint), not two half-markers; use `tahajjud_window` when
you need a window rather than a point.

Rounding order: duration math runs in UTC, the result is rounded to the
nearest minute half-up (`rounded_minute`), and only then converted to the
display zone (`astimezone`). Minute-rounded outputs therefore never carry
seconds or microseconds.

Degenerate nights (Maghrib at or after next-day Fajr once offsets apply,
e.g. extreme per-prayer adjustments) raise `ValidationError` at
construction instead of returning a marker before Maghrib.

## Alternative anchors

Some authorities anchor the night at Isha instead of Maghrib, or at
astronomical sunset ignoring Maghrib offsets. Pass explicit aware
datetimes to `night_fraction` for those schools:

```python
# Isha-anchored school: Isha -> next-day Fajr
isha_half = sunnah.night_fraction(0.5, start=prayer_times.isha)

# Fully explicit pair (e.g. unadjusted sunset as start)
custom = sunnah.night_fraction(0.5, start=start_dt, end=end_dt)
```

Omitted `start`/`end` fall back to Maghrib/next-day Fajr. Anchors must be
timezone-aware datetimes with `end > start`; anything else raises
`ValidationError`, as does a fraction outside `(0, 1)`.

## With timezone

```python
from zoneinfo import ZoneInfo

tz = ZoneInfo("America/New_York")
prayer_times = PrayerTimes(
    coordinates,
    datetime.now(),
    CalculationMethod.MUSLIM_WORLD_LEAGUE,
    time_zone=tz,
)
sunnah = SunnahTimes(prayer_times)
```

## DST-safe

The calculation uses absolute elapsed time (UTC internally), so markers are correct even on nights with DST transitions. Spring-forward nights are one hour short in absolute time; fall-back nights (e.g. 2015-10-31 America/New_York) are one hour long — wall-clock subtraction would be off by an hour, UTC subtraction is not. Local outputs on a fall-back night carry the correct `fold` (PEP 495) via `astimezone`.

## See also

- [API Reference](/v1.1.0/api-reference/) — full API documentation
- [Timezone Handling](/v1.1.0/timezone/) — timezone conversion details
