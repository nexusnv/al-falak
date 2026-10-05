# Phase 5 Hijri Converter Implementation Plan (issue #61 deferred-compute noted)

> **For workers:** Execute task-by-task via TDD (failing test first). Review gate: momus-review on this plan file before execution.

**Goal:** Implement the approved Phase 5 Hijri converter per `docs/development/specs/2026-10-05-phase-5-hijri-converter-design.md` as stacked PRs: tabular + UQU + MABIMS calendars, sunset bridge, JSON offsets, CLI subcommand, public API exports.

**Architecture:** New `src/alfalak/calendar/` package mirroring `calculation/`: `HijriDate` frozen value, `HijriCalendar` ABC with 4-method contract + `CALENDARS` registry + `get_calendar` sentinel factory, three subclasses over Phase-4 `crescent_geometry_at_sunset` predicates, `bridge.gregorian_to_hijri` and `OffsetStore` as decorators outside the hierarchy (no per-calendar branches). Bulk/precomputed month-start table is explicitly deferred to issue #61 — v1 month-walks with bounded `lru_cache`.

**Tech Stack:** Python 3.11+, stdlib only (zero runtime deps), `black` (target py311), `ruff` (F, E4/E7/E9), `mypy --disallow-untyped-defs`, `pytest` (`--cov=alfalak --cov-branch`, gate `--cov-fail-under=95`). Venv: `.venv/bin/python`.

**References:** Spec `docs/development/specs/2026-10-05-phase-5-hijri-converter-design.md`, `ARCHITECTURE.md:48-93`, `src/alfalak/astronomy/CrescentGeometry.py:44-58,184-289`, `src/alfalak/astronomy/Mabims.py:13-32`, `src/alfalak/data/Constants.py:1-7`, `src/alfalak/PrayerTimes.py:114-155`, `src/alfalak/exceptions.py:1-16`, `src/alfalak/__init__.py:28-54`, `src/alfalak/__main__.py:8-50`, `src/alfalak/util/DateComponents.py:12-14`, `src/alfalak/astronomy/CalendricalHelper.py:4-29`, deferred compute issue #61.

**Branch:** `feat/phase-5-hijri-converter` (already cut; stacked PRs per task below).

---

## File Structure

- Create: `src/alfalak/calendar/__init__.py` — re-exports (`HijriDate`, `HijriCalendar`, `TabularCalendar`, `UmmAlQuraCalendar`, `MabimsCalendar`, `OffsetStore`, `gregorian_to_hijri`, `get_calendar`).
- Create: `src/alfalak/calendar/HijriDate.py` — frozen dataclass `HijriDate(year, month, day)` + `isoformat()`.
- Create: `src/alfalak/calendar/HijriCalendar.py` — ABC (`name`, `from_gregorian`, `to_gregorian`, `month_length`) + `CALENDARS` + `get_calendar(name, *, country=None, adjustment_days=0)`.
- Create: `src/alfalak/calendar/TabularCalendar.py` — Type IIa, epoch JD 1948439.5, leaps `{2,5,7,10,13,16,18,21,24,26,29}`, `adjustment_days in [-2,2]`.
- Create: `src/alfalak/calendar/UmmAlQuraCalendar.py` — Makkah ref from `data/Constants.py`, `lag_hours > 0` + `moon_age_days < 15.0` with sentinel/NaN guards, post-1423H guard.
- Create: `src/alfalak/calendar/MabimsCalendar.py` — `country in {MY,ID,BN,SG}`, 4 national-proxy refs, `is_neo_mabims_2021` predicate.
- Create: `src/alfalak/calendar/bridge.py` — `gregorian_to_hijri(dt, *, calendar, coordinates=None, params=None, change_at_sunset=False, offsets=None)`.
- Create: `src/alfalak/calendar/OffsetStore.py` — JSON loader + Hijri-day shift applier.
- Modify: `src/alfalak/__init__.py` — re-export 8 public names + `__all__`.
- Modify: `src/alfalak/__main__.py` — add `hijri` subcommand, keep bare prayer invocation byte-identical.
- Test: `tests/calendar/test_hijri_date.py` (create), `tests/calendar/test_tabular.py` (create), `tests/calendar/test_uqu.py` (create), `tests/calendar/test_mabims.py` (create), `tests/calendar/test_bridge.py` (create), `tests/calendar/test_offsets.py` (create), `tests/calendar/test_factory.py` (create).
- Test modify: `tests/test_public_api.py` — 8 new names; `tests/test_cli.py` — hijri subcommand; `tests/test_blackbox_sweep.py` + `tests/test_parameterized_sweep.py` — extensions per spec §6.

