---
title: Madhab
description: Choose between Shafi and Hanafi Asr calculation methods.
slug: v1.2.1/madhab
---

# Madhab

The madhab (Islamic school of jurisprudence) determines how Asr prayer time is calculated. Al-Falak supports both major madhabs.

## Madhab options

| Madhab | Shadow Length | Default |
|---|---|---|
| `Madhab.SHAFI` | Single (1.0) | Yes |
| `Madhab.HANAFI` | Double (2.0) | No |

## Using a madhab

```python
from alfalak import PrayerTimes, CalculationParameters, Madhab

params = CalculationParameters()
params.madhab = Madhab.HANAFI
prayer_times = PrayerTimes(
    coordinates,
    datetime.now(),
    calculation_parameters=params,
)
```

## What is the difference?

Asr time is calculated based on the length of an object's shadow relative to the object's height:

- **Shafi**: Shadow length = object height × 1 (shadow equals object height)
- **Hanafi**: Shadow length = object height × 2 (shadow is twice object height)

This results in a later Asr time for Hanafi, typically 30–50 minutes later depending on location and date.

## Comparison example

```python
from datetime import datetime
from alfalak import PrayerTimes, CalculationParameters, Madhab, CalculationMethod

coordinates = (35.7750, -78.6336)
today = datetime.now()

for madhab in [Madhab.SHAFI, Madhab.HANAFI]:
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.madhab = madhab
    pt = PrayerTimes(coordinates, today, calculation_parameters=params)
    print(f"{madhab.name}: Asr at {pt.asr.strftime('%H:%M')}")
```

## See also

- [Calculation Methods](calculation-methods/) — all supported methods
- [API Reference](api-reference/) — full API documentation
