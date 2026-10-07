---
title: Polar Regions
description: Handle prayer times in polar regions where the sun may never rise or set.
slug: v1.1.0/polar-regions
---

# Polar Regions

Above the Arctic Circle (or below the Antarctic Circle), the sun may never rise or set for days or weeks. Al-Falak provides configurable strategies for these situations.

## PolarCircleRule options

| Rule | Behavior |
|---|---|
| `NEAREST_LATITUDE` | Compute at nearest latitude where sun rises/sets (default) |
| `NEAREST_DAY` | Use schedule from nearest date with normal sunrise/sunset |
| `MAKKAH` | Use Makkah's schedule for the same date |
| `NONE` | Raise `AstronomicalError` (no fallback) |

## Using a polar rule

```python
from alfalak import PrayerTimes, CalculationParameters, PolarCircleRule

params = CalculationParameters(
    polar_circle_rule=PolarCircleRule.NEAREST_LATITUDE,
)
prayer_times = PrayerTimes(
    (78.2232, 15.6267),  # Longyearbyen, Svalbard
    datetime.now(),
    calculation_parameters=params,
)
```

## NEAREST_LATITUDE (default)

Aqrab al-Bilad: finds the nearest latitude (same longitude, same date) where the sun still rises and sets. This is the default behavior.

## NEAREST_DAY

Aqrab al-Ayyam: finds the nearest date (same location) with a normal sunrise/sunset schedule. Returned datetimes carry that date.

## MAKKAH

Uses Makkah's coordinates (21.4225°N, 39.8262°E) for the same date. Useful for consistency with the Haram schedule.

## NONE

No fallback. Raises `AstronomicalError` when the sun never rises or sets:

```python
from alfalak import PrayerTimes, CalculationParameters, PolarCircleRule, AstronomicalError

params = CalculationParameters(polar_circle_rule=PolarCircleRule.NONE)
try:
    PrayerTimes((78.2232, 15.6267), datetime.now(), calculation_parameters=params)
except AstronomicalError as e:
    print(f"Polar day/night: {e}")
```

## Important notes

- Estimates are approximations: near the polar boundary, adjacent markers can invert by minutes
- The `NEAREST_LATITUDE` strategy backs off 0.5° from the exact boundary to ensure a usable day/night split
- All strategies preserve the original date in the returned datetimes (except `NEAREST_DAY` which uses the nearest valid date)

## Interaction with high-latitude caps

Polar resolution runs before the `HighLatitudeRule` night-fraction caps: the
fallback coordinates/date get a normal schedule first, then Fajr/Isha are
clamped as usual. Observer `elevation_m` is threaded into the polar
rise/set probes too, so an elevated observer keeps the same horizon for
fallback detection and for the final times.
