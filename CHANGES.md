# Changelog

## Unreleased

* CLI expansion to six explicit subcommands covering almost all of
  `alfalak.__all__`: `prayer` (full `CalculationParameters` parity),
  `qibla` (spherical/ellipsoidal + optional magnetic heading),
  `sunnah` (night markers + `--fraction`/`--start`/`--end`),
  `hijri` (kept flags plus `--reverse` Hijri→Gregorian and
  `--month-length`), `moon-sighting` (crescent geometry + Yallop/Odeh/
  MABIMS scores in one block), and `astro` (`lunar-position`,
  `delta-t`).
* Every subcommand accepts `--json` (same keys, one compact JSON
  object, same key order).
* Breaking: the bare invocation (`al-falak --latitude ...`, previously
  the prayer-times default) now exits with code 2 — insert `prayer`
  (`al-falak prayer --latitude ...`). Forward `hijri` invocations (flags
  after the subcommand) and all existing `key=value` keys/order are
  unchanged; flags before the subcommand (e.g. `--date X hijri ...`) now
  exit with code 2.
* Docs: `docs/user/cli.md` rewritten around the six subcommands;
  `migration.md` notes the `bare → prayer` fix.

## 1.2.1 — 2026-10-07 (hotfix: finite-real overflow, Qibla self doc)

* Fix: `require_finite_real` now maps `float()` `OverflowError`/`ValueError`
  (e.g. huge `int`s like `10**1000` that do not fit in a `float`) to
  `ValidationError`, per the `AlFalakError` contract. Affects `delta_t`,
  `yallop_q`/`yallop_zone`, `odeh_v`/`odeh_class`, `is_neo_mabims_2021`/
  `is_mabims_1992`, and `LunarCoordinates` (all funnel through the same
  helper). Previously leaked bare `OverflowError`.
* Docs: `Qibla` self-point now states both models return `180.0` at the
  exact self point (was `spherical ~180.0 vs ellipsoidal 0.0`); `qibla.md`,
  `errors.md`, `api-reference.md`, and `moon-sighting.md` synced to the
  landed behavior (float-overflowing inputs raise `ValidationError`).
* Tests: regression coverage for huge-int `ValidationError` and both-models
  `180.0` self bearing. Full suite green.

## 1.2.0 — 2026-10-06 (phases 4–5: moon-sighting, Hijri converter)

> Scope: this release lands milestone phases 4–5 (lunar ephemeris and
> visibility criteria, Hijri calendars and sunset bridge). One behavioral
> breaking change from 1.1.0: `Coordinates` is now frozen — assigning to
> its fields raises `FrozenInstanceError`; construct a new instance
> instead of mutating (e.g. `coords = Coordinates(new_lat, new_lon)`).

* Phase 4 — moon-sighting:
  * Add `LunarCoordinates` (Meeus Ch.47 low-precision Moon position).
  * Add `crescent_geometry_at_sunset` → `CrescentGeometry` (elongation,
    geocentric/topocentric ARCV, azimuth difference, width,
    illumination, moonset lag, moon age; evaluated at local sunset,
    raises on polar no-sunset).
  * Add `delta_t` provider (Espenak polynomial + IERS `override`;
    lunar path only; calibrated 2005–2050, `UserWarning` outside).
  * Add visibility criteria: `yallop_q`/`yallop_zone` (Yallop 1997
    eq. 6.1 with /10 scale), `odeh_v`/`odeh_class` (Danjon floor),
    `is_mabims_1992`/`is_neo_mabims_2021` (topocentric altitude input,
    not ARCV proxy).
  * Document the moon-sighting guide (`docs/user/moon-sighting.md`).
* Phase 5 — Hijri converter:
  * Add `HijriDate` (frozen, ordered value type with zero-padded
    `isoformat()`).
  * Add `HijriCalendar` ABC + `get_calendar` factory (`"tabular"`,
    `"uqu"`, `"mabims"`; `country` required iff `mabims`,
    `adjustment_days` in [-2, 2] iff `tabular`).
  * Add `TabularCalendar` (arithmetic Type IIa / "Kuwaiti" pattern;
    epoch 1 Muharram 1 AH = 622-07-19 proleptic).
  * Add `UmmAlQuraCalendar` (1423H month-start rule at Makkah;
    support floor Gregorian 2002-03-15; modern targets walk from the
    verified 1445H anchor).
  * Add `MabimsCalendar` (Neo-MABIMS 2021 at per-country `MY`/`ID`/
    `BN`/`SG` proxies; forward-only walk from the 1 Muharram 1445H
    anchor; announced dates may differ by ±1 day by design).
  * Add `gregorian_to_hijri` bridge (civil-date default;
    `change_at_sunset=True` rolls over at Maghrib; naive-as-UTC
    semantics; unwrapped polar `AstronomicalError`).
  * Add `OffsetStore` (per-month `"YYYY-MM"` shifts in {-2, -1, 1, 2}
    from dict/JSON, applied once and last; `to_gregorian` ignores it).
  * Add `hijri` CLI subcommand (two-line `hijri=`/`calendar=` output;
    `--country`, `--adjustment-days`, `--sunset-transition`,
    `--offsets`).
  * Document the converter guide (`docs/user/hijri-converter.md`) and
    record offline/zero-dependency/deterministic computation as
    project invariants (`docs/adr/0001-offline-zero-dependency-deterministic.md`).
