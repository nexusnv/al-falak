---
title: Getting Started
description: Install al-falak and run your first prayer time calculation.
slug: v1.1.0/getting-started
---

# Getting Started

## Install

```bash
pip install al-falak
```

## Your first calculation

```python
from datetime import datetime
from alfalak import PrayerTimes, CalculationMethod

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

## Using a Coordinates object

```python
from alfalak import Coordinates, PrayerTimes, CalculationMethod

coords = Coordinates(latitude=35.7750, longitude=-78.6336)
prayer_times = PrayerTimes(coords, datetime.now(), CalculationMethod.MUSLIM_WORLD_LEAGUE)
```

## Using custom parameters

```python
from alfalak import PrayerTimes, CalculationParameters

params = CalculationParameters(
    fajr_angle=18,
    isha_angle=18,
    isha_interval=90,  # Isha = Maghrib + 90 minutes
)
prayer_times = PrayerTimes(
    coordinates,
    datetime.now(),
    calculation_parameters=params,
)
```

## Timezone conversion

```python
from zoneinfo import ZoneInfo

london = ZoneInfo("Europe/London")
prayer_times = PrayerTimes(
    (51.5074, -0.1278),
    datetime.now(),
    CalculationMethod.MOON_SIGHTING_COMMITTEE,
    time_zone=london,
)
```

## Next steps

- [Calculation Methods](/v1.1.0/calculation-methods/) — compare all 11 methods
- [API Reference](/v1.1.0/api-reference/) — full API documentation
- [CLI Usage](/v1.1.0/cli/) — command-line interface