No new runtime deps; no `pyproject.toml` packaging change (new subpackage ships under existing `packages = ["src/alfalak"]`); `py.typed` untouched.

---

## Background the implementer needs

### Current state (verbatim signatures)

`src/alfalak/PrayerTimes.py:114-121` takes date-only semantics despite a `datetime` arg:
```python
def __init__(
    self,
    coordinates: tuple[float, float] | Coordinates,
    date: datetime | DateComponents,
    calculation_method: Optional[CalculationMethod] = None,
    calculation_parameters: Optional[CalculationParameters] = None,
    time_zone: Optional[ZoneInfo] = None,
):
```
`self._date_components = DateComponents.from_utc(date)` (`PrayerTimes.py:154`) drops the time part; `DateComponents.from_utc` (`util/DateComponents.py:13-14`) is `cls(date.year, date.month, date.day)`. So the bridge must pass `calculation_parameters=` as keyword (third positional is `calculation_method`) and normalize naive `dt` via `dt.replace(tzinfo=timezone.utc)` before `dt >= maghrib` (maghrib is tz-aware UTC).

`src/alfalak/astronomy/CrescentGeometry.py:184-186`:
```python
def crescent_geometry_at_sunset(
    day: date, coordinates: Coordinates, delta_t_override: float | None = None
) -> CrescentGeometry:
```
Fields used by calendars: `lag_hours: float` (NaN when no moonset), `moon_age_days: float` (floor 0.1, failure sentinel 30.0), `moon_alt_topo_deg` (property name is `moon_alt_topo_deg` — verify against `CrescentGeometry.py:44-58`), `arcl_deg: float`. `is_neo_mabims_2021(alt_deg, elong_deg)` (`astronomy/Mabims.py:13-17`) is `alt >= 3.0 and elong >= 6.4` with finite-real guards.

`MAKKAH` lives at `src/alfalak/data/Constants.py:7` (`Coordinates(21.4225241, 39.8261818)`); `Qibla.py` only re-exports. Calendars import from `data.Constants`, never from `Qibla`.

### Design decisions (locked, from spec)

1. Sentinel factory: `country is not None` for non-mabims raises; `country is None` for mabims raises; `adjustment_days != 0` for non-tabular raises; defaults never raise.
2. UQU post-1423H only (`>= 2002-03-15`); month-walk probes crossing the epoch raise the same `ValidationError("Umm al-Qura calendar supports post-1423H dates only")`.
3. Moon-age sentinel `>= 30.0 - eps` and NaN `lag_hours` raise `AstronomicalError`, never decide a month length.
4. Search window ±4 days, 1-day steps; exhaustion raises `AstronomicalError` with seed date + window bounds + calendar key; never silently extend.
5. Caches bounded (`functools.lru_cache(maxsize=...)` + clear hook); no unbounded module dicts, no raw-float keys (round lat/lon, ISO date).
6. Offsets: Hijri-day stepping via `month_length`, once, no re-lookup; `to_gregorian` ignores offsets.
7. CLI: `--time` required iff `--sunset-transition`; `--lat/--lon` required iff `--sunset-transition`; `--country` iff mabims; `--adjustment-days` non-zero only with tabular; output exactly `hijri=` + `calendar=` lines.

---

### Task 1: `HijriDate` + ABC + factory + `TabularCalendar`

**Files:** `src/alfalak/calendar/__init__.py`, `HijriDate.py`, `HijriCalendar.py`, `TabularCalendar.py`, `tests/calendar/test_hijri_date.py`, `tests/calendar/test_tabular.py`, `tests/calendar/test_factory.py`

**Goal:** Frozen value + calendar contract + working tabular base all other calendars seed from.

- [ ] Failing tests first: `test_hijri_date_rejects_month_13_and_day_31`, `test_tabular_roundtrip_1900_2100`, `test_tabular_leap_set_11_per_30`, `test_tabular_ramadan_1446_anchor_is_tabular_value`, `test_adjustment_plus1_minus2_shifts_exactly`, `test_factory_sentinels_default_never_raises`. Run: `.venv/bin/python -m pytest tests/calendar/test_hijri_date.py tests/calendar/test_tabular.py tests/calendar/test_factory.py -q --no-cov` → Expected: FAIL (modules missing).
- [ ] Implement: `HijriDate` frozen dataclass (`year >= 1`, `month 1..12`, `day 1..30`, `isoformat()` zero-padded, dataclass ordering); ABC with `name`/`from_gregorian`/`to_gregorian`/`month_length`; `CALENDARS` dict + `get_calendar` sentinel logic raising `ConfigurationError`; `TabularCalendar(adjustment_days=0)` with epoch JD 1948439.5, leap set `{2,5,7,10,13,16,18,21,24,26,29}`, `_hijri_to_jd`/`_jd_to_hijri` via `CalendricalHelper.julian_day`, `adjustment_days in [-2,2]` else `ValidationError`, exact-length enforcement at conversion time. Fully typed.
- [ ] Verify: same pytest command → PASS; `.venv/bin/python -m mypy src/alfalak/calendar` clean.

