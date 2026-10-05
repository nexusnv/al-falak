# Phase 5 — Unified Hijri Converter & Override Layer: Design Spec

Date: 2026-10-05 | Branch: `feat/phase-5-hijri-converter` | Status: approved design, pre-plan
Scope: full Phase 5 (slices 5.1–5.6) in one spec, implemented as stacked PRs.
Decisions locked during brainstorming: full-phase scope; architecture B (OOP hierarchy
for Diyanet + future regionals); UQU post-1423H only with pre-1423 deferred;
MABIMS per-country refs (MY/ID/BN/SG); sunset bridge default civil; offsets ±1 and ±2;
tabular `adjustment_days` param default 0; CLI `--calendar` + `--country`.

## 1. Background and goals

Phase 4 (merged, `8c434da`) provides the lunar-sighting foundation now exported from
`alfalak.__init__`: `LunarCoordinates`, `CrescentGeometry` /
`crescent_geometry_at_sunset`, `delta_t`, `yallop_q` / `yallop_zone`,
`odeh_v` / `odeh_class`, `is_neo_mabims_2021` / `is_mabims_1992`.
Phase 5 builds the calendar layer on top: a converter that turns Gregorian dates into
Hijri dates under a selectable calendar rule, bridges prayer times to calendar days at
sunset, and applies regional corrections. There is no calendar code of any kind in
`src/` today; `CalculationMethod.UMM_AL_QURA` is a prayer preset (Fajr 18.5° + 90/120-min
Isha), not a calendar.

Goals: (a) correct tabular base with Type IIa / "Kuwaiti" equivalence documented;
(b) two observational calendars (UQU post-1423H, MABIMS Neo-2021 per-country) as thin
predicates over Phase-4 sunset geometry; (c) explicit sunset-transition bridge reusing
`PrayerTimes` Maghrib; (d) JSON delta-offset overrides with defined precedence;
(e) CLI + public API following existing repo patterns (zero runtime deps, stdlib only,
`AlFalakError` hierarchy, `__init__.__all__` exports).
Non-goals: visibility-map export (slice 4.7, deferred, no dependents); pre-1423H UQU
rules (deferred with explicit guard); per-zone (60-zone MY) handling (deferred);
bundled regional offset data files (loader + schema only, no shipped Takwim data).

## 2. Architecture (approach B: OOP hierarchy + registry)

New package `src/alfalak/calendar/` mirroring `calculation/`:

- `HijriDate.py` — immutable value type, no calendar logic.
- `HijriCalendar.py` — abstract base class (ABC) defining the calendar contract.
- `TabularCalendar.py`, `UmmAlQuraCalendar.py`, `MabimsCalendar.py` — the three v1 rules.
- `OffsetStore.py` — JSON delta-offset loader + applier.
- `bridge.py` — `gregorian_to_hijri()` sunset/offset orchestration (outside the hierarchy).
- `__init__.py` — re-exports; public names also re-exported from `alfalak.__init__`.

The ABC contract (every calendar implements all four):

- `name: str` (property: `"tabular"`, `"uqu"`, `"mabims"`; future `"diyanet"`).
- `from_gregorian(d: date) -> HijriDate`
- `to_gregorian(h: HijriDate) -> date`
- `month_length(year: int, month: int) -> int` (29 or 30).

Factory / registry in `HijriCalendar.py`:

- `CALENDARS: dict[str, type[HijriCalendar]] =
  {"tabular": TabularCalendar, "uqu": UmmAlQuraCalendar, "mabims": MabimsCalendar}`.
- `get_calendar(name, *, country=None, adjustment_days=0) -> HijriCalendar`.
  Sentinel semantics (defaults never raise): `country is not None` for a non-`mabims`
  calendar raises; `country is None` for `mabims` raises (required there).
  `adjustment_days != 0` for a non-`tabular` calendar raises; the default `0` is
  accepted everywhere and ignored outside `tabular`. Any other misuse raises
  `ConfigurationError`. Adding Turkish Diyanet later is one subclass plus
  one registry line; bridge, offsets, and CLI resolve through the factory and gain the
  new calendar with no core changes.

