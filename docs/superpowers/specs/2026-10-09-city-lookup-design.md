# City Lookup Design — CLI `--city` + `cities` (300 cities)

Date: 2026-10-09
Status: approved (brainstorming 3/3 sections)
Baseline: `src/alfalak/cli/common.py:39-41` (`--latitude/--lon` required on all location commands); `--timezone` already implemented (`common.py:87,129-135,199-204`, `PrayerTimes.py:517-528`); zero-dep offline invariant (`docs/adr/0001-offline-zero-dependency-deterministic.md`).

## 1. Decisions locked during brainstorming

- Scope: CLI-only first. No `alfalak.__init__` / `Coordinates` API change. `--city` on all location commands: `prayer`, `sunnah`, `qibla`, `moon-sighting`, plus `hijri` (only with `--sunset-transition`, mirroring `--lat/--lon` gates).
- Identifier: strict `"Name,CC"` required, e.g. `--city "Kuala Lumpur,MY"`. Bare `"Kuala Lumpur"` (no comma) rejected with a generic format hint (`expected NAME,CC, e.g. --city "Kuala Lumpur,MY"` — the hint never infers a country). Normalization (exact, in this order): `raw.strip()` → split on the **last** comma (no comma → format error) → `name_part.strip()` / `cc_part.strip()` (either empty → format error) → CC shape check (not exactly 2 ASCII alpha → invalid-CC error, takes precedence over lookup) → collapse all internal whitespace runs (`\s+` → single space) in the name → key = `name.lower() + "," + cc.upper()`. `"Kuala Lumpur , MY"` and `kuala  LUMPUR,my` both key to `"kuala lumpur,my"`. Extra commas use the last comma as separator and surface as unknown-city when the CC part is well-formed (name may not itself contain a comma — `"A,B,CD"` → name `"A,B"`, CC `"CD"`, which never matches a table key). No fuzzy matching, no network calls.
- Table: 300 pinned entries = all OIC capitals (deduplicated by normalized key; the table as-shipped is the frozen pin for disputed capitals) + largest world metros by population (UN WUP desc) until 300. Source-cited header (GeoNames wins on disagreement, Natural Earth as fallback, + retrieval date). 4-decimal coords (~11 m, well within minute-rounded prayer output tolerance). Count asserted `== 300` in tests; any future table change updates spec + goldens together.
- Storage: embedded table in `src/alfalak/data/Cities.py` (`City` frozen dataclass with `name: str, country: str, latitude: float, longitude: float, timezone: str`; `CITY_TABLE` as `MappingProxyType` dict exposed as read-only `Mapping[str, City]`, stdlib-only, ~15KB, internal only — NOT added to `alfalak.__init__.__all__` or `alfalak.data.__all__`). Rejected: JSON resource (packaging overhead), minimal spike in `common.py` (throwaway given all-commands scope).
- Timezone: city IANA zone becomes display default **only on the `prayer`/`sunnah` (`build_prayer_times`) path**; explicit `--timezone` wins; else UTC (existing default). `qibla` has no timezone concept and `moon-sighting` outputs JD/floats — city tz is ignored there. `hijri --time` stays naive-treated-as-UTC (see `hijri.py` epilog); `--city` on hijri supplies coordinates for sunset rollover only, never a timezone.
- Conflict: valid iff `bool(city) XOR (lat is not None and lon is not None)`; every other combination (both, neither, or partial coords with or without `--city`) = hard error exit 2. The neither-case message names `--city` as the alternative (preserves "required" feel with guidance).
- Discovery: single top-level `al-falak cities [--country MY] [--json]`, sorted by `(country, city-lower)` tuple in byte order — i.e. `key=(c.country, c.name.lower())`, independent of the `"name,cc"` table key — so `Tripoli,LY` vs `Tripoli,LB` is deterministic, showing coords + timezone for transparency. No per-command `--list-cities` flags.

## 2. Module layout

- New `src/alfalak/data/Cities.py`: `class City(frozen dataclass): name: str, country: str, latitude: float, longitude: float, timezone: str`; `CITY_TABLE` (`MappingProxyType`-backed, typed `Mapping[str, City]`) keyed by `"kuala lumpur,my"`; `normalize_city_key(raw) -> str` (pure normalization per §1 order, raises `ValidationError` with `expected NAME,CC` message on missing comma / empty part / bad CC); `resolve_city(raw) -> City` (calls normalize, raises `ValidationError` with `unknown --city '<input>' ... try 'al-falak cities --country <CC>'` interpolating the actual uppercased CC part on miss — pure, no argparse; callers map `ValidationError` → `parser.error`). `City`/`CITY_TABLE` stay internal (no `__init__` export).
- Modify `src/alfalak/cli/common.py`: `add_city_args(parser)` (`--city` optional, help states the XOR + `cities` discovery); `resolve_location(*, city, lat, lon, timezone_raw, parser) -> (Coordinates, ZoneInfo|None)` taking **explicit values, not `args`** — callers pass `args.latitude`/`args.longitude` on `prayer`/`sunnah`/`qibla`/`moon-sighting` and `args.lat`/`args.lon` on `hijri` (this bridges the `latitude` vs `lat` attribute split). Enforces the §1 XOR rule (partial coords = error), maps `resolve_city` `ValidationError` → `parser.error` exit 2, returns city tz as default (`explicit --timezone` wins, validated via existing `parse_timezone`; wraps `ZoneInfoNotFoundError` on a corrupt table row into `ConfigurationError` so the CLI keeps its exit-2 contract). `build_prayer_times` delegates to it for coords+tz; `qibla`/`moon_sighting` take the `Coordinates` and discard the tz; `hijri` sunset path takes the `Coordinates` and discards the tz (never wired into the naive bridge). Flip `prayer`/`sunnah`/`qibla`/`moon-sighting` `--latitude/--longitude` to `required=False` with manual presence check (`hijri --lat/--lon` stay optional as today). `hijri` `run()` `--reverse`/`--month-length` clash list gains `--city` (same as `--lat`/`--lon`).
- New `src/alfalak/cli/cities.py`: `register()` for `cities [--country CC] [--json]`; text mode prints one 5-line `city=|country=|latitude=|longitude=|timezone=` block per city in §1 sort order (blocks separated by a single blank line, no trailing blank; `city=` value is the `Name,CC` display form; lat/lon print the stored 4-decimal values); `--json` emits one array of the same objects via `json.dumps` (not the single-object `emit()`). `--country` is normalized by `strip().upper()` with the same 2-ASCII-alpha rule (`cities --country my` == `MY`); malformed `--country` → exit 2; well-formed but unmatched `--country` → empty success (text: no output, JSON: `[]`, exit 0).
- Modify `src/alfalak/cli/__init__.py`: register `cities`.
- Example entry: `City(name="Kuala Lumpur", country="MY", latitude=3.1390, longitude=101.6869, timezone="Asia/Kuala_Lumpur")`.

