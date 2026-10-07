---
title: API Reference
description: Complete API reference for al-falak.
slug: v1.1.0/api-reference
---

# API Reference

All public names are importable from the package root:

```python
from alfalak import (
    PrayerTimes,
    Qibla,
    SunnahTimes,
    CalculationMethod,
    CalculationParameters,
    HighLatitudeRule,
    Madhab,
    PolarCircleRule,
    PrayerAdjustments,
    Coordinates,
    Prayer,
    AlFalakError,
    AstronomicalError,
    ConfigurationError,
    ValidationError,
)
```

## PrayerTimes

```python
PrayerTimes(
    coordinates: tuple[float, float] | Coordinates,
    date: datetime | DateComponents,
    calculation_method: CalculationMethod | None = None,
    calculation_parameters: CalculationParameters | None = None,
    time_zone: ZoneInfo | None = None,
)
```

Exactly one of `calculation_method` or `calculation_parameters` must be provided.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `imsak` | `datetime` | Imsak time (Fajr − `imsak_offset`, default 10 min) |
| `fajr` | `datetime` | Fajr time |
| `sunrise` | `datetime` | Sunrise time |
| `syuruk` | `datetime` | Syuruk time (== sunrise, MY/SG name) |
| `ishraq` | `datetime` | Ishraq time (sunrise + `ishraq_offset`, default 15 min) |
| `dhuha` | `datetime` | Start of Dhuha window (sunrise + `dhuha_offset`, default 28 min) |
| `dhuhr` | `datetime` | Dhuhr time |
| `asr` | `datetime` | Asr time |
| `maghrib` | `datetime` | Maghrib time |
| `isha` | `datetime` | Isha time |
| `coordinates` | `Coordinates` | Location coordinates |
| `calculation_parameters` | `CalculationParameters` | Parameters used |
| `time_zone` | `ZoneInfo \| None` | Timezone (if set) |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `time_for_prayer(prayer: Prayer)` | `datetime` | Get time for a specific prayer |

## Qibla

```python
Qibla(coordinates: tuple[float, float] | Coordinates, method: str = "spherical")
```

`method` is `"spherical"` (default) or `"ellipsoidal"` (Karney inverse on
WGS84); anything else raises `ConfigurationError`.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `direction` | `float` | Degrees clockwise from north |
| `distance_to_makkah_km` | `float` | Distance to Makkah in km (per `method`) |
| `method` | `str` | `"spherical"` (default) or `"ellipsoidal"` |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `magnetic_direction(declination_deg)` | `float` | Compass heading: true direction minus east-positive declination, unwound to [0, 360); accepts any real number (int/float/Fraction/Decimal) |

## SunnahTimes

```python
SunnahTimes(prayer_times: PrayerTimes)
```

The night is Maghrib to next-day Fajr (offsets included). Duration math
runs in UTC, rounds to the minute half-up, then converts to the display
zone.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `first_third_of_the_night` | `datetime` | Maghrib + 1/3 of the night |
| `middle_of_the_night` | `datetime` | Midpoint between Maghrib and Fajr |
| `last_third_of_the_night` | `datetime` | Start of last third of the night |
| `tahajjud_window` | `tuple[datetime, datetime]` | `(last_third_of_the_night, next-day Fajr)` |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `night_fraction(fraction, start=None, end=None)` | `datetime` | Maghrib + `fraction` of the night (`0 < fraction < 1`, else `ValidationError`); accepts `int`/`float`/`Fraction`/`Decimal` (`bool` rejected); pass aware `start`/`end` datetimes for Isha-anchored or sunset-anchored variants, `end` must be after `start` |

## CalculationParameters

```python
CalculationParameters(
    method: CalculationMethod | None = None,
    adjustments: PrayerAdjustments | None = None,
    method_adjustments: PrayerAdjustments | None = None,
    isha_interval: int = 0,
    fajr_angle: float = 0.0,
    isha_angle: float = 0.0,
    polar_circle_rule: PolarCircleRule = PolarCircleRule.NEAREST_LATITUDE,
    imsak_offset: int = 10,
    ishraq_offset: int = 15,
    dhuha_offset: int = 28,
    elevation_m: float = 0.0,
    is_ramadan: bool = False,
)
```