### Task 2: `UmmAlQuraCalendar` (post-1423H)

**Files:** `src/alfalak/calendar/UmmAlQuraCalendar.py`, `tests/calendar/test_uqu.py`. Depends on: Task 1 (ABC + tabular seed).

**Goal:** Makkah-rule observational calendar with explicit pre-1423H guard.

- [ ] Failing tests: `test_uqu_12month_spotcheck_x2years_deltas_listed`, `test_uqu_pre1423_raises_validation_error`, `test_uqu_sentinel_age_raises_not_30day`. Run: `.venv/bin/python -m pytest tests/calendar/test_uqu.py -q --no-cov` → Expected: FAIL.
- [ ] Implement: `MAKKAH` import from `data.Constants`; on each 29th evening evaluate `crescent_geometry_at_sunset` at Makkah — `lag_hours > 0` and `moon_age_days < 15.0`; NaN lag or `moon_age_days >= 30.0 - eps` raises `AstronomicalError`; true → 29 days else 30; month-walk from tabular seed (±4-day window) with exhaustion `AstronomicalError`; any input mapping before `2002-03-15` raises `ValidationError("Umm al-Qura calendar supports post-1423H dates only")`; module + class docstrings state calendar-vs-prayer-preset distinction and rule history citation (not implemented).
- [ ] Verify: `.venv/bin/python -m pytest tests/calendar/test_uqu.py tests/calendar/test_tabular.py -q --no-cov` → PASS (no tabular regression).

### Task 3: `MabimsCalendar` per-country

**Files:** `src/alfalak/calendar/MabimsCalendar.py`, `tests/calendar/test_mabims.py`. Depends on: Task 1.

**Goal:** Neo-MABIMS 2021 at four national-proxy refs.

- [ ] Failing tests: `test_mabims_ramadan_syawal_1to2years_deltas_listed`, `test_mabims_bad_country_raises_configuration_error`, `test_mabims_case_insensitive`, `test_mabims_month_length_29_or_30_full_year_all_refs`, `test_mabims_1992_vs_2021_flip_comment`. Run: `.venv/bin/python -m pytest tests/calendar/test_mabims.py -q --no-cov` → Expected: FAIL.
- [ ] Implement: `country` required, case-insensitive normalize to upper, else `ConfigurationError`; refs MY `(3.1390, 101.6869)`, ID `(-6.2088, 106.8456)`, BN `(4.8903, 114.9420)`, SG `(1.3521, 103.8198)` pinned at 4dp, documented as proxies; predicate `is_neo_mabims_2021(moon_alt_topo_deg, arcl_deg)` on 29th evening at country ref; month-walk identical structure to UQU; docstring records superseded 1992 rule as migration context only.
- [ ] Verify: same pytest command → PASS.

### Task 4: Bridge `gregorian_to_hijri`

**Files:** `src/alfalak/calendar/bridge.py`, `tests/calendar/test_bridge.py`. Depends on: Tasks 1–3.

**Goal:** Single datetime orchestration point with sunset transition.

- [ ] Failing tests: `test_bridge_maghrib_minus5_plus5_successive_when_on`, `test_bridge_same_day_when_off`, `test_bridge_change_at_sunset_without_coordinates_raises`, `test_bridge_naive_treated_as_utc`, `test_bridge_polar_maghrib_propagates`. Run: `.venv/bin/python -m pytest tests/calendar/test_bridge.py -q --no-cov` → Expected: FAIL.
- [ ] Implement: signature `gregorian_to_hijri(dt, *, calendar, coordinates=None, params=None, change_at_sunset=False, offsets=None)`; `False` → `dt.date()`; `True` → require coordinates (`ConfigurationError`), `PrayerTimes(coordinates, dt, calculation_parameters=params).maghrib` (keyword form), naive `dt.replace(tzinfo=timezone.utc)` before `dt >= maghrib`, advance civil date by one on `>=`, delegate to `calendar.from_gregorian`; polar `AstronomicalError` propagates unwrapped; docstring + warning that aware datetimes are strongly preferred.
- [ ] Verify: same pytest command → PASS.

