---
title: Changelog
description: Version history for al-falak.
---

# Changelog

## Unreleased — phase 4 (moon-sighting)

- `LunarCoordinates` (Meeus Ch.47 low-precision Moon position)
- `crescent_geometry_at_sunset` → `CrescentGeometry` (elongation, geocentric/topocentric ARCV, azimuth difference, width, illumination, moonset lag, moon age)
- `delta_t` provider (Espenak polynomial + IERS `override`; lunar path only;
  calibrated 2005–2050, `UserWarning` outside that range)
- Visibility criteria: `yallop_q`/`yallop_zone`, `odeh_v`/`odeh_class`, `is_mabims_1992`/`is_neo_mabims_2021`
- New [Moon Sighting](/moon-sighting/) guide; no breaking API changes
  from 1.1.0 (`CrescentGeometry` also exposes `sun_alt_deg` /
  `moon_alt_topo_deg` so MABIMS callers pass a true altitude, not an
  ARCV proxy; note `delta_t` validates `year` even when `override=` is set)

## 1.1.0 — phases 1–3 (geodesy, twilight markers, night divisions)

> Scope: phases 1–3 only. Phase 4 (Hijri/moon-sighting) and later remain
> for the next minor release. No breaking API changes from 1.0.0.

- Phase 1: JD/J2000 goldens + Gregorian-only note; Qibla bearing lock +
  canonical constants; `Qibla.distance_to_makkah_km`; opt-in
  `Qibla(method="ellipsoidal")` (Karney/WGS84);
  `Qibla.magnetic_direction()` hook; geodesy accuracy budget docs
- Phase 2: twilight preset goldens; `CalculationMethod.JAKIM` (20/18);
  `imsak` (Fajr − 10 min); `syuruk`/`ishraq` (+15)/`dhuha` (+28);
  `equation_of_time`/`solar_declination` helpers; `elevation_m`
  dip correction; Umm al-Qura Ramadan mode (`is_ramadan`, 120 min total)
- Phase 3: `first_third_of_the_night`;
  `night_fraction(f, start=None, end=None)`; `tahajjud_window`;
  Maghrib → next-day Fajr night definition documented
- See `CHANGES.md` for the full entry and `docs/user/` topical pages for
  behavior details

## 1.0.0 — first independent `al-falak` release

> `al-falak` is versioned independently from `adhanpy` (a separate PyPI
> package). Entries below marked `1.0.5` / `1.0.4` are upstream `adhanpy`
> lineage, kept for provenance.

- **Breaking:** Package renamed from `adhanpy` to `alfalak` (PyPI: `al-falak`)
- **Breaking:** Dedicated `AlFalakError` hierarchy replaces builtins (`AstronomicalError`, `ConfigurationError`, `ValidationError`)
- **Breaking:** Python >= 3.11 required (3.9/3.10 reached end-of-life)
- Fix hour-rollover in `rounded_minute` (`10:59:31` now rounds to `11:00`)
- Polar day/night and undefined Asr now raise with diagnostic messages
- Narrowed bare `except:` clauses
- Unknown madhab raises `ConfigurationError`; non-`CalculationMethod` method raises `TypeError`
- `PrayerTimes` accepts a `Coordinates` object as well as a tuple
- Method parameters are now copied per instance (no shared globals)
- Ship `py.typed` (PEP 561) and complete type annotations
- Define the public API surface (`__all__`-pinned)
- Add `PrayerTimes.time_for_prayer(Prayer)` accessor
- Add `Qibla` direction calculation
- Add polar-day/night estimation strategies (`PolarCircleRule`)
- Add `SunnahTimes` (middle and last third of the night)
- Add `python -m alfalak` CLI
- Validate inputs: coordinates, angles, intervals
- Build backend is now hatchling (setup.py removed)
- Dev process: ruff lint gate, `mypy --disallow-untyped-defs`

## 1.0.5

- Fix `AttributeError` when method is not provided or set to `None`

## 1.0.4

- Fix rounding of minutes function incorrectly setting 60 for minutes
- Bring support for Python 3.9
