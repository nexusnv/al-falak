# CLI Expansion Design — full public-surface coverage for the Debian/apt release

- Date: 2026-10-08
- Status: approved (§1–§6 confirmed in chat)
- Scope: widen `al-falak` CLI to cover almost all of `alfalak.__all__` ahead of a Debian release (`apt install`).
- Non-goals: new astronomy, new calendars, Python API changes. CLI-only.

## 1. Command tree (Option A: domain subcommands)

```
al-falak <subcommand> [options] [--json]
  prayer   # PrayerTimes — full CalculationParameters parity
  qibla    # Qibla direction + distance + optional magnetic heading
  sunnah   # SunnahTimes (reuses prayer flags) + night-fraction knobs
  hijri    # gregorian->hijri (existing, kept) + --reverse + --month-length
  moon-sighting  # crescent_geometry_at_sunset + all 6 criteria in one block
  astro    # low-level: lunar-position, delta-t
```

- Explicit subcommands only. Bare `al-falak --latitude...` (today's prayer
  default) becomes an error:
  `al-falak: error: a subcommand is required (did you mean 'prayer'?)`.
  Migration is a one-word fix (`prayer` insert) documented in CLI docs,
  migration notes, CHANGES, and the error text itself.
- `hijri` keeps its name and all existing flags; `--reverse` and
  `--month-length` are additive.
- `moon-sighting` couples geometry + criteria (the way `moon-sighting.md` teaches it)
  instead of five tiny subcommands. `astro` holds the two loners that do not
  fit `moon-sighting`.

## 2. Flags per subcommand

Shared: `--latitude/--longitude` canonical everywhere (`--lat/--lon` kept as
aliases only inside `hijri` for backcompat; new subcommands accept both
spellings). `--date YYYY-MM-DD` defaults to today UTC. Numeric validation
mirrors the Python API (failures → exit 2, §4).

