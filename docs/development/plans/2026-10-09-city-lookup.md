# City Lookup Implementation Plan

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Add CLI-only `--city "Name,CC"` to the five location commands plus a `cities` discovery command backed by a frozen 300-entry table, with city-tz as display default on `prayer`/`sunnah` only.

**Architecture:** New pure data module `data/Cities.py` (normalize + resolve + frozen table, no argparse) with a thin CLI adapter `resolve_location` in `cli/common.py` that enforces the XOR rule and supplies coords/tz; `cities.py` lists the same table. Library API (`Coordinates`, `PrayerTimes`, `__init__.__all__`) is NOT changed. What is NOT changed: fuzzy search, network geocoding, elevation/method per city, `astro` command.

**Tech Stack:** Python 3.11+, stdlib only (dataclasses, `MappingProxyType`, `ZoneInfo`), `black` (py311), `ruff` (F,E4/E7/E9), `mypy --disallow-untyped-defs`, `pytest --cov-fail-under=95`.

**References:** Spec `docs/superpowers/specs/2026-10-09-city-lookup-design.md` §§1–6; `src/alfalak/cli/common.py:39-41` (required coords), `:87,129-135,199-204` (timezone path); `src/alfalak/cli/hijri.py:188-196` (sunset gates), `:239-268` (reverse/month-length clash); `src/alfalak/data/Coordinates.py:13-29` (validation); `src/alfalak/exceptions.py:1-16` (hierarchy); `docs/adr/0001-offline-zero-dependency-deterministic.md` (offline/zero-dep invariant); `debian/al-falak.1`, `debian/completions/al-falak.bash`, `debian/completions/al-falak.zsh`; `docs/user/cli.md`.

**Branch:** `feature/city-lookup` from `main`.

---

## Background the implementer needs

### Current state (verbatim)

`src/alfalak/cli/common.py:39-41`:
```python
def add_coord_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--latitude", "--lat", type=float, required=True)
    parser.add_argument("--longitude", "--lon", type=float, required=True)
```

`src/alfalak/cli/common.py:199-204` builds coords inline with no city concept:
```python
return PrayerTimes(
    Coordinates(args.latitude, args.longitude),
    parse_date(args.date, parser),
    calculation_parameters=params,
    time_zone=parse_timezone(args.timezone, parser),
)
```

`src/alfalak/cli/hijri.py:190-196` gates sunset coords:
```python
if args.sunset_transition:
    if args.lat is None or args.lon is None:
        raise ConfigurationError("--sunset-transition requires --lat and --lon.")
    if args.time is None:
        raise ConfigurationError("--sunset-transition requires --time.")
elif args.lat is not None or args.lon is not None:
    raise ConfigurationError("--lat/--lon require --sunset-transition.")
```

`src/alfalak/cli/common.py:209-214` `emit` handles one object only (no list, no blank-separated blocks).

### Design decisions (locked, from spec)

1. Strict `"Name,CC"` + last-comma split; validation order: no-comma → empty part → CC shape (2 ASCII alpha, takes precedence over lookup) → whitespace collapse → `name.lower()+","+cc.upper()`; `"A,B,CD"` → unknown-city.
2. Valid iff `bool(city) XOR (lat and lon both set)`; partial = exit 2; neither-case message names `--city`.
3. City tz is display default only on `prayer`/`sunnah`; explicit `--timezone` wins; `qibla`/`moon-sighting`/`hijri` discard tz (hijri stays naive-as-UTC).
4. Table 300 = OIC capitals (as-shipped = frozen pin) + UN WUP metros; GeoNames wins, header cites source + date; 4-decimal; `MappingProxyType`-backed, internal only.
5. `cities` sorted by `(c.country, c.name.lower())` byte order; text = 5-line blocks separated by one blank line, no trailing blank; JSON = one array via `json.dumps`; `--country` via `strip().upper()` + same CC rule; unmatched well-formed → empty success exit 0.
6. Unknown-city hint interpolates actual CC; malformed input gets format hint, never the `cities` hint. Corrupt table tz wraps `ZoneInfoNotFoundError → ConfigurationError` in `resolve_location`.
7. Hijri order: missing `--sunset-transition` → city+coords clash → missing `--time`; `--city` joins the reverse/month-length clash list.

---

## File Structure

