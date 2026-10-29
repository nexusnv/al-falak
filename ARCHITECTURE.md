# Architecture

## Overview

`Al-Falak` is an offline library for Islamic astronomy, starting with precise prayer times and expanding into broader temporal calculations. It follows a pipeline architecture: input coordinates and date flow through astronomical models to produce accurate timekeeping outputs.

## Package Structure

```
src/alfalak/
├── __init__.py          # Public API re-exports
├── __main__.py          # CLI entry point (python -m alfalak)
├── PrayerTimes.py       # Main prayer times calculator
├── Qibla.py             # Qibla direction calculator
├── SunnahTimes.py       # Sunnah night markers
├── exceptions.py        # AlFalakError hierarchy
├── py.typed             # PEP 561 type marker
│
├── astronomy/           # Astronomical calculations
│   ├── Astronomical.py           # Solar position algorithms
│   ├── CalendricalHelper.py      # Julian day/century conversions
│   ├── CrescentGeometry.py       # Crescent geometry at sunset
│   ├── DeltaT.py                 # TT minus UT1 provider
│   ├── Geodesy.py                # WGS84 ellipsoidal geodesics
│   ├── LunarCoordinates.py       # Low-precision Moon position
│   ├── Mabims.py                 # MABIMS visibility criteria
│   ├── Odeh.py                   # Odeh visibility criterion
│   ├── SolarCoordinates.py       # Sun's declination, right ascension
│   ├── SolarTime.py              # Transit, sunrise, sunset, hour angles
│   └── Yallop.py                 # Yallop visibility criterion
│
├── calculation/         # Calculation configuration
│   ├── CalculationMethod.py      # Enum of methods (MWL, ISNA, etc.)
│   ├── CalculationParameters.py # User-configurable parameters
│   ├── HighLatitudeRule.py       # Night portion rules
│   ├── Madhab.py                 # Shafi/Hanafi Asr
│   ├── MethodsParameters.py      # Method-specific defaults
│   ├── PolarCircleRule.py        # Polar region strategies
│   ├── PrayerAdjustments.py      # Per-prayer minute offsets
│   └── Twilight.py               # Seasonal twilight adjustments
│
├── calendar/            # Hijri calendar conversion
│   ├── bridge.py                 # Gregorian/Hijri bridge with sunset rollover
│   ├── HijriCalendar.py          # Calendar contract and factory
│   ├── HijriDate.py              # Immutable Hijri date value type
│   ├── MabimsCalendar.py         # MABIMS 2021 calendar
│   ├── OffsetStore.py            # Per-month offset overrides
│   ├── TabularCalendar.py        # Arithmetic (tabular) calendar
│   └── UmmAlQuraCalendar.py      # Umm al-Qura calendar
│
├── cli/                 # CLI subcommands
│   ├── astro.py                  # Lunar position and Delta-T
│   ├── cities.py                 # Built-in city lookup
│   ├── common.py                 # Shared argument/output helpers
│   ├── hijri.py                  # Hijri conversion
│   ├── moon_sighting.py          # Crescent visibility
│   ├── prayer.py                 # Prayer times
│   ├── qibla.py                  # Qibla direction
│   └── sunnah.py                 # Sunnah night markers
│
├── data/                # Data types
│   ├── Cities.py                 # Built-in city coordinates
│   ├── Constants.py              # Canonical constants (Makkah)
│   ├── Coordinates.py            # Lat/lon with validation
│   ├── NightPortions.py          # Fajr/Isha night fractions
│   ├── Prayer.py                 # Prayer enum (FAJR, SUNRISE, etc.)
│   └── ShadowLength.py           # Asr shadow length factor
│
└── util/                # Utilities
    ├── CalendarUtil.py           # Minute rounding
    ├── DateComponents.py         # Date decomposition
    ├── FloatUtil.py              # Angle normalization
    └── TimeComponents.py         # Time decomposition
```

## Data Flow

```
Input: coordinates + date + calculation method/parameters
  │
  ▼
CalculationParameters ──► resolves method defaults, validates inputs
  │
  ▼
PolarCircleRule ──► resolves polar day/night (if needed)
  │
  ▼
SolarTime ──► computes transit, sunrise, sunset, hour angles
  │              (uses Astronomical + SolarCoordinates + CalendricalHelper)
  ▼
PrayerTimes ──► computes each prayer time:
  │              Fajr    = sunrise - night_portion (or twilight)
  │              Sunrise = solar sunrise
  │              Dhuhr   = solar transit
  │              Asr     = afternoon shadow length (madhab-dependent)
  │              Maghrib = solar sunset
  │              Isha    = sunset + night_portion (or interval)
  ▼
Output: timezone-aware UTC datetime for each prayer
```

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `PrayerTimes` | Orchestrates the calculation pipeline; public API |
| `Qibla` | Spherical trigonometry for direction to Makkah |
| `SunnahTimes` | Derives night markers from prayer times |
| `calculation/*` | Configuration, enums, method defaults |
| `astronomy/*` | Pure astronomical math (no prayer logic) |
| `calendar/*` | Gregorian/Hijri conversion rules and value types |
| `cli/*` | Command-line adapters over the public API |
| `data/*` | Immutable data types with validation |
| `util/*` | Shared helper functions |

## Error Hierarchy

```
AlFalakError (base)
├── AstronomicalError    # Sun position undefined (polar day/night)
├── ConfigurationError   # Invalid setup (method, madhab, etc.)
└── ValidationError      # Out-of-range input (coordinates, angles)
```

## Design Principles

- **No external dependencies** — pure Python standard library
- **Fully typed** — all public APIs annotated, `py.typed` shipped
- **Immutable data** — `Coordinates`, `Prayer`, etc. are frozen dataclasses
- **Explicit errors** — no silent failures; all errors are `AlFalakError` subclasses
- **Tested** — 100% line coverage, 99%+ branch coverage