Minute-count offsets/intervals must be non-negative integers (`bool`
rejected); `elevation_m` must be a finite non-negative number of metres;
`is_ramadan` must be a `bool` (applies to `UMM_AL_QURA` only, 120 min total
in Ramadan vs 90 otherwise); `dhuha_offset` must be `>= ishraq_offset`.
Violations raise `ValidationError` (`is_ramadan` type raises
`ConfigurationError`).

**Attributes (settable):**

| Attribute | Type | Default | Description |
|---|---|---|---|
| `madhab` | `Madhab` | `Madhab.SHAFI` | Asr calculation method |
| `high_latitude_rule` | `HighLatitudeRule` | `MIDDLE_OF_THE_NIGHT` | High latitude rule |
| `polar_circle_rule` | `PolarCircleRule` | `NEAREST_LATITUDE` | Polar region strategy |
| `fajr_angle` | `float` | From method | Fajr angle in degrees |
| `isha_angle` | `float` | From method | Isha angle in degrees |
| `isha_interval` | `int` | From method | Isha interval in minutes |
| `imsak_offset` | `int` | `10` | Minutes before Fajr for Imsak |
| `ishraq_offset` | `int` | `15` | Minutes after sunrise for Ishraq |
| `dhuha_offset` | `int` | `28` | Minutes after sunrise for start of Dhuha window (`>= ishraq_offset`) |
| `elevation_m` | `float` | `0.0` | Observer eye height in metres for dip-of-horizon correction |
| `is_ramadan` | `bool` | `False` | Umm al-Qura Ramadan mode (120 min Isha total; preset only) |
| `method` | `CalculationMethod` | `NONE` | Calculation method |
| `adjustments` | `PrayerAdjustments` | — | Per-prayer minute offsets |
| `method_adjustments` | `PrayerAdjustments` | — | Method-specific offsets |

## Enums

### CalculationMethod

`NONE`, `MUSLIM_WORLD_LEAGUE`, `EGYPTIAN`, `KARACHI`, `UMM_AL_QURA`, `DUBAI`, `MOON_SIGHTING_COMMITTEE`, `NORTH_AMERICA`, `KUWAIT`, `QATAR`, `SINGAPORE`, `UOIF`, `JAKIM`

### HighLatitudeRule

`MIDDLE_OF_THE_NIGHT`, `SEVENTH_OF_THE_NIGHT`, `TWILIGHT_ANGLE`

### Madhab

`SHAFI`, `HANAFI`

### PolarCircleRule

`NONE`, `NEAREST_LATITUDE`, `NEAREST_DAY`, `MAKKAH`

### Prayer

`NONE`, `IMSAK`, `FAJR`, `SUNRISE`, `SYURUK`, `ISHRAQ`, `DHUHA`, `DHUHR`, `ASR`, `MAGHRIB`, `ISHA` (listed in chronological definition order, which is canonical — numeric values are frozen for backward compatibility, so do not sort by `.value`)

## Data types

### Coordinates

```python
Coordinates(latitude: float, longitude: float)
```

Validates that latitude is in [-90, 90] and longitude is in [-180, 180].

### PrayerAdjustments

```python
PrayerAdjustments(
    fajr: int = 0,
    sunrise: int = 0,
    dhuhr: int = 0,
    asr: int = 0,
    maghrib: int = 0,
    isha: int = 0,
    imsak: int = 0,
    ishraq: int = 0,
    dhuha: int = 0,
)
```

No separate `syuruk` slot by design: Syuruk aliases sunrise, so `sunrise`
adjustments flow through to it.

## Exceptions

```
AlFalakError (base)
├── AstronomicalError
├── ConfigurationError
└── ValidationError
```

## See also

- [Getting Started](getting-started/) — quick start guide
- [Calculation Methods](calculation-methods/) — method details
- [Errors](errors/) — error handling
