---
title: High Latitude Rules
description: Handle prayer times at high latitudes with extreme night lengths.
slug: v1.2.1/high-latitude
---

# High Latitude Rules

At high latitudes, summer nights can be very short, making it difficult to determine Fajr and Isha times. Al-Falak provides three rules for these situations.

## HighLatitudeRule options

| Rule | Behavior |
|---|---|
| `MIDDLE_OF_THE_NIGHT` | Fajr never earlier than middle of night, Isha never later (default) |
| `SEVENTH_OF_THE_NIGHT` | Fajr never earlier than start of last seventh, Isha never later than end of first seventh |
| `TWILIGHT_ANGLE` | Uses fajr_angle/60 and isha_angle/60 as night fractions |

## Using a high latitude rule

```python
from alfalak import PrayerTimes, CalculationParameters, HighLatitudeRule

params = CalculationParameters(
    high_latitude_rule=HighLatitudeRule.MIDDLE_OF_THE_NIGHT,
)
prayer_times = PrayerTimes(
    (51.5074, -0.1278),  # London
    datetime.now(),
    calculation_parameters=params,
)
```

## MIDDLE_OF_THE_NIGHT (default)

The night is split in half. Fajr cannot be earlier than the midpoint between sunset and sunrise, and Isha cannot be later than that midpoint.

## SEVENTH_OF_THE_NIGHT

The night is split into sevenths. Fajr cannot be earlier than the start of the last seventh, and Isha cannot be later than the end of the first seventh.

## TWILIGHT_ANGLE

Similar to seventh-of-the-night, but uses the Fajr and Isha angles divided by 60 as the night fraction. For example, with a Fajr angle of 18°, the fraction is 18/60 = 0.3 (30% of the night).

## When to use these rules

These rules are most relevant for locations above ~48° latitude during summer months:

| Latitude | Example locations |
|---|---|
| 48°–55° | Paris, Berlin, Kyiv, London |
| 55°–60° | Copenhagen, Oslo, Stockholm, St. Petersburg |
| 60°+ | Helsinki, Reykjavik, Anchorage, Longyearbyen |

## Interaction with Moonsighting Committee and polar fallback

- These caps apply to every method, but `MOON_SIGHTING_COMMITTEE` does not
  use them: it substitutes its own seasonal-twilight caps (see
  [Calculation Methods](/v1.2.1/calculation-methods/) — MSC section).
- Interval Isha (Umm al-Qura, Qatar) bypasses the Isha cap entirely:
  `maghrib + interval` is used as-is.
- Order of operations: `PolarCircleRule` resolution runs first (no-op on
  normal days). Only afterwards do these night-fraction caps clamp Fajr/Isha.
  Near the polar boundary the Asr clamps (`asr = dhuhr` when the shadow angle
  is unreachable, `asr = maghrib` when it spills past sunset) can also engage.

## See also

- [Polar Regions](/v1.2.1/polar-regions/) — handling polar day/night
- [Calculation Methods](/v1.2.1/calculation-methods/) — method-specific defaults
