---
title: Qibla Direction
description: Calculate the Qibla direction (degrees clockwise from north) for any location.
slug: v1.2.0/qibla
---

# Qibla Direction

The Qibla is the direction to the Kaaba in Makkah, used during Islamic prayer.

## Basic usage

```python
from alfalak import Qibla

direction = Qibla((35.7750, -78.6336)).direction
print(f"Qibla: {direction:.1f}° clockwise from north")
```

## Using a Coordinates object

```python
from alfalak import Qibla, Coordinates

coords = Coordinates(latitude=35.7750, longitude=-78.6336)
direction = Qibla(coords).direction
```

## Multiple cities

```python
from alfalak import Qibla

cities = [
    ("Raleigh, US", (35.7750, -78.6336)),
    ("London, UK", (51.5074, -0.1278)),
    ("Jakarta, ID", (-6.2088, 106.8456)),
    ("Sydney, AU", (-33.8688, 151.2093)),
]

for name, coords in cities:
    print(f"{name}: {Qibla(coords).direction:.1f}°")
```

## Distance to Makkah

```python
from alfalak import Qibla

qibla = Qibla((35.7750, -78.6336))
print(f"{qibla.direction:.1f}°, {qibla.distance_to_makkah_km:.0f} km")
```

## Ellipsoidal (WGS84) mode

The default above treats Earth as a sphere. For the geodesic on the
WGS84 ellipsoid (Karney inverse, stdlib-only, no new dependencies), opt in:

```python
from alfalak import Qibla

qibla = Qibla((35.7750, -78.6336), method="ellipsoidal")
print(f"{qibla.direction:.3f}°, {qibla.distance_to_makkah_km:.3f} km")
```

Any other `method` raises `ConfigurationError`. The spherical-vs-ellipsoidal
difference is typically a few arcminutes, worst case ~0.3–0.35° — use the
ellipsoidal mode when that matters to you, spherical otherwise.

## Magnetic compass heading

`direction` is true-north (that is the default). A magnetic compass points
at magnetic north instead, so pass your local declination to get the needle
heading:

```python
from alfalak import Qibla

qibla = Qibla((35.7750, -78.6336))
print(f"True: {qibla.direction:.1f}°")
print(f"Compass: {qibla.magnetic_direction(-8.0):.1f}°")  # synthetic -8°W
```

Sign convention (NOAA NCEI): declination is positive east of true north —
"east is least", i.e. `magnetic = true − declination_east`. Eastern values
subtract, western values (pass negative) add. This library does not look up
your declination; get it from a compass app, chart, or magnetic model. Model
values drift over time (secular variation; e.g. WMM2025, valid 2025–2030 on
its 5-year cycle), so always use a current value — any future model-backed
lookup must state its model and epoch.

## How it works (spherical default)

The default Qibla direction is calculated using spherical trigonometry:

```
direction = atan2(
    sin(Δlongitude),
    cos(latitude) × tan(Makkah_latitude) - sin(latitude) × cos(Δlongitude)
)
```

Where Makkah's coordinates are 21.4225°N, 39.8262°E.

This is a spherical-Earth model — see [Accuracy and error budget](#accuracy-and-error-budget)
for how far that assumption stretches. The 4-dp coordinate above
is canonical (~11 m); code carries extra display digits for compatibility.

Edge cases never raise: at Makkah itself the bearing is degenerate
(returns a float in [0, 360)), and at the true antipode
(~21.42°S, 140.17°W) every bearing is equidistant. Distance uses the
spherical great-circle with mean radius 6371.0088 km.

## Accuracy and error budget

The two models give slightly different answers; the differences below are
observed model differences, not a ranking — the library provides both and
which to use is up to you:

- **Bearing, spherical (default):** typically within a few arcminutes of the
  WGS84 ellipsoidal azimuth, worst case ~0.3–0.35° (reported comparisons;
  primary references to be pinned — see Citations).
- **Bearing, ellipsoidal:** Karney inverse vendored from GeographicLib —
  matches the GeographicLib 2.1 reference within the committed test goldens
  (≤1e-6° / ≤1 m).
- **Kaaba coordinates:** 4 dp (`21.4225°N, 39.8262°E`, ~11 m) is canonical;
  code carries extra display digits for compatibility. 11 m at 10,000 km is
  ~0.00006°.
- **Distance, spherical:** two stacked conventions — the radius choice
  (`6371.0088 km` here; `6371.0`/`6378.137` variants shift ~0.1–0.3%) plus
  the shape error below.
- **Distance, ellipsoidal:** WGS84 geodesic, within ≤1 m of the reference
  in the committed goldens.
- **Haversine is not "high-precision":** Haversine (like any spherical
  formula) assumes one radius, but flattening `f ≈ 1/298` means Earth's
  radii span ~0.33% from equator to pole (equatorial 6378.137 km vs polar
  6356.752 km). Spherical distances therefore have a path-dependent shape
  error, not a fixed error floor. Pinning `R` only fixes the scale
  convention, never the shape error; the ellipsoidal path comes from the
  ellipsoidal inverse, not a tuned Haversine.
- **Compass heading:** exactly as good as your declination value — model
  lookups drift with secular variation, so use a current one.

## See also

- [API Reference](api-reference/) — full API documentation
- [Citations](citations/) — attribution and references