- `prayer`: `--latitude* --longitude* --date --method (default
  MUSLIM_WORLD_LEAGUE) --madhab SHAFI|HANAFI --high-latitude-rule
  MIDDLE_OF_THE_NIGHT|SEVENTH_OF_THE_NIGHT|TWILIGHT_ANGLE --polar-rule
  NONE|NEAREST_LATITUDE|NEAREST_DAY|MAKKAH --fajr-angle --isha-angle
  --isha-interval --imsak-offset --ishraq-offset --dhuha-offset --elevation
  --ramadan (flag, UMM_AL_QURA only) --timezone ZoneInfo-name --adjust
  NAME=MIN (repeatable, NAME in imsak,fajr,sunrise,dhuhr,asr,maghrib,isha,
  ishraq,dhuha; maps to PrayerAdjustments; no syuruk slot by design).
  Explicit angles/interval override the `--method` preset exactly like
  `CalculationParameters(method=...)` then attribute assignment.
  `method_adjustments` is NOT separately exposed (comes from the preset).
- `qibla`: `--latitude* --longitude* --method spherical|ellipsoidal (default
  spherical) --declination DEG (optional; when present also print `magnetic=`
  via `magnetic_direction`)`.
- `sunnah`: all `prayer` location+parameter flags (builds PrayerTimes
  internally) + `--fraction F (0<F<1)` + `--start ISO --end ISO` (aware
  datetimes for Isha-/sunset-anchored schools, passed to `night_fraction`).
- `hijri`: existing `--date/--calendar/--country/--adjustment-days/
  --sunset-transition/--lat/--lon/--time/--offsets` unchanged +
  `--reverse HIJRI-YYYY-MM-DD` (`to_gregorian`) + `--month-length
  HIJRI-YYYY-MM`. `--calendar` (plus `--country` for mabims) stays required
  in all three hijri modes. `--reverse/--month-length` are mutually exclusive with
  `--date/--sunset-transition/--offsets` (offsets are a display-only
  Gregorian→Hijri correction; `to_gregorian` ignores them by design).
- `moon-sighting`: `--latitude* --longitude* --date* --delta-t-override SEC
  (optional IERS value)`.
- `astro lunar-position --julian-day JD` → LunarCoordinates fields.
  `astro delta-t --year DEC-YEAR [--override SEC]` → `delta_t`.

## 3. Output contract

- Default stays `key=value` lines (grep/cron-friendly), chronological where
  time applies. `--json` (every subcommand) emits the same keys as one compact
  JSON object in the same key order. Datetimes: ISO-8601 with offset (UTC
  default, else `--timezone` via `astimezone`). Floats: `repr` in text
  (`nan` lowercase), `null` in JSON. Bools: lowercase text / JSON bool.
- `prayer` (10 lines, byte-identical order/keys to today): imsak fajr sunrise
  syuruk ishraq dhuha dhuhr asr maghrib isha.
- `qibla`: `direction distance_km method` + optional `magnetic`. Text: 6dp
  direction / 3dp distance; JSON: raw floats.
- `sunnah`: `middle_of_the_night first_third_of_the_night
  last_third_of_the_night tahajjud_start tahajjud_end` (window split in two).
  With `--fraction F`: single `night_fraction=` line.
- `hijri`: forward unchanged (`hijri= calendar=`); `--reverse` →
  `gregorian=YYYY-MM-DD calendar=`; `--month-length` → `days=29|30 calendar=`.
- `moon-sighting`: geometry `arcl_deg arcv_geo_deg arcv_topo_deg sun_alt_deg
  moon_alt_topo_deg daz_deg width_arcmin illumination lag_hours moon_age_days
  moon_age_at_moonset_days used_delta_t_s sunset_jd_utc` + scores `yallop_q
  yallop_zone odeh_v odeh_class neo_mabims mabims_1992`.
- `astro`: `lunar-position` → `longitude latitude distance_km right_ascension
  declination`; `delta-t` → `delta_t=` (range UserWarning to stderr, §4).

## 4. Errors & exit codes

- Exit 0 on success, 2 on everything user-fixable. ValidationError,
  ConfigurationError, AstronomicalError (polar day/night, moon-sighting no-sunset,
  degenerate sunnah nights) all route through `parser.error(...)` → stderr +
  exit 2. No new exit codes (argparse convention; existing tests stay green).
- Messages name the flag and echo the value (e.g. `--fajr-angle 95.0 out of
  range [0, 90]`; unknown `--adjust` name lists valid names; unknown
  `--timezone` names ZoneInfo). Polar failures print the resolution hint
  (`--polar-rule ... or NONE to keep the error`).
- Warnings never fail: `delta_t` out-of-range UserWarning → stderr, value
  still prints, exit 0.
- `--help` carries the standing caveats where relevant: uqu-calendar ≠
  UMM_AL_QURA preset; tabular ±1–2d vs observed; naive `--date/--time`
  treated as UTC.

## 5. Debian artifacts + backcompat

- Layout: `__main__.py` becomes a thin dispatcher; new stdlib-only
  `src/alfalak/cli/` package with one module per subcommand
  (`prayer/qibla/sunnah/hijri/moon_sighting/astro`, shared `common.py`). No new runtime
  deps; typed, `mypy --disallow-untyped-defs` clean.
- Man page: checked-in `debian/al-falak.1` generated once from `--help` +
  static header, then hand-maintained; `docs/user/cli.md` stays the human
  source of truth. Covers all 6 subcommands + exit codes + caveats.
- Completion: static `debian/completions/al-falak.bash` +
  `al-falak.zsh` (subcommands, enum choices, file completion for `--offsets`).
  No dynamic runtime hook (offline/deterministic promise kept).
- Backcompat: only the bare-invocation default breaks (→ `prayer` insert).
  `hijri` invocation and all existing `key=value` keys unchanged. Both
  `al-falak`/`alfalak` entry points keep working.

## 6. Tests & docs

- Tests (`tests/test_cli*.py`): per-subcommand byte-identical `key=value`
  goldens (prayer Raleigh vector; qibla both methods + magnetic; sunnah block
  + `--fraction`; hijri forward/reverse/month-length; moon-sighting KL evening incl.
  yallop F / odeh D; astro lunar + delta-t) + `--json` key-parity + exit-2
  coverage for every validation gate + bare-invocation break test. Fixed
  dates/vectors (deterministic). Gates stay green: black, ruff, mypy,
  `pytest --cov-fail-under=95`.
- Docs: versionless `docs/user/cli.md` rewritten around the 6 subcommands
  (relative links only); `migration.md` gains the `bare → prayer` note;
  one-line CLI cross-pointers in api-reference/moon-sighting/qibla/
  sunnah-times pages. Frozen `docs/user/vX/` snapshots untouched. CHANGES.md
  records the break + new surface.

## Alternatives considered

- B (1:1 API mirror, ~12 subcommands): literal completeness but CLI sprawl and
  man/completion bloat; rejected.
- C (prayer/qibla/sunnah/hijri only, no moon-sighting/astro): smallest diff but
  contradicts the agreed full-scope goal; rejected.