Sunset bridge and offsets are decorators outside the hierarchy: the bridge computes a
civil date (possibly advanced past Maghrib) and delegates to the calendar; offsets shift
the calendar result. Neither contains per-calendar branches.

## 3. Components

### 3.1 `HijriDate` (frozen value)

Frozen dataclass `HijriDate(year, month, day)` with `__post_init__` validation:
`year >= 1`, `month in 1..12`, `day in 1..30`. The 30-day upper bound is intentional:
exact month length (29 vs 30) depends on the calendar rule, so the constructor enforces
the universal bound and each calendar enforces the exact length at conversion time
(wrong-length days raise `ValidationError` naming the calendar and month). Provides
`isoformat() -> "YYYY-MM-DD"` (zero-padded) and orders/compares by dataclass equality.
No `to_gregorian` method on the value itself; conversion lives on calendars so the value
stays rule-free.

### 3.2 `TabularCalendar(adjustment_days=0)`

Type IIa arithmetic from epoch 1 Muharram 1 AH = Friday 16 July 622 Julian
(= 19 July 622 Gregorian proleptic), JD 1948439.5 at noon. Thirty-year leap cycle with
leap years `{2, 5, 7, 10, 13, 16, 18, 21, 24, 26, 29}` (355 days; the
al-Fazari/al-Khwarizmi/al-Battani pattern). Both directions via JD arithmetic
(`_hijri_to_jd` / `_jd_to_hijri`), reusing `CalendricalHelper.julian_day` for the
Gregorian side. `adjustment_days: int in [-2, 2]`, default 0, shifts the JD by N days;
documents the "Kuwaiti = Type IIa + `HijriAdjustment` nudge" equivalence
(Windows/.NET `HijriCalendar`, SQL Server) and notes sibling leap patterns
(Fatimid/Tayyibi, Habash/al-Biruni, 8-year Ottoman cycle) as comments, not code.
Tabular output must never be presented as a sighting: docstrings and CLI help state the
routine ±1–2 day tabular-vs-observed variance.

### 3.3 `UmmAlQuraCalendar()` (post-1423H only)

Fixed reference: Makkah, reusing the existing `MAKKAH` constant from
`data/Constants.py` (21.4225241, 39.8261818; canonical statement at 4 dp per the
Phase-1 correction; `Qibla.py` only re-exports it — calendars must not import
it from `Qibla`).
Rule (van Gent / KACST, in force since 1423H / 15 Mar 2002): on the 29th of each Hijri
month, if geocentric conjunction occurred before Makkah sunset AND the moon sets after
Makkah sunset, the next day is the 1st of the new month; otherwise the month completes
30 days. Implementation over existing `CrescentGeometry` fields at Makkah on the 29th
evening: moonset-after-sunset is `lag_hours > 0` (NaN lag is impossible at Makkah;
if `lag_hours` is ever NaN here, propagate `AstronomicalError` — never decide a
month length from it); conjunction-before-sunset is
`moon_age_days < 15.0` (post-conjunction age on a 29th evening is 0–30 h, pre-conjunction
age is ~28.5–29.5 d, so the 15-day midpoint is a side discriminator, not a visibility
threshold). The `_moon_age_days` search-failure sentinel (`30.0`) must not be treated
as a 30-day month: if `moon_age_days >= 30.0 - eps`, raise `AstronomicalError`
naming the date and Makkah location instead of deciding. Month length follows directly otherwise: visible-rule true → 29 days, else 30.
`from_gregorian`/`to_gregorian` walk month-starts from a tabular seed (bounded local
search, §4). Any input mapping before the 1423H epoch raises
`ValidationError("Umm al-Qura calendar supports post-1423H dates only")` — explicit
guard, no silent wrong answer. The 1392/1420/1423 rule history is cited in the module
docstring, not implemented. The class docstring states the calendar-vs-prayer-preset
distinction (`UmmAlQuraCalendar` vs `CalculationMethod.UMM_AL_QURA`).

