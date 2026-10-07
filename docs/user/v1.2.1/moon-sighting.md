---
title: Moon Sighting
description: Compute crescent geometry at sunset and apply Yallop, Odeh, and MABIMS visibility criteria.
slug: v1.2.1/moon-sighting
---

# Moon Sighting

The new crescent marks the start of a Hijri month. This library computes the
Sun–Moon geometry at local sunset and scores it against three published
visibility criteria (Yallop, Odeh, MABIMS). It does not issue religious
rulings: actual sighting also depends on weather, optics, horizon, and your
local authority — present all three scores and decide per that authority.

## Basic usage

```python
from datetime import date
from alfalak import Coordinates, crescent_geometry_at_sunset

geometry = crescent_geometry_at_sunset(
    date(2025, 2, 28), Coordinates(3.1390, 101.6869)  # Kuala Lumpur
)
print(f"elongation: {geometry.arcl_deg:.2f}°")
print(f"moonset lag: {geometry.lag_hours:.2f} h after sunset")
print(f"moon age: {geometry.moon_age_days * 24:.1f} h")
```

```
elongation: 6.17°
moonset lag: 0.41 h after sunset
moon age: 10.0 h
```

## What you get back

| Field | Meaning |
|---|---|
| `arcl_deg` | Sun–Moon elongation (angular distance) in degrees |
| `arcv_geo_deg` | Geocentric arc of vision (altitude difference) in degrees |
| `arcv_topo_deg` | Topocentric arc of vision (parallax-corrected) in degrees |
| `sun_alt_deg` | True Sun altitude at the evaluated TT instant in degrees |
| `moon_alt_topo_deg` | Topocentric Moon altitude in degrees — pass this to the MABIMS helpers |
| `daz_deg` | Sun–Moon azimuth difference in degrees |
| `width_arcmin` | Crescent width in arcminutes |
| `illumination` | Illuminated fraction of the lunar disc, [0, 1] |
| `lag_hours` | Sunset-to-moonset hours (negative = Moon sets first; `NaN` = no moonset) |
| `moon_age_days` | Days since the previous new moon (at sunset) |
| `moon_age_at_moonset_days` | Moon age at moonset (`NaN` = no moonset) — the MABIMS 1992 age input |
| `used_delta_t_s` | Delta-T value used for the TT conversion |
| `sunset_jd_utc` | Julian Date (UTC) of local sunset |

## Visibility criteria

```python
from alfalak import (
    yallop_q, yallop_zone, odeh_v, odeh_class,
    is_neo_mabims_2021, is_mabims_1992,
)

q = yallop_q(geometry.arcv_geo_deg, geometry.width_arcmin)
v = odeh_v(geometry.arcv_topo_deg, geometry.width_arcmin)
moon_alt = geometry.moon_alt_topo_deg
age_hours = geometry.moon_age_at_moonset_days * 24.0

print(yallop_zone(q))                                        # 'F' for this evening
print(odeh_class(v, geometry.arcl_deg))                      # 'D' for this evening
print(is_neo_mabims_2021(moon_alt, geometry.arcl_deg))       # False
print(is_mabims_1992(moon_alt, geometry.arcl_deg,
                     age_hours))                             # True (age branch)
```

### Yallop

`q` measures geocentric ARCV above a width-dependent limit curve. Zones
`A` (easily visible) through `F` (not visible even with a telescope):

| Zone | q |
|---|---|
| A | > 0.216 |
| B | > −0.014 |
| C | > −0.160 |
| D | > −0.232 |
| E | > −0.293 |
| F | ≤ −0.293 |

Yallop's `q` is defined at the day's best viewing time; feeding it sunset
geometry (as above) understates it, because ARCV keeps growing after sunset
as the Sun sinks faster than the Moon. Treat sunset `q` as conservative.

### Odeh

`V` measures topocentric ARCV above a width-dependent limit curve. Classes
`A` (easily visible) through `D` (invisible):

