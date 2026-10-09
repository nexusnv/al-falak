# City Lookup Design — CLI `--city` + `cities` (300 cities)

Date: 2026-10-09
Status: approved (brainstorming 3/3 sections)
Baseline: `src/alfalak/cli/common.py:39-41` (`--latitude/--lon` required on all location commands); `--timezone` already implemented (`common.py:87,129-135,199-204`, `PrayerTimes.py:517-528`); zero-dep offline invariant (`docs/adr/0001-offline-zero-dependency-deterministic.md`).

## 1. Decisions locked during brainstorming

- Scope: CLI-only first. No `alfalak.__init__` / `Coordinates` API change. `--city` on all location commands: `prayer`, `sunnah`, `qibla`, `moon-sighting`, plus `hijri` (only with `--sunset-transition`, mirroring `--lat/--lon` gates).
- Identifier: strict `"Name,CC"` required, e.g. `--city "Kuala Lumpur,MY"`. Bare `"Kuala Lumpur"` rejected with hint showing `,MY` form. Normalization: strip, collapse inner whitespace, lowercase name + uppercase 2-letter CC. No fuzzy matching, no network calls.
- Table: 300 entries = all OIC capitals + largest world metros to fill. Source-cited header (GeoNames/Natural Earth + retrieval date). 4-decimal coords.
- Storage: embedded frozen dict in `src/alfalak/data/Cities.py` (`CITY_TABLE: dict[str, City]`), stdlib-only, ~15KB. Rejected: JSON resource (packaging overhead), minimal spike in `common.py` (throwaway given all-commands scope).
- Timezone: city IANA zone becomes display default; explicit `--timezone` wins; else UTC (existing default).
- Conflict: `--city` XOR explicit coords = hard error exit 2. Neither = exit 2 (preserves "required" feel).
- Discovery: single top-level `al-falak cities [--country MY] [--json]`, sorted by country,city, showing coords + timezone for transparency. No per-command `--list-cities` flags.

## 2. Module layout

- New `src/alfalak/data/Cities.py`: `class City(frozen dataclass): name, country, latitude, longitude, timezone`; `CITY_TABLE` keyed by `"kuala lumpur,my"`; `resolve_city(raw) -> City | None` (pure normalization, no argparse).
- Modify `src/alfalak/cli/common.py`: `add_city_args(parser)` (`--city` optional); `resolve_location(args, parser) -> (Coordinates, ZoneInfo|None)` — enforces XOR, unknown-city error with `cities --country CC` hint, returns city tz as default; `build_prayer_times` + `qibla`/`moon_sighting`/`hijri` sunset path consume it. Flip `prayer`/`sunnah`/`qibla`/`moon-sighting` `--latitude/--longitude` to `required=False` with manual presence check (`hijri --lat/--lon` stay optional as today)
- New `src/alfalak/cli/cities.py`: `register()` for `cities [--country CC] [--json]`; text lines `city=|country=|latitude=|longitude=|timezone=`, JSON list of same objects.
- Modify `src/alfalak/cli/__init__.py`: register `cities`.
- Example entry: `City(name="Kuala Lumpur", country="MY", latitude=3.1390, longitude=101.6869, timezone="Asia/Kuala_Lumpur")`.

## 3. CLI UX + data flow

```
--city "Kuala Lumpur,MY" --timezone Asia/Kuala_Lumpur (explicit wins)
  → resolve_city → Coordinates(3.1390,101.6869) + default tz
  → PrayerTimes(..., time_zone=explicit or city-tz or None→UTC)
  → existing ISO-8601 emit (unchanged)
```

- `prayer|qibla|sunnah|moon-sighting --city 'Kuala Lumpur,MY'`; hijri: `--city` requires `--sunset-transition` (exit 2 otherwise, same as `--lat/--lon`).
- Quoting needed for spaced names; `kuala  LUMPUR,my` accepted via normalization.
- `cities --country my` filters case-insensitively; `--json` emits same list as one array.

## 4. Errors + boundaries

- Both `--city` + coords → `parser.error` exit 2. Neither → exit 2.
- Unknown `--city` → exit 2 + `try 'al-falak cities --country CC'` hint. No Levenshtein suggestions (deterministic).
- Missing `,CC` → exit 2 with format hint. Invalid CC (not 2-alpha) → exit 2.
- `hijri --city` without `--sunset-transition` → exit 2; partial `--lat` without `--lon` (or vice versa) still exit 2 as today; `--city` with either `--lat`/`--lon` → exit 2.
- City tz string invalid (should not happen; table is frozen) → internal `ConfigurationError`, covered by test asserting every tz loads via `ZoneInfo`.
- `hijri --city` without `--sunset-transition` → exit 2; with `--sunset-transition` still requires `--time` as today.

## 5. Testing + docs

- Unit: normalization variants, unknown city, XOR both/neither, missing `,CC`, `--country` filter case-insensitivity, every table tz loads.
- Golden parity (3 cities: Kuala Lumpur,MY / Makkah,SA / London,GB): `prayer --city` byte-identical to explicit `--latitude/--longitude` (+ city-tz default vs explicit `--timezone` override case).
- `cities` text/json shape + sort order; coverage gate `pytest --cov-fail-under=95`; gates `black --check src/`, `ruff check src/ tests/`, `mypy src`.
- Docs: `docs/user/cli.md` (`--city` row on each location command + `cities` section + tz-auto note); man page + completions updated (city names not completed — only `--country` values).

## 6. Out-of-scope + acceptance

Out: library `Coordinates.from_city`, fuzzy/prefix search, network geocoding, per-city elevation, auto-`--method` per country, shell completion of 300 names.
Acceptance: `--city` works on all five location paths, `cities` lists 300 with coords+tz, all gates green, no new deps, no prayer golden churn (city path resolves to identical `Coordinates`).