### 3.4 `MabimsCalendar(country)` (Neo-MABIMS 2021, per-country)

`country: str in {"MY", "ID", "BN", "SG"}` (required, case-insensitive input normalized
to upper; anything else → `ConfigurationError`). One fixed national-proxy reference per
country, pinned at 4 dp for v1 (documented as proxies, not per-zone truth):

- MY: Kuala Lumpur (3.1390, 101.6869)
- ID: Jakarta (-6.2088, 106.8456)
- BN: Bandar Seri Begawan (4.8903, 114.9420)
- SG: Singapore (1.3521, 103.8198)

Rule on the 29th evening at the country ref, via existing
`crescent_geometry_at_sunset` + `is_neo_mabims_2021(moon_alt_topo_deg, arcl_deg)`:
`alt >= 3.0° and elong >= 6.4°` at local sunset → new month next day, else 30 days.
Month walking is forward-only from the anchor 1 Muharram 1445H = 19 July 2023
(observed in all four member countries), identical in structure to §3.3 with the
country ref substituted: the anchor is the support floor, and any input mapping
before it raises `ValidationError` (deferred, mirror of the UQU pre-1423H guard).
Backward walking is explicitly out of scope — a backward single-probe rule cannot
reconstruct the true 29th evening (a visible 30th evening is indistinguishable from
a visible 29th), so it systematically misreads 30-day months as 29-day ones. Old
1992 Labuan rule (`2°/3°-or-8 h`) is not implemented; the docstring records it as the
superseded predecessor for migration context.

## 4. Data flow (conversion pipeline)

Date-only calendars speak `date`: `calendar.from_gregorian(d)` and
`calendar.to_gregorian(h)`. Observational calendars resolve month-starts by evaluating
their predicate on successive 29th evenings: starting from the tabular estimate for the
target (±4-day search window, 1-day steps), find month-start dates, then select the
containing month. If no month-start is found inside the window, raise
`AstronomicalError` naming the tabular seed date, the window bounds, and the calendar
key — never silently extend the window. Month-start results cache per Hijri month
under key `(calendar name, country, adjustment_days, hijri-year, hijri-month)` in a
`functools.lru_cache(maxsize=...)` (bounded; plus a `clear` hook for tests);
`CrescentGeometry` results cache per `(date-iso, rounded lat/lon)` via `lru_cache`
for the same reason — the lunar age backward search dominates cost (pure-Python,
stdlib only; no new deps). Unbounded module-level dicts with raw-float keys are
explicitly out of scope.

Datetime handling lives in one free function in `bridge.py`:

`gregorian_to_hijri(dt: datetime, *, calendar: HijriCalendar,
coordinates: Coordinates | None = None, params: CalculationParameters | None = None,
change_at_sunset: bool = False, offsets: OffsetStore | None = None) -> HijriDate`

Default civil (`change_at_sunset=False`): uses `dt.date()` directly. When `True`,
`coordinates` is required (`ConfigurationError` otherwise); the bridge computes that
day's Maghrib via `PrayerTimes(coordinates, dt, calculation_parameters=params).maghrib`
(keyword form — the third positional is `calculation_method`, not params; only the
date part of `dt` feeds the prayer computation) and advances the civil
date by one when `dt >= maghrib`, then delegates to `calendar.from_gregorian`.
Naive datetimes are normalized to UTC first (`dt.replace(tzinfo=timezone.utc)`) so the
`>=` comparison never mixes naive and aware datetimes; aware datetimes compare in
their own frame against the Maghrib instant (which is tz-aware UTC). This naive-as-UTC
rule is new bridge semantics (the prayer CLI only ever uses the date part, so it sets
no comparison precedent). Aware datetimes
are strongly preferred when `change_at_sunset=True`: a naive local-time input misplaces
Maghrib by its UTC offset, so the docstring and CLI help carry this warning.
A polar `AstronomicalError` from the Maghrib computation propagates unwrapped
(consistent with §5); the bridge adds no polar fallback.

