# al-falak

[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)
![pytest](https://github.com/nexusnv/al-falak/actions/workflows/test.yml/badge.svg)

`Al-Falak` is an offline library for Islamic astronomy, starting with precise prayer times and expanding into broader temporal calculations. It follows a pipeline architecture: input coordinates and date flow through astronomical models to produce accurate timekeeping outputs. It originates from the same [`batoulapps/adhan`](https://github.com/batoulapps/adhan) port lineage as [alphahm/adhanpy](https://github.com/alphahm/adhanpy) (via that Python port) and is developed and released as an independent library, from a detached fork of the original `adhanpy` repository.

## Features

- **Offline** — no network calls, no API keys
- **Timezone-aware** — returns UTC `datetime` objects, with optional `ZoneInfo` conversion
- **Multiple calculation methods** — Muslim World League, ISNA, Egyptian, Karachi, Umm al-Qura, Dubai, Moonsighting Committee, and more
- **Polar region support** — configurable strategies for locations above the Arctic/Antarctic circles
- **High latitude rules** — middle of the night, seventh of the night, twilight angle
- **Madhab selection** — Shafi (default) and Hanafi for Asr calculation
- **Qibla direction** — degrees clockwise from north
- **Sunnah times** — middle and last third of the night
- **Moon sighting** — crescent geometry at sunset with Yallop, Odeh, and MABIMS visibility criteria
- **Hijri converter** — Gregorian-to-Hijri dates via tabular, Umm al-Qura, and per-country MABIMS calendars, with sunset rollover and official-correction offsets
- **CLI** — `python -m alfalak` for quick terminal output
- **Fully typed** — PEP 561 `py.typed` marker, `mypy --disallow-untyped-defs` clean

## Requirements

- Python >= 3.11

## Installation

```bash
pip install al-falak
```

## Quick Start

```python
from datetime import datetime
from alfalak import PrayerTimes, CalculationMethod, Prayer

# Coordinates for Raleigh, NC
coordinates = (35.7750, -78.6336)
today = datetime.now()

prayer_times = PrayerTimes(
    coordinates,
    today,
    CalculationMethod.NORTH_AMERICA,
)

print(f"Fajr:    {prayer_times.fajr.strftime('%H:%M')}")
print(f"Sunrise: {prayer_times.sunrise.strftime('%H:%M')}")
print(f"Dhuhr:   {prayer_times.dhuhr.strftime('%H:%M')}")
print(f"Asr:     {prayer_times.asr.strftime('%H:%M')}")
print(f"Maghrib: {prayer_times.maghrib.strftime('%H:%M')}")
print(f"Isha:    {prayer_times.isha.strftime('%H:%M')}")
```

## Usage

### Timezone Conversion

Pass a `ZoneInfo` object to get times in that timezone:

```python
from zoneinfo import ZoneInfo
from alfalak import PrayerTimes, CalculationMethod

london_zone = ZoneInfo("Europe/London")
prayer_times = PrayerTimes(
    (51.5074, -0.1278),
    datetime.now(),
    CalculationMethod.MOON_SIGHTING_COMMITTEE,
    time_zone=london_zone,
)
```

### Custom Calculation Parameters

```python
from alfalak import PrayerTimes, CalculationParameters

params = CalculationParameters(
    fajr_angle=18,
    isha_angle=18,
    isha_interval=90,  # Isha = Maghrib + 90 minutes
)
prayer_times = PrayerTimes(
    coordinates,
    today,
    calculation_parameters=params,
)
```

### Qibla Direction

```python
from alfalak import Qibla

direction = Qibla((35.7750, -78.6336)).direction
print(f"Qibla: {direction:.1f}° clockwise from north")
```

### Sunnah Times

```python
from alfalak import PrayerTimes, SunnahTimes, CalculationMethod

prayer_times = PrayerTimes(coordinates, today, CalculationMethod.MUSLIM_WORLD_LEAGUE)
sunnah = SunnahTimes(prayer_times)

print(f"Middle of the night: {sunnah.middle_of_the_night}")
print(f"Last third:         {sunnah.last_third_of_the_night}")
```

### Polar Regions

```python
from alfalak import PrayerTimes, CalculationParameters, PolarCircleRule

params = CalculationParameters(
    polar_circle_rule=PolarCircleRule.NEAREST_LATITUDE,  # default
)
prayer_times = PrayerTimes(
    (78.2232, 15.6267),  # Longyearbyen, Svalbard
    datetime.now(),
    calculation_parameters=params,
)
```

### Hijri Conversion

```python
from datetime import datetime, timezone
from alfalak import get_calendar, gregorian_to_hijri

hijri = gregorian_to_hijri(
    datetime(2025, 3, 1, 12, 0, tzinfo=timezone.utc),
    calendar=get_calendar("tabular"),
)
print(hijri.isoformat())  # 1446-09-01
```

### Command Line

```bash
python -m alfalak --latitude 35.7750 --longitude -78.6336 --date 2015-07-12 --method NORTH_AMERICA
```

Output:
```
fajr=2015-07-12T08:42:00+00:00
sunrise=2015-07-12T10:08:00+00:00
dhuhr=2015-07-12T17:21:00+00:00
asr=2015-07-12T21:09:00+00:00
maghrib=2015-07-13T00:32:00+00:00
isha=2015-07-13T01:57:00+00:00
```

```bash
python -m alfalak hijri --date 2025-03-01 --calendar tabular
```

```
hijri=1446-09-01
calendar=tabular
```

See [the Hijri converter guide](docs/user/hijri-converter.md) for the Umm al-Qura and MABIMS calendars, sunset rollover, and official-correction offsets.

## API Reference

See [`docs/user/api-reference.md`](docs/user/api-reference.md) for the full API reference
([rendered site](https://nexusnv.github.io/al-falak/api-reference/)).

## Migrating from adhanpy

`Al-Falak` is developed as an independent library, but it originates from the same
[`batoulapps/adhan`](https://github.com/batoulapps/adhan) port lineage as
[`adhanpy`](https://github.com/alphahm/adhanpy), so the public surface keeps the same
class and method names — switching packages is typically a matter of changing the
install (`adhanpy` → `al-falak`) and the import (`adhanpy` → `alfalak`). The move exists
to track currently supported Python versions, keep development dependencies and tooling
current, and leave room for the milestones of this project to evolve on their own.
In return you get a hardened `AlFalakError` hierarchy, fully typed APIs, and ongoing
maintenance. See [the migration guide](docs/user/migration.md) for details.

## Examples

See [`src/example/`](src/example/) for comprehensive examples covering:
- Basic usage
- Calculation methods comparison
- Qibla direction
- Sunnah times
- Polar region strategies
- High latitude rules
- Madhab selection
- Moon sighting and Hijri conversion
- CLI usage

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup and contribution guidelines.

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for a high-level overview of the codebase.

## Attribution & References

### Original Authors & Projects

- **batoulapps** — Original `adhan` library in [Java](https://github.com/batoulapps/adhan-java), [JavaScript](https://github.com/batoulapps/adhan-js), [Swift](https://github.com/batoulapps/adhan-swift), and [Kotlin](https://github.com/batoulapps/adhan-kotlin). The astronomical calculation methods, formulas, and overall architecture are derived from these implementations.
- **alphahm** — Original [adhanpy](https://github.com/alphahm/adhanpy) Python port. This fork continues from that work.

### Astronomical Calculation Sources

The prayer time calculation methods, mathematical formulas, and computational steps are derived from:

- **Jean Meeus** — *Astronomical Algorithms* (2nd ed., Willmann-Bell, 1998). The core astronomical formulas for solar position, equation of time, and hour angle calculations.
- **US Naval Observatory (USNO)** — Solar position algorithms and twilight calculations. Reference: [aa.usno.navy.mil](https://aa.usno.navy.mil/)
- **PrayTimes.org** — Standard prayer time calculation methods and Fajr/Isha angle conventions. Reference: [praytimes.org](https://praytimes.org/)
- **Muslim World League** — Fajr angle 18°, Isha angle 17°
- **ISNA (Islamic Society of North America)** — Fajr angle 15°, Isha angle 15°
- **Egyptian General Authority of Survey** — Fajr angle 19.5°, Isha angle 17.5°
- **University of Islamic Sciences, Karachi** — Fajr angle 18°, Isha angle 18°
- **Umm al-Qura University, Makkah** — Fajr angle 18.5°, Isha interval 90 minutes
- **Moonsighting Committee** — Fajr angle 18°, Isha angle 18°, with seasonal adjustments

### License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

## Credits

- **batoulapps** — original `adhan` implementation and calculation methods
- **alphahm** — original `adhanpy` Python port
- **Azahari Zaman** — community maintenance of `al-falak`