- Create: `src/alfalak/data/Cities.py` — `City` frozen dataclass, `CITY_TABLE`, `normalize_city_key`, `resolve_city`.
- Modify: `src/alfalak/cli/common.py` — `add_city_args`, `resolve_location`, flip coord `required` to `False`, delegate `build_prayer_times` to it.
- Modify: `src/alfalak/cli/prayer.py`, `sunnah.py`, `qibla.py`, `moon_sighting.py` — add `--city`, consume `resolve_location` (qibla/moon discard tz).
- Modify: `src/alfalak/cli/hijri.py` — add `--city`, extend sunset gates + clash list, discard tz.
- Create: `src/alfalak/cli/cities.py` — `register()` for `cities [--country CC] [--json]`; Modify: `src/alfalak/cli/__init__.py` — register it.
- Test: `tests/test_cities.py` (create) — normalize/resolve/table invariants.
- Test: `tests/test_cli_cities.py` (create) — XOR, parity goldens, `cities` shapes, hijri gates.
- Docs: `docs/user/cli.md` — `--city` rows + `cities` section + tz notes; Modify: `debian/al-falak.1`, `debian/completions/al-falak.bash`, `debian/completions/al-falak.zsh`.

No library API change; no new deps; no `__init__.__all__` change.

---

### Task 1: Data table + pure lookup

**Files:** `src/alfalak/data/Cities.py`, `tests/test_cities.py`

**Goal:** Frozen 300-entry table with pure `normalize_city_key` / `resolve_city` per spec §1 order.

- [ ] Failing tests first in `tests/test_cities.py`: `test_normalize Variants` (comma whitespace, case, multi-space, empty name/CC, `"A,B,CD"` → key `"a,b,cd"`, bad-CC precedence), `test_unknown_interpolates_cc`, `test_table_count_300_no_dup_keys`, `test_every_tz_loads`, `test_every_latlon_validates`, `test_bad_tz_wrap` (injected bad-`City` through `resolve_location` path is in Task 2; here cover `ZoneInfo` load of every row). Run: `pytest tests/test_cities.py -v` → FAIL (module missing).
- [ ] Implement `Cities.py`: `City(name: str, country: str, latitude: float, longitude: float, timezone: str)` frozen; `CITY_TABLE` as `MappingProxyType({...})` typed `Mapping[str, City]`; 300 rows (OIC capitals + UN WUP desc, GeoNames-wins header + retrieval date, 4-decimal, `Makkah,SA` canonical spelling); `normalize_city_key(raw: str) -> str` and `resolve_city(raw: str) -> City` raising `ValidationError` per spec (unknown message interpolates `<CC>`). Verify: `pytest tests/test_cities.py -v` → PASS; `mypy src` clean.
- [ ] Regression: `pytest tests/test_cities.py -q` green. Commit: `feat(data): add frozen city table + pure lookup`.

### Task 2: Shared resolver + four commands + parity

**Files:** `src/alfalak/cli/common.py`, `src/alfalak/cli/prayer.py`, `sunnah.py`, `qibla.py`, `moon_sighting.py`, `tests/test_cli_cities.py`

**Goal:** `resolve_location` enforces XOR, supplies city tz default on `build_prayer_times` only.

- [ ] Failing tests in `tests/test_cli_cities.py`: `test_xor_both_neither_partial` (city+coords, neither, lat-only, city+lat-only → exit 2; neither message mentions `--city`), `test_parity_a_explicit_tz` and `test_parity_b_bare_city_default` for KL/Makkah/London with pinned `--date 2025-03-01 --method MUSLIM_WORLD_LEAGUE` using exact 4-decimal table coords, `test_utc_default_differs` (bare coords without tz NOT identical, pinned date), `test_unknown_city_hint` (exit 2 + `cities --country <CC>`), `test_bad_cc_format_hint`. Run: `pytest tests/test_cli_cities.py -v` → FAIL.
- [ ] Implement: `add_city_args` (optional `--city`, help states XOR + discovery); `resolve_location(*, city, lat, lon, timezone_raw, parser)` per spec (explicit values; wraps `ZoneInfoNotFoundError → ConfigurationError`); `build_prayer_times` delegates for coords+tz; `qibla`/`moon_sighting` take coords, discard tz; flip the four commands' lat/lon to `required=False`. Verify: `pytest tests/test_cli_cities.py tests/test_cli.py tests/test_cli_prayer.py tests/test_cli_qibla.py tests/test_cli_sunnah.py tests/test_cli_moon.py -q` → PASS (existing `test_cli_requires_coordinates` still exit 2).
- [ ] Regression: `black --check src/ && ruff check src/ tests/ && mypy src` green. Commit: `feat(cli): add --city resolver + wire four commands`.