| Class | Condition |
|---|---|
| A | V ≥ 5.65 |
| B | V ≥ 2.0 |
| C | V ≥ −0.96 |
| D | otherwise, or elongation < 6.4° (Danjon floor) |

### MABIMS

Two presets from the Malaysia–Brunei–Indonesia–Singapore (MABIMS) practice:

- **1992 rule:** visible when (altitude ≥ 2° and elongation ≥ 3°) or age ≥ 8 h.
- **Neo-MABIMS 2021:** visible when altitude ≥ 3° and elongation ≥ 6.4°.

Both take the Moon's **altitude**, not ARCV — pass
`geometry.moon_alt_topo_deg` directly. Altitudes use UTC-based sidereal
time with the TT ephemeris, so no ARCV-minus-sunset proxy is needed (or
wanted: near a threshold, even arcminute differences matter — treat
boundary calls as uncertain).

The 1992 age branch is defined **at moonset** — pass
`geometry.moon_age_at_moonset_days * 24.0`, not the sunset age (they
differ by the lag, up to ~1 h). When `lag_hours` is `NaN` (no moonset
that date) the moonset age is likewise `NaN` and the age branch is
unevaluable: rely on the altitude/elongation branch instead.

## Reading the results

Check in this order:

1. **`lag_hours` first.** Negative means the Moon sets before the Sun: no
   evening window, regardless of any other score. `NaN` means no moonset
   that date (e.g. circumpolar Moon) — also no sunset-to-moonset window.
   A large positive value (many hours) means the Moon stays up well past
   sunset — a gibbous or full Moon, not a crescent window. The crescent
   signal is a *small* positive lag (minutes to about an hour).
2. **Then the criteria.** They are different models and routinely disagree
   (the Kuala Lumpur evening above passes old-MABIMS on age yet scores
   Yallop F / Odeh D). Report all three; your local authority picks.
3. **The age branch assumes post-conjunction evenings.** `moon_age_days`
   counts back to the *previous* new moon, so on the evening *before* a new
   moon it reads ~29 days and the `age ≥ 8 h` branch fires for a Moon that
   already set. Only trust that branch once conjunction has happened
   (small but growing elongation, positive lag).

## Accuracy and limitations

- **Low-precision lunar position** (Meeus Ch.47), validated against
  Example 47.a within the committed test tolerances — arcminute-level, not
  ephemeris-level. Fine for visibility scoring, not for eclipse prediction.
- **Delta-T drift:** the default Espenak polynomial runs ~5–6 s high vs
  IERS observed values by 2024–2025. Pass IERS values via `delta_t_override`
  when absolute-time accuracy matters; the used value is recorded in
  `used_delta_t_s`.
- **Hourly moon-age resolution** (±0.5 h) with a 0.1-day floor; ages under
  ~2.4 h report the floor.
- **Cost:** one call samples ~720 ephemeris evaluations over the prior
  month (~50 ms); a full-year scan is on the order of ~20 s single-threaded.
- **No weather, refraction beyond the standard sunset depression, or
  observer elevation** in this path; no "best time" search (see Yallop note).
- **Polar regions:** raises `AstronomicalError` when the Sun does not set.
  Non-`date`/`Coordinates` inputs (or a non-finite or float-overflowing
  override, e.g. a huge `int`) raise `ValidationError` (a `datetime` is accepted and its calendar date is used).
- **Delta-T range:** the default polynomial is calibrated for 2005–2050;
  other years emit a `UserWarning` and extrapolate — pass IERS values via
  `delta_t_override` when accuracy matters.

## See also

- [Hijri Converter](/v1.2.1/hijri-converter/) — Gregorian↔Hijri conversion on the observational rules
- [API Reference](/v1.2.1/api-reference/) — full API documentation
- [Errors](/v1.2.1/errors/) — error handling
- [Citations](/v1.2.1/citations/) — attribution and references