## 3. CLI UX + data flow

```
--city "Kuala Lumpur,MY" --timezone Asia/Kuala_Lumpur (explicit wins)
  → resolve_city → Coordinates(3.1390,101.6869) + default tz
  → PrayerTimes(..., time_zone=explicit or city-tz or None→UTC)  # prayer/sunnah only
  → existing ISO-8601 emit (unchanged)
  (qibla/moon-sighting/hijri: city supplies Coordinates only; tz ignored)
```

- `prayer|qibla|sunnah|moon-sighting --city 'Kuala Lumpur,MY'`; hijri: `--city` requires `--sunset-transition` (exit 2 otherwise, same as `--lat/--lon`).
- Quoting needed for spaced names; `kuala  LUMPUR,my` accepted via normalization.
- `cities --country my` filters case-insensitively; unmatched well-formed `--country` → empty success (no text lines / `[]`); `--json` emits same list as one array.

## 4. Errors + boundaries

- Both `--city` + coords, neither, or partial coords (with or without `--city`) → `parser.error` exit 2, per the §1 rule.
- Unknown `--city` (well-formed but no table hit) → exit 2 + `try 'al-falak cities --country <CC>'` with the actual CC interpolated. Malformed input (missing `,CC`, empty part, bad CC shape) → exit 2 with the format hint instead — never the `cities` hint. No Levenshtein suggestions (deterministic).
- `hijri` gate order with `--city` (mirrors `--lat`/`--lon`): `--city` without `--sunset-transition` → exit 2 first; then `--city` with either `--lat`/`--lon` → exit 2; then with `--sunset-transition`, `--time` still required as today. Partial `--lat` without `--lon` (or vice versa) still exit 2 as today. `hijri --city` combined with `--reverse`/`--month-length` → exit 2 via the existing mutual-exclusion clash list (same as `--lat`/`--lon`).
- City tz string invalid (should not happen; table is frozen) → wrapped into `ConfigurationError` inside `resolve_location` (corrupt-table internal; surfaces as exit 2 via the existing `AlFalakError → parser.error` path). Tests assert every table tz loads via `ZoneInfo` plus one injected bad-`City` unit test for the wrap so the branch is covered.

## 5. Testing + docs

- Unit: normalization variants (comma whitespace, case, multi-space, empty name/CC, extra commas with well-formed CC → unknown-city, bad-CC precedence over lookup), unknown city (with interpolated `--country` hint), XOR both/neither/partial, missing `,CC`, `--country` filter case-insensitivity + whitespace strip + malformed `--country` + unmatched `--country` empty success, every table tz loads + injected bad-tz wrap, every table lat/lon passes `Coordinates` validation, table count `== 300` with no duplicate normalized keys.
- Golden parity (3 cities: Kuala Lumpur,MY / Makkah,SA canonical spelling — `Mecca,SA` is intentionally unknown / London,GB), each in two cases with pinned `--date` + `--method` using the exact 4-decimal table values on the explicit side: (a) `prayer --city X` + explicit `--timezone <city-tz>` byte-identical to explicit `--latitude/--longitude` + same `--timezone`; (b) bare `prayer --city X` (city-tz default) byte-identical to explicit coords + explicit `--timezone <city-tz>`. Bare coords without `--timezone` (UTC default) are intentionally NOT identical — assert the difference in one pinned-date case to lock the default behavior (pin the date to avoid DST ambiguity on `Europe/London`).
- `cities` text shape (5-line block per city + blank separator, sort order) / json shape (one array); coverage gate `pytest --cov-fail-under=95`; gates `black --check src/`, `ruff check src/ tests/`, `mypy src`.
- Docs: `docs/user/cli.md` (`--city` row on each location command + `cities` section + tz-auto note scoped to `prayer`/`sunnah` + `hijri --time`-stays-UTC note); man page + completions updated (city names not completed — only `--country` values, generated from the table's distinct country set so they cannot rot).

## 6. Out-of-scope + acceptance

Out: library `Coordinates.from_city`, fuzzy/prefix search, network geocoding, per-city elevation, auto-`--method` per country, shell completion of 300 names.
Acceptance: `--city` works on all five location paths, `cities` lists 300 with coords+tz, all gates green, no new deps, no prayer golden churn (city path resolves to identical `Coordinates`).
