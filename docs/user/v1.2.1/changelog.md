---
title: Changelog
description: Version history for al-falak.
---

# Changelog

## 1.2.1 — hotfix (finite-real overflow, Qibla self doc)

* `require_finite_real` maps float-overflowing huge `int`s to
  `ValidationError` (was bare `OverflowError`); covers `delta_t`,
  `yallop_*`, `odeh_*`, `is_*mabims*`, `LunarCoordinates`.
* `Qibla` self-point docs now state both models return `180.0`
  (was `spherical ~180 vs ellipsoidal 0`).

## 1.2.0 — phases 4–5 (moon-sighting, hijri converter)

One behavioral breaking change from 1.1.0: `Coordinates` is now frozen —
assigning to its fields raises `FrozenInstanceError`. Replace the instance
instead of mutating it (e.g. `coords = Coordinates(new_lat, new_lon)`).

### Hijri converter (phase 5)

- `HijriDate` (frozen, ordered value type with zero-padded `isoformat()`)
- `HijriCalendar` ABC + `get_calendar` factory (`"tabular"`, `"uqu"`, `"mabims"`; `country` required iff `mabims`, `adjustment_days` in [-2, 2] iff `tabular`, else `ConfigurationError`)
- `TabularCalendar` (arithmetic Type IIa / "Kuwaiti" pattern; `adjustment_days` shift; epoch 1 Muharram 1 AH = 622-07-19 proleptic)
- `UmmAlQuraCalendar` (1423H month-start rule at Makkah; support floor Gregorian 2002-03-15; modern targets walk from the verified 1445H anchor; distinct from the `UMM_AL_QURA` prayer preset)
- `MabimsCalendar` (Neo-MABIMS 2021 at per-country `MY`/`ID`/`BN`/`SG` proxies; forward-only walk from the 1 Muharram 1445H anchor; announced dates may differ by ±1 day by design)
- `gregorian_to_hijri` bridge (civil-date default; `change_at_sunset=True` rolls over at Maghrib with naive-as-UTC semantics and unwrapped polar `AstronomicalError`)
- `OffsetStore` (per-month `"YYYY-MM"` shifts in {-2, -1, 1, 2} from dict/JSON, applied once and last; `to_gregorian` ignores it)
- `hijri` CLI subcommand (two-line `hijri=`/`calendar=` output; `--country`, `--adjustment-days`, `--sunset-transition`, `--offsets`)
- New [Hijri Converter](/hijri-converter/) guide; additive additions only
- Offline/zero-dependency/deterministic computation recorded as project invariants (see `docs/adr/0001-offline-zero-dependency-deterministic.md`)

### Moon-sighting (phase 4)

- `LunarCoordinates` (Meeus Ch.47 low-precision Moon position)
- `crescent_geometry_at_sunset` → `CrescentGeometry` (elongation, geocentric/topocentric ARCV, azimuth difference, width, illumination, moonset lag, moon age)
- `delta_t` provider (Espenak polynomial + IERS `override`; lunar path only;
  calibrated 2005–2050, `UserWarning` outside that range)
- Visibility criteria: `yallop_q`/`yallop_zone`, `odeh_v`/`odeh_class`, `is_mabims_1992`/`is_neo_mabims_2021`
- New [Moon Sighting](/moon-sighting/) guide; additive additions only
  (`CrescentGeometry` also exposes `sun_alt_deg` /
  `moon_alt_topo_deg` so MABIMS callers pass a true altitude, not an
  ARCV proxy; note `delta_t` validates `year` even when `override=` is set)
- Correctness fixes from PR review: `yallop_q` applies the /10 scale of
  Yallop (1997) eq. 6.1; lunar position applies the E-factor and additive
  corrections of Meeus Ch.47; sidereal time runs on UTC with the ephemeris
  on TT; `CrescentGeometry.moon_age_at_moonset_days` feeds the MABIMS 1992
  age branch defined at moonset

- `Coordinates` is now frozen: the shared `MAKKAH` singleton cannot be
  mutated in place (closes #47). Callers that assigned to
  `latitude`/`longitude` must construct a new instance instead
  (raises `FrozenInstanceError` otherwise)

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
