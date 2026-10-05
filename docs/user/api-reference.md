---
title: API Reference
description: Complete API reference for al-falak.
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
    LunarCoordinates,
    CrescentGeometry,
    crescent_geometry_at_sunset,
    delta_t,
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

## LunarCoordinates

```python
LunarCoordinates(julian_day_tt: float)
```

Low-precision geocentric Moon position (Meeus 2nd ed. Ch.47, Tables 47.A–47.B).
Non-real or non-finite Julian days raise `ValidationError`.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `longitude` | `float` | Geocentric ecliptic longitude in degrees [0, 360) |
| `latitude` | `float` | Geocentric ecliptic latitude in degrees |
| `distance_km` | `float` | Geocentric distance in km |
| `right_ascension` | `float` | Right ascension in degrees [0, 360) |
| `declination` | `float` | Declination in degrees |

## CrescentGeometry

```python
crescent_geometry_at_sunset(
    day: date, coordinates: Coordinates,
    delta_t_override: float | None = None,
) -> CrescentGeometry
```

Topocentric crescent geometry at local sunset for moon-sighting work:
elongation, geocentric/topocentric arcs of vision, azimuth difference,
crescent width, illumination, moonset lag, and moon age.
Raises `AstronomicalError` when the Sun does not set on that date;
non-`date`/`Coordinates` inputs (or a non-finite override) raise
`ValidationError`. A `datetime` is accepted and its calendar date is used.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `arcl_deg` | `float` | Sun–Moon elongation in degrees |
| `arcv_geo_deg` | `float` | Geocentric arc of vision in degrees |
| `arcv_topo_deg` | `float` | Topocentric (parallax-corrected) arc of vision in degrees |
| `sun_alt_deg` | `float` | True Sun altitude at the evaluated TT instant in degrees (near −0.83° at sunset; differs slightly because the ephemeris runs at TT) |
| `moon_alt_topo_deg` | `float` | Topocentric (parallax-corrected) Moon altitude in degrees — pass this (not ARCV) as `alt_deg` to the MABIMS helpers |
| `daz_deg` | `float` | Sun–Moon azimuth difference in degrees |
| `width_arcmin` | `float` | Crescent width in arcminutes |
| `illumination` | `float` | Illuminated fraction of the lunar disc [0, 1] |
| `lag_hours` | `float` | Hours from sunset to moonset (negative when the Moon sets first; `NaN` when no moonset occurs on that date; large positives mean a gibbous/full Moon up well past sunset — the crescent signal is a small positive lag) |
| `moon_age_days` | `float` | Days since the previous new moon (youngest hourly ARCL minimum over the prior 30 days) |
| `moon_age_at_moonset_days` | `float` | Moon age at moonset (sunset age advanced by the lag; `NaN` when no moonset occurs) — feed this to the MABIMS 1992 age branch |
| `used_delta_t_s` | `float` | Delta-T in seconds used for the TT conversion |
| `sunset_jd_utc` | `float` | Julian Date (UTC) of local sunset |

## delta_t

```python
delta_t(year: float, override: float | None = None) -> float
```

Isolated Delta-T (TT minus UT1, in seconds) for the lunar path only —
never called by the prayer path. Default is the Espenak polynomial for
2005–2050; pass IERS-observed values via `override` for modern dates.
Years outside 2005–2050 emit a `UserWarning` and extrapolate (the value is
still returned); the `override` path never warns. Non-real or non-finite
inputs raise `ValidationError` (`year` is validated even when `override=`
is set).

## yallop_q

```python
yallop_q(arcv_geo_deg: float, width_arcmin: float) -> float
```

Best-time Yallop q from geocentric ARCV (degrees) and topocentric
crescent width (arcminutes). Non-real or non-finite inputs raise
`ValidationError`.

## yallop_zone

```python
yallop_zone(q: float) -> str
```

Yallop visibility zone (`"A"`–`"F"`) for a q value. Non-real or
non-finite inputs raise `ValidationError`.

## odeh_v

```python
odeh_v(arcv_topo_deg: float, width_arcmin: float) -> float
```

Odeh V from airless topocentric ARCV (degrees) and topocentric
crescent width (arcminutes). Non-real or non-finite inputs raise
`ValidationError`.

## odeh_class

```python
odeh_class(v: float, arcl_deg: float) -> str
```

Odeh visibility class (`"A"`–`"D"`) for a V value and elongation
ARCL (degrees). Elongation below 6.4 degrees (Danjon floor) is class
`"D"` regardless of V. Non-real or non-finite inputs raise
`ValidationError`.

## is_neo_mabims_2021

```python
is_neo_mabims_2021(alt_deg: float, elong_deg: float) -> bool
```

Neo-MABIMS 2021 visibility: `True` when the topocentric Moon altitude
(`moon_alt_topo_deg` from `crescent_geometry_at_sunset`, not ARCV) is at
least 3 degrees and the elongation is at least 6.4 degrees.
Non-real or non-finite inputs raise `ValidationError`.

## is_mabims_1992

```python
is_mabims_1992(alt_deg: float, elong_deg: float, age_hours: float) -> bool
```

1992 MABIMS visibility: `True` when (topocentric Moon altitude
`>= 2` degrees and elongation `>= 3` degrees) or the Moon age is at
least 8 hours. Pass `moon_alt_topo_deg` (not ARCV) as the altitude.
Non-real or non-finite inputs raise `ValidationError`.

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

- [Getting Started](/getting-started/) — quick start guide
- [Calculation Methods](/calculation-methods/) — method details
- [Moon Sighting](/moon-sighting/) — crescent geometry and visibility criteria
- [Errors](/errors/) — error handling