Offsets apply last and win. `OffsetStore` wraps `dict[str, int]` mapping `"YYYY-MM"`
of the *computed* Hijri month to a shift in `{-2, -1, 1, 2}`. If the computed date's
month carries an entry, the date shifts by N Hijri days via Hijri-day arithmetic:
step day-by-day using the same calendar's `month_length` (day 30 of a 29-day month
rolls to day 1 of the next month; day 1 minus 1 rolls to the last day of the previous
month, whose length is looked up on that month). This is intentionally not
`to_gregorian(h) + N days → from_gregorian`: the Gregorian round-trip would re-run
the observational predicate and could double-apply month-start logic. The shift applies
once; no re-lookup of the shifted date occurs. Lookup is
post-computation so tabular and observational paths share one override mechanism.
`to_gregorian` ignores `OffsetStore` entirely (offsets are a Gregorian→Hijri display
correction only); the reverse direction is always the unshifted calendar rule.

## 5. Error handling (existing `AlFalakError` hierarchy)

- `ValidationError`: `HijriDate` field violations; `adjustment_days` outside [-2, 2];
  `from_gregorian`/`to_gregorian` outside the supported range — defined as:
  tabular accepts any Gregorian date mapping to Hijri `year >= 1`
  (Gregorian `>= 622-07-19` proleptic per `CalendricalHelper.julian_day`;
  pre-1582 dates are continuous proleptic, no reform jump; golden coverage is
  `1900-01-01..2100-12-31`); UQU accepts only inputs mapping on/after the 1423H
  epoch (Gregorian `>= 2002-03-15`; anything earlier — including a month-walk probe
  that would cross the epoch — raises the explicit "deferred" message);
  MABIMS accepts only inputs mapping on/after the 1445H anchor
  (Gregorian `>= 2023-07-19`; anything earlier — including a month-walk probe
  that would cross the anchor — raises the explicit deferred
  "MABIMS calendar supports post-1445 dates only" message, mirror of the UQU
  guard; geometry outside the golden window is untested and
  implementers must not silently extrapolate without a cited announcement);
  UQU pre-1423H input
  (explicit "deferred" message); computed 30th of a 29-day month.
- `ConfigurationError`: unknown `--calendar`/`--country`; `country` supplied for a
  non-MABIMS calendar or missing for MABIMS; non-zero `adjustment_days` supplied for a
  non-tabular calendar; `change_at_sunset=True` without coordinates; malformed offset
  file (unparseable JSON, non-object top level, key not matching `YYYY-MM` with month
  01–12, value not an int in {-2,-1,1,2} — including rejection of 0 as a config smell),
  with file path and offending key in the message.
- `AstronomicalError`: propagated unwrapped from `crescent_geometry_at_sunset`
  (polar no-sunset and undefined geometry), preserving location/date diagnostics;
  plus the §4 search-window exhaustion and the §3.3 moon-age-sentinel / NaN-lag cases.
  The bridge's polar Maghrib failure propagates the same way.
- Invariant: converters never return NaN, never silently clamp; every failure names the
  offending value.

## 6. Testing

- Tabular: round-trip property `to_gregorian(from_gregorian(d)) == d` over 1900–2100
  (fixed seed, stdlib `random`, following `test_parameterized_sweep.py` precedent);
  leap-set assertion (11 leaps per 30-year cycle); anchor `1 Ramadan 1446` asserted as
  the *tabular* value with the observed-Saudi-2025-03-01 variance note (sighting Fri eve
  28 Feb 2025; tabular agreement that month is coincidence, not proof);
  `adjustment_days=+1/-2` shifts exactly N days.
- UQU: 12-month spot check × 2 recent Hijri years vs published Umm al-Qura dates, deltas
  listed in-test (not hidden); pre-1423H input raises; no polar case (Makkah never polar).