### Task 3: Hijri `--city` sunset path

**Files:** `src/alfalak/cli/hijri.py`, `tests/test_cli_cities.py`

**Goal:** `--city` mirrors `--lat/--lon` gates, discards tz, joins clash list.

- [ ] Failing tests: `test_hijri_city_needs_transition`, `test_hijri_city_clashes_with_latlon`, `test_hijri_city_needs_time`, `test_hijri_city_sunset_parity` (`--city Kuala Lumpur,MY --sunset-transition --time 12:00` byte-identical to `--lat 3.1390 --lon 101.6869` same time/date/calendar), `test_hijri_city_reverse_clash`. Run: `pytest tests/test_cli_cities.py -k hijri -v` → FAIL.
- [ ] Implement in order: missing-transition check → city+lat/lon clash → missing-time (per Background gates); sunset path takes coords from `resolve_location` and discards tz; add `--city` to reverse/month-length clash list. Verify: `pytest tests/test_cli_cities.py -k hijri tests/test_cli_hijri.py -q` → PASS.
- [ ] Regression: `mypy src` clean. Commit: `feat(cli): add --city to hijri sunset path`.

### Task 4: `cities` discovery command

**Files:** `src/alfalak/cli/cities.py`, `src/alfalak/cli/__init__.py`, `tests/test_cli_cities.py`

**Goal:** `al-falak cities [--country CC] [--json]` per §1 sort + output shape.

- [ ] Failing tests: `test_cities_text_shape` (5-line blocks, sort by `(country, name.lower())`, one blank separator, no trailing blank, 4-decimal values), `test_cities_json_shape` (one array, same keys), `test_cities_country_filter` (`my` == `MY`, strip), `test_cities_bad_country_exit2`, `test_cities_unmatched_empty_success` (text empty / JSON `[]`, exit 0). Run: `pytest tests/test_cli_cities.py -k cities -v` → FAIL.
- [ ] Implement `register()` + text loop with explicit blank-line handling + `json.dumps` array path (not single-object `emit`); `register_all` gains `cities`. Verify: `pytest tests/test_cli_cities.py -k cities -q` → PASS.
- [ ] Regression: full CLI suite `pytest tests/test_cli.py tests/test_cli_cities.py -q` green. Commit: `feat(cli): add cities discovery command`.

### Task 5: Docs, man, completions + full gates

**Files:** `docs/user/cli.md`, `debian/al-falak.1`, `debian/completions/al-falak.bash`, `debian/completions/al-falak.zsh`

**Goal:** User-visible docs match behavior; no golden churn.

- [ ] Update `docs/user/cli.md`: `--city` row on each of the five location commands, `cities` section, tz-auto note scoped to `prayer`/`sunnah`, `hijri --time`-stays-UTC note, `Mecca,SA`-unknown note. Update man page: `cities` section + `--city` under the five commands + `cities` in synopsis. Update both completions: add `cities` to subcommands, `--city` to the five commands' flag lists (no value completion), `cities --country` completes the table's distinct CC set generated in the same diff (hijri `--country` stays `MY ID BN SG`); add `cities` flag/state blocks. Smoke-test: `bash -n debian/completions/al-falak.bash` and `zsh -n debian/completions/al-falak.zsh` exit 0; `man --warnings -l debian/al-falak.1` clean (or `groff -man -Tascii ... > /dev/null` if `man` unavailable).
- [ ] Final gates: `black --check src/` → `ruff check src/ tests/` → `mypy src` → `pytest --cov-fail-under=95` all green; confirm no existing prayer golden churn (`pytest tests/test_cli_prayer.py tests/test_prayer_times.py -q` PASS without golden edits). Commit: `docs(cli): document --city + cities`.

---

## Self-review

- Spec coverage: identifier order + H1 example (T1), XOR partials (T2), tz wrap + discard (T2/T3), hijri order + clash (T3), sort/emit/country (T4), parity dates + DST (T2), man/completions (T5). All covered.
- Placeholder scan: clean — every task names files, test names, and `pytest` verifies.
- Type consistency: `City` fields, `CITY_TABLE: Mapping[str, City]`, `normalize_city_key(str) -> str`, `resolve_city(str) -> City`, `resolve_location(...) -> (Coordinates, ZoneInfo|None)` match across tasks.
- Momus dry: references exist (`common.py`, `hijri.py`, `Coordinates.py`, `exceptions.py`, ADR, spec, debian artifacts); each task startable independently after T1; QA has tool + steps + expected PASS.