### Task 5: `OffsetStore`

**Files:** `src/alfalak/calendar/OffsetStore.py`, `tests/calendar/test_offsets.py`. Depends on: Task 4 (applies last in bridge).

**Goal:** JSON delta overrides with defined precedence.

- [ ] Failing tests: `test_offsets_plus1_minus2_month_boundary_carry`, `test_offsets_unknown_key_and_zero_raise`, `test_offsets_precedence_over_computed`. Run: `.venv/bin/python -m pytest tests/calendar/test_offsets.py -q --no-cov` → Expected: FAIL.
- [ ] Implement: wraps `dict[str,int]` keyed `"YYYY-MM"` of computed Hijri month, values in `{-2,-1,1,2}` (0 rejected as config smell); malformed file (unparseable JSON, non-object, bad key, non-int/out-of-range value) raises `ConfigurationError` with path + offending key; shift by N Hijri days via `month_length` stepping (no Gregorian round-trip, no re-lookup); `to_gregorian` ignores store; wire `offsets` param through bridge (applies last and wins).
- [ ] Verify: `.venv/bin/python -m pytest tests/calendar/test_offsets.py tests/calendar/test_bridge.py -q --no-cov` → PASS.

### Task 6: Public API + CLI

**Files:** `src/alfalak/__init__.py`, `src/alfalak/__main__.py`, `src/alfalak/calendar/__init__.py`, `tests/test_public_api.py`, `tests/test_cli.py`, `tests/test_blackbox_sweep.py`, `tests/test_parameterized_sweep.py`. Depends on: Tasks 1–5.

**Goal:** Export 8 names; `hijri` subcommand without breaking bare prayer invocation.

- [ ] Failing tests: `test_public_api_lists_8_hijri_names`, `test_cli_hijri_two_line_output`, `test_cli_hijri_country_required_iff_mabims`, `test_cli_hijri_time_required_iff_transition`, `test_cli_bare_prayer_byte_identical`. Run: `.venv/bin/python -m pytest tests/test_public_api.py tests/test_cli.py -q --no-cov` → Expected: FAIL (names/subcommand missing).
- [ ] Implement: re-export `HijriDate`, `HijriCalendar`, `TabularCalendar`, `UmmAlQuraCalendar`, `MabimsCalendar`, `OffsetStore`, `gregorian_to_hijri`, `get_calendar` from `alfalak.calendar` through `alfalak.__init__` `__all__` (fully typed, `mypy --disallow-untyped-defs` clean); `__main__.py` keeps bare prayer path green, adds `hijri --date --calendar [--country] [--adjustment-days] [--sunset-transition --lat --lon --time] [--offsets]` with the iff-rules, `--date` default today UTC, MWL default params for bridge Maghrib, exactly two output lines, `--help` with UQU-preset distinction + ±1–2 day caveat + naive-UTC warning; extend blackbox/parameterized sweeps per spec §6 (fixed seeds, deterministic).
- [ ] Verify: `.venv/bin/python -m pytest tests/test_public_api.py tests/test_cli.py -q --no-cov` → PASS.

### Task 7: Full gates + stacked PRs

**Files:** none (verification only).

- [ ] Run all gates from repo root: `.venv/bin/python -m black --check src/ 2>&1 | tail -1` → clean; `.venv/bin/python -m ruff check src/ tests/` → clean; `.venv/bin/python -m mypy src 2>&1 | tail -1` → clean; `.venv/bin/python -m pytest -q --cov=alfalak --cov-branch --cov-fail-under=95 2>&1 | tail -2` → all pass, coverage gate holds.
- [ ] Push stacked PRs per task (1→6) against `feat/phase-5-hijri-converter` with test evidence and golden citations (Meeus page/edition, Takwim URL+date, ΔT choice where date-dependent).

---

## QA per task (all use `.venv/bin/python`)

Tabular: `to_gregorian(from_gregorian(d)) == d` over 1900–2100 (fixed seed `random`), leap-set 11/30, Ramadan-1446 tabular anchor with variance note. UQU/MABIMS: spot-check goldens with deltas listed in-test, never hidden. Bridge: Maghrib±5 min successive/same-day asserts. Offsets: boundary carry + `ConfigurationError` on unknown key / value 0. Invariants: `month_length in {29,30}` over a full Hijri year per calendar. Final: four gates green before merge.
