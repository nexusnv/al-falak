---
title: Errors
description: Understand the al-falak error hierarchy and how to handle failures.
---

# Errors

Al-Falak uses a dedicated error hierarchy for all failures. All errors inherit from `AlFalakError`.

## Error hierarchy

```
AlFalakError (base)
├── AstronomicalError    # Sun position undefined (polar day/night)
├── ConfigurationError   # Invalid setup (method, madhab, etc.)
└── ValidationError      # Out-of-range input (coordinates, angles)
```

## Catching errors

```python
from alfalak import PrayerTimes, CalculationMethod, AlFalakError

try:
    pt = PrayerTimes((35.7750, -78.6336), datetime.now(), CalculationMethod.NORTH_AMERICA)
except AlFalakError as e:
    print(f"Calculation failed: {e}")
```

## Specific error types

### AstronomicalError

Raised when the sun never rises or sets (polar day/night) and `PolarCircleRule.NONE` is set:

```python
from alfalak import AstronomicalError, PolarCircleRule, CalculationParameters

params = CalculationParameters(polar_circle_rule=PolarCircleRule.NONE)
try:
    PrayerTimes((78.2232, 15.6267), datetime.now(), calculation_parameters=params)
except AstronomicalError as e:
    print(f"Polar day/night: {e}")
```

Also raised by `crescent_geometry_at_sunset` when the Sun does not set on
that date (polar day/night), since there is no sunset to evaluate the
crescent at.

### ConfigurationError

Raised for invalid configuration:

```python
from alfalak import ConfigurationError, CalculationParameters

try:
    # Both method and parameters is invalid
    params = CalculationParameters(method=None, fajr_angle=18)
    # ... but passing both to PrayerTimes raises
except ConfigurationError as e:
    print(f"Invalid config: {e}")
```

### ValidationError

Raised for out-of-range input:

```python
from alfalak import ValidationError, Coordinates

try:
    Coordinates(latitude=91, longitude=0)
except ValidationError as e:
    print(f"Invalid coordinates: {e}")
```

Moon-sighting inputs follow the same rule: `crescent_geometry_at_sunset`
rejects a non-`date` day (a `datetime` is accepted and its calendar date
is used), a non-`Coordinates` location, or a non-finite
`delta_t_override`, as do the `delta_t`, `yallop_*`, `odeh_*`, and
`is_*mabims*` helpers for non-real or non-finite arguments (`odeh_v` and
`yallop_q` additionally reject a negative crescent width).

## Error messages

All errors include descriptive messages:

```
AstronomicalError: Unable to compute prayer times: sunrise, sunset, or solar transit is undefined for these coordinates and date (polar day/night). coordinates=Coordinates(latitude=78.2232, longitude=15.6267), date=DateComponents(year=2026, month=6, day=21).
```

## See also

- [Moon Sighting](/moon-sighting/) — crescent geometry error cases
- [Polar Regions](/polar-regions/) — handling polar day/night
- [API Reference](/api-reference/) — full API documentation
