---
title: Timezone Handling
description: Understand how al-falak handles timezones and DST transitions.
slug: v1.2.0/timezone
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

## See also

- [Sunnah Times](sunnah-times/) — DST-safe night markers
- [API Reference](api-reference/) — full API documentation