* Fix: `Coordinates` is now a frozen dataclass — the shared `MAKKAH`
  singleton can no longer be mutated in place (closes #47). Callers
  that assigned to `latitude`/`longitude` must construct a new instance
  instead (raises `FrozenInstanceError` otherwise).
* Docs: `docs/user/` topical pages cover every new calendar/criterion
  (`moon-sighting`, `hijri-converter`, `api-reference`, `cli`,
  `citations`, `errors`); `docs/user/v1.0.0/` frozen snapshot untouched.
* Tests: full suite green, `black --check src/` → `ruff check src/ tests/`
  → `mypy src` → `pytest --cov-fail-under=95` green.

## 1.1.0 — 2026-10-03 (phases 1–3: geodesy, twilight markers, night divisions)

> Scope: this release lands milestone phases 1–3 only (core geodesy,
> solar/twilight markers, night divisions). Phase 4 (Hijri/moon-sighting:
> lunar ephemeris, Yallop/Odeh, MABIMS) and phase 5+ remain for the next
> minor release. No breaking API changes from 1.0.0.

* Phase 1 — geodesy and calendrical hardening:
  * Lock JD/J2000 goldens (Meeus Ch.7) and document the Gregorian-only
    limitation (no Julian-calendar branch; correct for prayer use).
  * Lock Qibla spherical bearing goldens; move `MAKKAH` into canonical
    `data/Constants.py` (4-dp canonical `21.4225N, 39.8262E`, 7-dp digits
    kept for cross-port compat); document spherical-vs-ellipsoidal error
    (typically few arcmin, worst ~0.3–0.35°) and degenerate
    Makkah-to-self/antipode behavior (float in [0,360), no raise).
  * Add `Qibla.distance_to_makkah_km` (haversine `atan2` form,
    `R = 6371.0088 km` IUGG mean radius pinned).
  * Add opt-in `Qibla(method="ellipsoidal")` Karney inverse on WGS84
    (`astronomy/Geodesy.py`); spherical stays default; unknown method
    raises `ConfigurationError`.
  * Add `Qibla.magnetic_direction(declination_deg)` pure hook
    (`true − declination_east`, NOAA east-positive; model lookup stays
    caller-side; future WMM/IGRF provider must take `(model, epoch)`).
  * Document geodesy accuracy budget, Kaaba precision, and why Haversine
    alone is not high-precision (`docs/user/qibla.md`).
* Phase 2 — twilight and prayer markers:
  * Lock one golden day per twilight preset (all 11 + `NONE`); pin
    `MWL 18/17`, `EGYPTIAN 19.5/17.5`, `NORTH_AMERICA 15/15 (ISNA)`,
    `SINGAPORE 20/18 (MUIS)`; record Dubai-offset provenance and the
    Qatar 18-vs-18.5 source conflict as doc notes.
  * Add `CalculationMethod.JAKIM` (20/18, identical angles to `SINGAPORE`
    by design; Malay naming + zone metadata; verified against Takwim
    Malaysia Kuala Lumpur/Kota Kinabalu).
  * Add `imsak` marker (`Fajr − imsak_offset`, default 10 min,
    configurable); new `Prayer.IMSAK`, `PrayerAdjustments.imsak`,
    `time_for_prayer` support, CLI row.
  * Add `syuruk`/`ishraq`/`dhuha` markers derived from sunrise
    (`syuruk == sunrise`; `ishraq` default +15 min; `dhuha` window-start
    default +28 min, single Malaysian source; `dhuha_offset >=
    ishraq_offset` validated); new `Prayer` members, no `syuruk`
    adjustment slot by design (sunrise flows through).
  * Expose `equation_of_time(jd)` / `solar_declination(jd)` thin wrappers
    (Meeus Ch.28/Ch.25; transit path unchanged).
  * Add `elevation_m` observer correction (dip `0.0293°·√h_m`, metres;
    sunrise/sunset/Maghrib only; default 0 = unchanged goldens).
  * Add Umm al-Qura Ramadan mode (`is_ramadan: bool`, `UMM_AL_QURA`
    only; 120 min total vs 90 otherwise, not additive +30).
  * Document angle-vs-interval Isha, DUBAI/MSC offsets, seasonal
    twilight, and `HighLatitudeRule`/`PolarCircleRule` interaction.
* Phase 3 — night divisions:
  * Add `first_third_of_the_night` (Maghrib + ⅓ night).
  * Add generic `night_fraction(f, start=None, end=None)`
    (`0 < f < 1`, `int`/`float`/`Fraction`/`Decimal`; explicit aware
    anchors for Isha-anchored/sunset-anchored schools; UTC math,
    minute-rounded, `ValidationError` on bad fraction/interval).
  * Add `tahajjud_window` (`last_third → next-day Fajr`); existing
    `middle`/`last_third` become thin wrappers.
  * Night is Maghrib → next-day Fajr (offsets included); document rounding
    order and anchor alternatives (`docs/user/sunnah-times.md`).
* Docs: `docs/user/` topical pages cover every new marker/parameter
  (`calculation-methods`, `qibla`, `sunnah-times`, `api-reference`,
  `cli`, `citations`); `docs/user/v1.0.0/` frozen snapshot untouched.
* Tests: 653 collected; `black --check src/` → `ruff check src/ tests/`
  → `mypy src` → `pytest --cov-fail-under=95` green.

## 1.0.0 — 2026-09-30 (first independent `al-falak` release)

> `al-falak` is versioned independently from `adhanpy` (a separate PyPI
> package). Entries below marked `1.0.5` / `1.0.4` are upstream `adhanpy`
> lineage, kept for provenance.

* Breaking: package renamed from `adhanpy` to `alfalak` (PyPI: `al-falak`).
* Breaking: dedicated `AlFalakError` hierarchy replaces builtins
  (`AstronomicalError`, `ConfigurationError`, `ValidationError`);
  messages unchanged. The internal isha-interval `ValueError` is untouched.
* Breaking: Python `>=3.11` required (3.9/3.10 reached end-of-life).
* Fix hour-rollover in `rounded_minute` (`10:59:31` now rounds to `11:00`),
  use half-up rounding at exactly 30 seconds, and zero microseconds.
* Polar day/night and undefined Asr now raise `AstronomicalError` with a
  diagnostic message instead of an empty `RuntimeError`.
* Narrowed bare `except:` clauses (`Astronomical.corrected_hour_angle`,
  `PrayerTimes._set_isha`).
* Unknown madhab raises `ConfigurationError`; non-`CalculationMethod` method raises
  `TypeError` (`None` still means `NONE`).
* `PrayerTimes` accepts a `Coordinates` object as well as a
  `(latitude, longitude)` tuple; fixed `src/example` header using the wrong date.
* Method parameters are now copied per instance: mutating one
  `CalculationParameters.method_adjustments` no longer leaks into
  subsequently created instances.
* Ship `py.typed` (PEP 561) and complete type annotations; the package
  is now `mypy --disallow-untyped-defs` clean with no runtime changes.
* Define the public API surface (`alfalak.__all__` plus `calculation`
  and `data` re-exports) and add `PrayerTimes.time_for_prayer(Prayer)`.
* Add `Qibla` direction calculation ported from upstream adhan.
* Add polar-day/night estimation strategies (`PolarCircleRule`:
  `NEAREST_LATITUDE` by default, `NEAREST_DAY`, `MAKKAH`, `NONE` to
  keep the old raise).
* Add `SunnahTimes` (middle and last third of the night) ported
  from upstream adhan.
* Add `python -m alfalak` CLI printing ISO-8601 UTC markers.
* Validate inputs: coordinates within [-90, 90]/[-180, 180], angles
  within [0, 90], non-negative Isha interval.
* Build backend is now hatchling (setup.py removed); CI covers
  Python 3.11–3.14.
* Asr is clamped to Dhuhr when polar-boundary geometry would place
  it earlier (total marker ordering now holds everywhere).
* Dev process: ruff lint gate (`F`, `E4/E7/E9`) over `src/` and
  `tests/`, and `mypy --disallow-untyped-defs` enforced via config.

## v1.0.5
* Fix [#16](https://github.com/alphahm/adhan/issues/16) where method is either not provided or
explicitly set to `None` when initialising `CalculationParameters` results in an `AttributeError`
in `PrayerTimes`

## v1.0.4
* Fix [#4](https://github.com/alphahm/adhan/issues/4) where rounding of minutes function tried to
incorrectly set 60 for minutes on a datetime object.
* Bring support for Python 3.9
