---
title: al-falak
description: An offline Python library for calculating Islamic prayer times.
slug: v1.1.0
---

# al-falak

An offline Python library for calculating Islamic prayer times. A community-maintained fork of [alphahm/adhanpy](https://github.com/alphahm/adhanpy), which is a Python port of [batoulapps/adhan](https://github.com/batoulapps/adhan) (Java).

## Who is this for?

| Audience | Use case |
|---|---|
| **Python developers** | Integrate prayer times into applications, bots, or services |
| **Researchers** | Analyze prayer time data across locations and dates |
| **Embedded systems** | Run on devices with no network connectivity |

## What al-falak does and does not do

| Does | Does not |
|---|---|
| Calculate all 6 prayer times (Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha) | Require network access |
| Support 11 calculation methods | Provide Hadith or fiqh rulings |
| Handle polar day/night with configurable strategies | Calculate prayer times for other religions |
| Return timezone-aware UTC datetimes | Include a GUI or web interface |
| Calculate Qibla direction | |
| Calculate Sunnah night markers | |
| Provide a CLI | |

## At a glance

```python
from datetime import datetime
from alfalak import PrayerTimes, CalculationMethod

coordinates = (35.7750, -78.6336)  # Raleigh, NC
prayer_times = PrayerTimes(
    coordinates,
    datetime.now(),
    CalculationMethod.NORTH_AMERICA,
)

print(f"Fajr: {prayer_times.fajr.strftime('%H:%M')}")
print(f"Dhuhr: {prayer_times.dhuhr.strftime('%H:%M')}")
print(f"Maghrib: {prayer_times.maghrib.strftime('%H:%M')}")
```

## Where to go next

| I want to... | Go to |
|---|---|
| Install and run my first calculation | [Getting Started](getting-started/) |
| Compare calculation methods | [Calculation Methods](calculation-methods/) |
| Handle polar regions | [Polar Regions](polar-regions/) |
| Use the CLI | [CLI Usage](cli/) |
| See all public APIs | [API Reference](api-reference/) |
| Migrate from adhanpy | [Migration](migration/) |

## Requirements

- Python >= 3.11

## License

MIT