- MABIMS: per-country Ramadan/Syawal over 1–2 years vs MY/ID announcements, deltas
  listed; same-eve 1992-vs-2021 flip documented in a test comment; all four country refs
  produce `month_length in {29, 30}` over a full Hijri year; pre-1445H input raises
  (forward-only walk from the 1445 anchor; backward walking deferred as unsound).
- Bridge: same civil date at Maghrib−5 min and Maghrib+5 min maps to successive Hijri
  days when on, the same day when off; naive-datetime-as-UTC documented in-test.
- Offsets: ±1/±2 shifts with month-boundary carry verified; unknown keys and value 0
  raise `ConfigurationError`; precedence test (computed vs offset) favors offsets.
- Invariants: `month_length in {29, 30}` for every calendar over a Hijri year;
  `to_gregorian(from_gregorian(d)) == d` on supported ranges. New public names covered
  by `tests/test_public_api.py` + `test_blackbox_sweep.py` extensions.

## 7. CLI and public API

`alfalak.__init__` gains `HijriDate`, `HijriCalendar`, `TabularCalendar`,
`UmmAlQuraCalendar`, `MabimsCalendar`, `OffsetStore`, `gregorian_to_hijri`,
`get_calendar` (all added to `__all__`; fully type-annotated per `mypy
--disallow-untyped-defs`; minute-rounding conventions untouched).

CLI keeps the bare prayer invocation byte-identical (existing `tests/test_cli.py`
green) and adds a subcommand:

`python -m alfalak hijri --date YYYY-MM-DD --calendar {tabular,uqu,mabims}
[--country {MY,ID,BN,SG}] [--adjustment-days N] [--sunset-transition --lat --lon
--time HH:MM[:SS]] [--offsets file.json]`

Date-only `--date` without `--time` means civil-date conversion only: `--sunset-transition`
requires `--time` (wall time at `--lat/--lon` combined with `--date` into a naive
datetime treated as UTC per the bridge rule, with the same local-time-misplacement
warning) because a bare date is midnight and would never
trigger the post-Maghrib advance. `--time` without `--sunset-transition` raises
`ConfigurationError`.

Rules: `--country` required iff `--calendar mabims`; `--lat/--lon` required iff
`--sunset-transition`; `--time` required iff `--sunset-transition`;
`--adjustment-days` accepted only with `--calendar tabular` (non-zero elsewhere raises);
`--date` defaults to today UTC. Sunset-transition Maghrib uses default
`CalculationParameters` (MWL method); method selection for the bridge is deferred.
Output is exactly two lines:
`hijri=<YYYY-MM-DD>` and `calendar=<name>[-<COUNTRY>]`. `--help` states the UQU-calendar-vs-prayer-preset distinction, the tabular-vs-observed
±1–2 day caveat, and the naive-datetime-treated-as-UTC warning for `--sunset-transition`.

## 8. Future calendars (Diyanet recipe)

Turkish Diyanet and further regionals arrive as: subclass `HijriCalendar` implementing
the four contract methods over `crescent_geometry_at_sunset` (or pure arithmetic for
algorithmic calendars), add one `CALENDARS` entry, extend the CLI `--calendar` choices
from the registry keys (no parser restructuring), and add §6-style spot tests with
cited official announcements. Bridge, `OffsetStore`, and the ABC remain untouched.

## 9. References

Meeus *Astronomical Algorithms* 2nd ed. (Willmann-Bell, 1998) Ch.7 (JD) / Ch.47 (Moon);
Yallop NAO TN No.69 (1997); Odeh *Exp. Astron.* 18:39–64; van Gent / KACST UQU rule
history (1392 / 1420–1422 / 1423H versions); MABIMS Labuan 1992 → KBIR 2016 / adoption
2021 (Neo-MABIMS 3°/6.4°); Microsoft/.NET `HijriCalendar` + `HijriAdjustment` for the
Kuwaiti-equivalence claim. Golden tests cite page/URL + edition; crescent goldens
record the IERS-vs-polynomial ΔT choice wherever the date depends on it.
