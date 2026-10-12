# Phase 6 — Validation Ecosystem Implementation Plan

> **For workers:** Execute task-by-task via TDD (failing test first). Review gate:
> momus-review on this plan file before execution. One PR per stacked task
> (§PR order), each green on all four gates before the next branches.

**Goal:** Implement the approved Phase 6 spec
(`docs/development/specs/2026-10-11-phase-6-validation-ecosystem-design.md`)
as six stacked PRs: (6.4) second-precision accessor + rounding canon,
(6.2) independent-reference goldens, (6.1) cross-port benchmark harness with
vendored vectors, (6.3+6.5) timezone matrix remainder + `tzdata` CI pin + docs,
(6.6) solar-coords cache + seeded fuzz, then a docs sweep.

**Architecture:** Additive hardening only (spec approach A). `PrayerTimes`
setters record the post-offset, pre-rounding UTC instant in
`self._unrounded: dict[Prayer, datetime]` and expose
`time_for_prayer_unrounded`; `SunnahTimes` gains `night_fraction_unrounded`.
A vendored-vector pytest harness under `tests/benchmark/` compares unrounded
round-trips (tier-(a), six astronomical prayers) and rounded outputs
(tier-(b), boundary-aware minute rule). A module-level `lru_cache` keyed on
`(y, m, d)` serves `SolarTime`'s three midnight `SolarCoordinates`. No pipeline
refactor, no new runtime deps, no public output-format change.

**Tech Stack:** Python 3.11+, stdlib only, `black` (target py311), `ruff`
(F, E4/E7/E9), `mypy --disallow-untyped-defs`, `pytest` (`--cov-branch`,
`--cov-fail-under=95`). Benchmark generation is offline tooling only (a pinned
Kotlin/Gradle checkout and a pinned `adhanpy` venv), never a CI step.

**References:**
- Spec: `docs/development/specs/2026-10-11-phase-6-validation-ecosystem-design.md`.
- Baseline slice doc: `docs/development/MILESTONE_PHASES_AND_SLICES.md` §Phase 6.
- Precedent plans: `docs/development/plans/2026-10-05-phase-5-hijri-converter.md`.
- Meeus, *Astronomical Algorithms*, 2nd ed. (Willmann-Bell, 1998): Ch.7 (JD),
  Ch.15 pp.102–103 (transit), Ch.25 p.165 (Ex.25.a), Ch.28 p.183 (EoT).
- USNO one-day tables; e-solat Takwim portal.

**Branch:** `phase-6-*` per PR off `main`.

---

## Background the implementer needs

Facts verified against `src/` and `tests/` before writing this plan. Treat the
spec as intent and these line anchors as the ground truth to preserve.

- **Rounding is load-bearing.** `PrayerTimes._rounded_minute`
  (`src/alfalak/PrayerTimes.py:479-491`) applies per-prayer adjustments +
  `method_adjustments`, then calls `rounded_minute` (`util/CalendarUtil.py`,
  half-up via `when.second >= 30`). Public fields are stored in UTC and only
  converted by `_adjust_prayers_time_zone()` (`:517+`) — rounding is in UTC,
  `astimezone` last. Do not change that order.
- **Call sites/prayer names.** `_set_fajr` `:319` (`"fajr"`), `_set_imsak`
  `:331` (`"imsak"`, input is `self.fajr - imsak_offset`), `_set_sunrise`
  `:339`, `_set_syuruk_ishraq_dhuha` `:346-363` (`"ishraq"`/`"dhuha"`,
  `syuruk = sunrise`), `_set_dhuhr` `:366`, `_set_asr` `:392`, `_set_maghrib`
  `:407`, `_set_isha` `:472`. `Prayer.name.lower()` matches every one of these
  names (FAJR→`fajr`, DHUHR→`dhuhr`, IMSAK→`imsak`, …); `syuruk`/`none` are
  never passed to `_rounded_minute`.
- **Both Asr clamps:** `_set_asr` `:399-404` (`self.asr < self.dhuhr` →
  `self.asr = self.dhuhr`) and `__init__` `:244-248` (`self.asr >
  self.maghrib` → `self.asr = self.maghrib`). Keep both.
- **`SunnahTimes.night_fraction`** `src/alfalak/SunnahTimes.py:62-132` validates
  `fraction` ∈ (0,1) exclusive, coerces anchors via `_coerce_utc` `:134-144`,
  rejects degenerate intervals (`ValidationError`), computes the offset exactly
  (`Fraction`), then `rounded_minute(start_utc + timedelta(seconds=...)).astimezone(self._zone)`.
  `__init__` calls `self.night_fraction(...)` for the public markers (`:54-56`).
- **Whole-second quantization.** `TimeComponents.from_float`
  (`util/TimeComponents.py:16-22`) truncates with `int(seconds)`; offsets are
  whole minutes. So adjusted instants carry `microsecond==0` — a whole-second
  boundary clause is vacuous on our side (spec §3.2 quantization note).
- **Cache target.** `SolarTime.__init__` (`astronomy/SolarTime.py:32-38`) builds
  `SolarCoordinates(julian_date - 1)`, `(julian_date)`, `(julian_date + 1)`;
  `julian_day(y,m,d)` always ends in `.5` at midnight
  (`astronomy/CalendricalHelper.py:29`). `SolarCoordinates.__init__` is
  jd-only (`astronomy/SolarCoordinates.py:18`) and is never called off-midnight
  by `SolarTime`. `CrescentGeometry` calls `SolarCoordinates` at non-midnight
  JDs — **exclude** it (spec §3.6).
- **Cache precedent.** Module-level `functools.lru_cache` + explicit clear:
  `calendar/UmmAlQuraCalendar.py:93,114` (`clear_caches`) and
  `calendar/MabimsCalendar.py:79,111,161` (`clear_mabims_cache`).
- **Public-API doc gate.** `tests/test_public_api.py:227-241` asserts every
  `__all__` name appears in `docs/user/api-reference.md`, plus a hard-coded
  method tuple `("time_for_prayer", "Qibla", "SunnahTimes")` (`:240`). Methods
  are not in `__all__`; this tuple is the only method gate.
- **Existing independent goldens to preserve, not loosen:**
  `tests/astronomy/test_astronomical.py:10` (`test_solar_coordinates`, Ex.25.a
  abs=1e-5 deg), `:72` (`test_transit_and_hour_angle`, Meeus p.103),
  `:161`/`:170`/`:187` (EoT Ch.28), `tests/astronomy/test_solar_time.py:10`
  (USNO Raleigh 2015-07-12), `tests/test_prayer_times.py:568`
  (`test_twilight_preset_goldens_raleigh`), `:648-689`
  (`test_jakim_malaysian_zone_goldens`, computed baseline).
- **Clamp-day fixtures for the accessor:** `tests/test_polar_circle.py:103`
  (`(66.4, 18.96)`, 2015-12-21, `NONE` → `asr == dhuhr`) and `:127`
  (`(89.1, 0.0)`, 2024-03-19 → `asr == maghrib`).
- **Fuzz precedent:** `tests/test_parameterized_sweep.py` (fixed seed, polar
  generator `:428-436`, `NEAREST_LATITUDE` at `|lat|==90`). The public seam and
  `AstronomicalError` handling pattern is in `tests/test_blackbox_sweep.py`.
- **CI/requirements:** `.github/workflows/test.yml` (ubuntu only, py3.11–3.14,
  `pip install -r requirements.txt` then `pytest --cov-fail-under=95`).
  `requirements.txt` has no `tzdata`. `pip install tzdata` + `PYTHONTZPATH=""`
  makes the PyPI DB win over `/usr/share/zoneinfo`
  (`zoneinfo._tzpath._parse_python_tzpath` returns `()` for an empty var).
- **`docs/development/` is ephemeral:** never link to it from `README.md`,
  `docs/user/`, code, comments, or docstrings; the benchmark baseline lives
  there but nothing may point at it.

---

## File structure

```
src/alfalak/PrayerTimes.py                 # 6.4: _unrounded map + accessor, clamps
src/alfalak/SunnahTimes.py                 # 6.4: night_fraction_unrounded
src/alfalak/astronomy/SolarTime.py         # 6.6: route midnight coords through cache
tests/test_unrounded_accessor.py           # 6.4 (new)
tests/astronomy/test_astronomical.py       # 6.2 transit golden + tolerance note
tests/astronomy/test_solar_time.py         # 6.2 USNO spot rows
tests/test_prayer_times.py                 # 6.2 Takwim portal rows
docs/user/citations.md                     # 6.2 golden citations
docs/user/api-reference.md                 # 6.4 method rows + rounding canon
tests/benchmark/grid.py                    # 6.1 shared fixed grid (new)
tests/benchmark/generate_adhan_kotlin.py   # 6.1 generator (new, not collected)
tests/benchmark/generate_adhanpy.py        # 6.1 generator (new, not collected)
tests/benchmark/vectors/*.json             # 6.1 vendored vectors (new)
tests/benchmark/test_cross_port.py         # 6.1 harness (new)
docs/development/baseline/2026-10-12-phase6-benchmark.md  # 6.1/6.6 scratch report
tests/test_timezone_matrix.py              # 6.3 (new)
requirements.txt                           # 6.5 tzdata pin
.github/workflows/test.yml                 # 6.5 PYTHONTZPATH="" on the pytest step
docs/user/timezone.md                      # 6.3/6.6 policy notes
docs/user/getting-started.md               # 6.5 Windows tzdata install step
docs/user/high-latitude.md                 # 6.3 high-latitude risk note
tests/test_fuzz_ordering.py                # 6.6 (new)
docs_site/astro.config.mjs                 # only if a new user page is added
```

---

## Task 1 (PR 1) — 6.4: second-precision accessor + rounding canon

Unblocks 6.1 tier-(a). No new astronomy; `_rounded_minute` is refactored to
take the `Prayer` member (its `.name.lower()` is the existing attribute key)
and to record the post-offset pre-round instant.

**1a. Failing tests first** — create `tests/test_unrounded_accessor.py`:

```python
"""Round-trip invariants for the second-precision accessors (Phase 6.4).

Anchors:
- default UTC build + an explicit ``time_zone`` build (DST-safe);
- both Asr clamp sites (test_polar_circle.py:103/:127 fixtures);
- adjustment-bearing methods (offsets are inside the unrounded value);
- derived markers (imsak/ishraq/dhuha) and the syuruk alias.
"""

import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from alfalak import (
    CalculationMethod, CalculationParameters, PolarCircleRule, Prayer,
    PrayerTimes, SunnahTimes,
)
from alfalak.exceptions import ConfigurationError, ValidationError
from alfalak.util.CalendarUtil import rounded_minute
from alfalak.util.DateComponents import DateComponents

ALL = (Prayer.IMSAK, Prayer.FAJR, Prayer.SUNRISE, Prayer.SYURUK,
       Prayer.ISHRAQ, Prayer.DHUHA, Prayer.DHUHR, Prayer.ASR,
       Prayer.MAGHRIB, Prayer.ISHA)


def _pt(time_zone=None):
    return PrayerTimes(
        (35.7750, -78.6336), DateComponents(2015, 7, 12),
        calculation_method=CalculationMethod.MUSLIM_WORLD_LEAGUE,
        time_zone=time_zone,
    )


def _none_rule_params():
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.polar_circle_rule = PolarCircleRule.NONE
    return params


@pytest.mark.parametrize("tz", [None, ZoneInfo("America/New_York")])
def test_unrounded_round_trips_every_prayer(tz):
    pt = _pt(tz)
    display = tz or timezone.utc
    for prayer in ALL:
        assert (rounded_minute(pt.time_for_prayer_unrounded(prayer))
                .astimezone(display) == pt.time_for_prayer(prayer)), prayer


def test_unrounded_includes_offsets():
    base = _pt()
    params = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    params.adjustments.fajr = 5
    shifted = PrayerTimes((35.7750, -78.6336), DateComponents(2015, 7, 12),
                          calculation_parameters=params)
    assert (shifted.time_for_prayer_unrounded(Prayer.FAJR)
            - base.time_for_prayer_unrounded(Prayer.FAJR)
            == timedelta(minutes=5))


def test_unrounded_syuruk_aliases_sunrise():
    pt = _pt()
    assert (pt.time_for_prayer_unrounded(Prayer.SYURUK)
            == pt.time_for_prayer_unrounded(Prayer.SUNRISE))


def test_unrounded_asr_clamp_dhuhr():
    pt = PrayerTimes((66.4, 18.96), DateComponents(2015, 12, 21),
                     calculation_parameters=_none_rule_params())
    assert pt.asr == pt.dhuhr
    assert pt.time_for_prayer_unrounded(Prayer.ASR) == pt.dhuhr


def test_unrounded_asr_clamp_maghrib():
    pt = PrayerTimes((89.1, 0.0), DateComponents(2024, 3, 19),
                     calculation_parameters=_none_rule_params())
    assert pt.asr == pt.maghrib
    assert pt.time_for_prayer_unrounded(Prayer.ASR) == pt.maghrib


def test_unrounded_rejects_none_and_non_prayer():
    pt = _pt()
    for bad in (Prayer.NONE, "fajr", None):
        with pytest.raises(ConfigurationError):
            pt.time_for_prayer_unrounded(bad)


def test_night_fraction_unrounded_round_trips():
    pt = _pt(ZoneInfo("America/New_York"))
    st = SunnahTimes(pt)
    for f in (1 / 3, 2 / 3, 0.5):
        assert (rounded_minute(st.night_fraction_unrounded(f))
                .astimezone(timezone.utc)
                == st.night_fraction(f).astimezone(timezone.utc))


def test_night_fraction_unrounded_explicit_anchors():
    pt = _pt()
    st = SunnahTimes(pt)
    assert (rounded_minute(st.night_fraction_unrounded(1 / 3, start=pt.isha))
            == st.night_fraction(1 / 3, start=pt.isha))


@pytest.mark.parametrize("bad", [0, 1, -0.1, 1.1, True, "x", None])
def test_night_fraction_unrounded_rejects_invalid_fraction(bad):
    st = SunnahTimes(_pt())
    with pytest.raises(ValidationError):
        st.night_fraction_unrounded(bad)
```

`_none_rule_params()` above mirrors the `test_polar_circle.py` fixture shape;
define it locally in this file (do not import private test helpers).

**1b. Implement `PrayerTimes`** (`src/alfalak/PrayerTimes.py`):

- In `__init__`, immediately before `self._set_fajr()` (`:237`) add:
  `self._unrounded: dict[Prayer, datetime] = {}`.
- Rewrite `_rounded_minute` to key on `Prayer` and record the adjusted instant:

```python
def _rounded_minute(
    self,
    adjustments: PrayerAdjustments,
    method_adjustments: PrayerAdjustments,
    prayer: Prayer,
    temp_prayer: datetime,
) -> datetime:
    name = prayer.name.lower()
    adjusted = (
        temp_prayer
        + timedelta(minutes=getattr(adjustments, name))
        + timedelta(minutes=getattr(method_adjustments, name))
    )
    self._unrounded[prayer] = adjusted
    return rounded_minute(adjusted)
```

- Update the nine `_rounded_minute(...)` call sites to pass `Prayer.FAJR`,
  `Prayer.IMSAK`, `Prayer.SUNRISE`, `Prayer.ISHRAQ`, `Prayer.DHUHA`,
  `Prayer.DHUHR`, `Prayer.ASR`, `Prayer.MAGHRIB`, `Prayer.ISHA` in that slot.
- Add to `_set_syuruk_ishraq_dhuha` right after `self.syuruk = self.sunrise`:
  `self._unrounded[Prayer.SYURUK] = self._unrounded[Prayer.SUNRISE]`.
- Both clamps update the store alongside the field:
  `_set_asr` `:404` → `self._unrounded[Prayer.ASR] = self.dhuhr`; `__init__`
  `:248` → `self._unrounded[Prayer.ASR] = self.maghrib`.
- Add the accessor:

```python
def time_for_prayer_unrounded(self, prayer: Prayer) -> datetime:
    """Return the post-offset, pre-rounding UTC instant for ``prayer``.

    Per-prayer ``adjustments`` and ``method_adjustments`` are included; the
    value is the instant immediately before half-up minute rounding, in UTC.
    ``time_for_prayer`` is its rounded, display-zone counterpart. ``syuruk``
    is the ``sunrise`` instant. ``Prayer.NONE`` and non-``Prayer`` inputs
    raise ``ConfigurationError``.
    """
    if not isinstance(prayer, Prayer) or prayer not in self._unrounded:
        raise ConfigurationError(f"Unknown prayer: {prayer!r}.")
    return self._unrounded[prayer]
```

**1c. Implement `SunnahTimes`** (`src/alfalak/SunnahTimes.py`): extract the
existing body of `night_fraction` (validation + anchor coercion + exact
`Fraction` offset, `:87-129`) into
`_night_fraction_utc(fraction, start, end) -> datetime` returning
`start_utc + timedelta(seconds=offset_seconds)` (UTC, no rounding). Then:

```python
def night_fraction(self, fraction, start=None, end=None) -> datetime:
    <existing docstring>
    return rounded_minute(
        self._night_fraction_utc(fraction, start, end)
    ).astimezone(self._zone)

def night_fraction_unrounded(self, fraction, start=None, end=None) -> datetime:
    """Return Maghrib + ``fraction`` of the night, UTC, never rounded.

    Same computation and validation as ``night_fraction`` minus the minute
    rounding and the display-zone conversion.
    """
    return self._night_fraction_utc(fraction, start, end)
```

`__init__` keeps calling `self.night_fraction(...)` — default output must be
byte-identical.

**1d. Wire the doc gate:** add `time_for_prayer_unrounded` and
`night_fraction_unrounded` to the hard-coded tuple in
`tests/test_public_api.py:240`, and add a row to the Methods table in
`docs/user/api-reference.md` for each (PrayerTimes `:74-78`, SunnahTimes
section) stating the post-offset pre-round UTC semantics and the
`ConfigurationError`/`ValidationError` contracts.

**1e. Rounding canon** in `docs/user/api-reference.md`: add a short
"Rounding order" subsection — per-prayer offsets applied pre-rounding, half-up
minute rounding in UTC, `astimezone` last; the unrounded accessor returns the
adjusted pre-round instant (offsets included), not raw solar geometry.

**Verify:** `pytest tests/test_unrounded_accessor.py tests/test_prayer_times.py
tests/test_sunnah_times.py tests/test_polar_circle.py tests/test_public_api.py
--no-cov` then the full gate (`black --check src/`, `ruff check src/ tests/`,
`mypy src`, `pytest --cov-fail-under=95`).

---

## Task 2 (PR 2) — 6.2: independent-reference goldens

No new infrastructure; append to existing modules. Preserve every existing
tighter bar (spec §3.3).

**2a. Transit golden** — append to `tests/astronomy/test_astronomical.py`:

```python
def test_greenwich_solar_transit_chain_consistency():
    # Chain-consistency lock (spec §3.3 fallback), NOT independent physical
    # truth: an independent Meeus Ch.15 hand-work needs the apparent sidereal
    # time Theta0 for 1992-10-13, which the cited examples do not publish, so
    # it would have to come from this repo (circular). Instead the expected
    # value is derived from published examples only:
    #   Meeus 2nd ed. Ex.25.a (p.165): apparent RA for 1992-10-13 (0h TD),
    #     alpha = 198.38083 deg = 13h13m31.4s;
    #   Meeus 2nd ed. Ex.28.a (p.183): E = +13m42s for the same date.
    # For the Sun at Greenwich, H = 0 gives transit = 12h - E:
    #   12:00:00 - 0:13:42 = 11:46:18 UT.
    # The independent transit truth is the USNO spot rows in 2b; this case
    # locks the second-level chain. Expected value is not taken from this
    # repo's corrected_transit.
    transit = SolarTime(
        DateComponents(1992, 10, 13), Coordinates(51.4779, 0.0)
    ).transit
    assert transit == pytest.approx(11 + 46 / 60 + 18 / 3600, abs=10 / 3600)
```

Only if the implementer produces a genuinely independent Ch.15 hand-work (a
published Θ0 for the date) should this be renamed
`test_greenwich_solar_transit_ex25a` and treated as independent truth; do
**not** substitute this repo's `corrected_transit` output for the expected
value either way.

**2b. USNO spot rows** — extend `tests/astronomy/test_solar_time.py` with 2–3
city×date USNO one-day tables, cities/dates fixed **now** (not chosen later).
Use US locations only — the one-day table's `state`/`place` form is US-scoped,
so a non-US city (e.g. Singapore) is not sourceable there: New York
(40.7128, −74.0060) 2024-12-21; Seattle (47.6062, −122.3321) 2024-03-20.
Source URL per row:
`https://aa.usno.navy.mil/rstt/onedaytable?form=1&ID=AA&year=...&month=...&day=...&state=...&place=...`.
Record the published rise/set/transit and compare the raw
`SolarTime.sunrise/.sunset/.transit` floats (hours) with
`abs(delta) <= 60 / 3600`, asserting the minute string alongside for
readability — `_time_string` alone cannot express a ±60 s bar. Keep the
existing Raleigh row untouched. If the USNO endpoint is unreachable, record the
failure and do not substitute an unverifiable number.

**2c. Takwim portal rows** — extend `tests/test_prayer_times.py` with 2–3
**published** e-solat values. "Distinct" means distinct *provenance*: the
existing goldens at `:648-689` lock this repo's computed 20/18 baseline, and
the illustrative portal value below happens to coincide with the KL computed
fajr (`22:02 UTC`) — so the new rows must carry the portal URL + retrieval
date as the assertion's evidence, not a second computed bar. Locations: Kuala
Lumpur (3.1390, 101.6869) and Kota Kinabalu (5.9804, 116.0735). Pin the local
date→UTC date mapping explicitly in-comment: a KL e-solat time on local date L
maps to the build's UTC date — e.g. local 2025-01-16 06:02 MYT (UTC+8) is
`22:02 UTC on 2025-01-15`, so `DateComponents(2025, 1, 15)` is the UTC date to
pass. Record the portal URL (`https://www.e-solat.gov.my/...`), the local date,
the UTC date, and a **numeric** administrative delta per prayer (e.g.
`ADMIN_DELTA_MINUTES = 2`, asserted as `abs(computed - published) <=
timedelta(minutes=2)`); record the observed delta next to the value the first
time it is captured rather than leaving "documented delta" qualitative. Repeat
the e-solat administrative-adjustment caveat already in `:678-679`.

**2d. Tolerance mapping** — add the two-tier policy as a module docstring
block to `tests/astronomy/test_astronomical.py` (transit/EoT full-chain ±10 s;
USNO rise/set ±60 s; Takwim minute-agreement + documented admin delta;
Ex.25.a abs=1e-5 deg and EoT ±10.2 s **unchanged**) and add entries to
`docs/user/citations.md` (edition + page/URL per new golden).

**Verify:** `pytest tests/astronomy/test_astronomical.py
tests/astronomy/test_solar_time.py tests/test_prayer_times.py --no-cov`, then
the full four gates.

---

## Task 3 (PR 3) — 6.1: cross-port benchmark harness + vendored vectors

**Source decisions (fixed here, not at implementation):**
- **`batoulapps/adhan-kotlin`** (`adhan2`, the maintained BatoulApps official
  port; `batoulapps/adhan-java` no longer hosts the code — correct the stale
  "adhan-java root" citation in the baseline/report only, not in frozen docs),
  version label `e23d1438`, SHA
  `e23d14385f6203954256b935ef91dc3c6565de34` (2026-08-21). Generated **twice**
  per entry: `Rounding.NONE` → whole-second `unrounded`
  (`seconds_procedure: "second"`), and `Rounding.NEAREST` → `rounded` (adhan2's
  `Rounder.NEAREST` is `Float.roundToInt()`, half-away-from-zero, matching our
  half-up at `:30`). The top-level metadata records both
  `seconds_procedure` and `rounded_rounding`. The Kotlin `CalculationMethod`
  enum includes both `MUSLIM_WORLD_LEAGUE` and `NORTH_AMERICA`, so the grid
  methods exist on both sides.
  **High-latitude rule must be pinned:** adhan2's `CalculationParameters`
  defaults `highLatitudeRule` to `null` and `nightPortions()` resolves
  `null` via `HighLatitudeRule.recommendedFor(coordinates)`, which is
  `SEVENTH_OF_THE_NIGHT` above 48° latitude — our `CalculationParameters`
  hard-sets `MIDDLE_OF_THE_NIGHT`
  (`src/alfalak/calculation/CalculationParameters.py:34`, no
  `recommendedFor`). The generator must derive per-method parameters and pin
  the rule on the copy —
  `CalculationMethod.<METHOD>.parameters.copy(
  highLatitudeRule = HighLatitudeRule.MIDDLE_OF_THE_NIGHT)` — **not** the bare
  `CalculationParameters(...)` constructor, which would discard the method's
  angles/adjustments (`adhan2` has no `_set_parameters_using_method`).
  Otherwise the London 51.5° rows diverge by hours at the solstice (fajr/isha
  fall back to `sunrise − portion·night` with 1/2 vs 1/7). Record the
  `recommendedFor` difference as an out-of-scope port finding in the in-file
  lineage notes — it is a parameter-default change, not shared-core math.
- **`alphahm/adhanpy`** (direct parent, third-party) at
  `f9cfed51a857cb6a8436ad4f5685e7ac27896782` (2024-04-06). adhanpy rounds to
  the minute, so it is a **rounded-only** vector
  (`seconds_procedure: "minute-only"`, no `unrounded` key) exercising the
  tier-(b) minute-only branch — including its documented rollover artifact
  (see 3d).
- `seconds_procedure` enum is `fractional | second | minute-only` (the spec
  names only two values; `second` is the actual whole-second-truncated case).

**3a. Shared fixed grid** — `tests/benchmark/grid.py` (non-test module imported
by both generators and the harness):

```python
GRID = (
    ("Raleigh", 35.7750, -78.6336, "2015-07-12"),
    ("Raleigh", 35.7750, -78.6336, "2015-12-01"),
    ("London", 51.5074, -0.1278, "2024-06-21"),
    ("London", 51.5074, -0.1278, "2024-12-21"),
    ("Singapore", 1.3521, 103.8198, "2024-03-20"),
    ("Tokyo", 35.6762, 139.6503, "2024-09-01"),
    ("Sydney", -33.8688, 151.2093, "2024-01-15"),
    ("Nairobi", -1.2921, 36.8219, "2024-04-10"),
    ("New York", 40.7128, -74.0060, "2024-11-03"),
    ("Cape Town", -33.9249, 18.4241, "2024-07-01"),
    ("Madrid", 40.4168, -3.7038, "2024-02-29"),
    ("Kuala Lumpur", 3.1390, 101.6869, "2024-06-01"),
)
METHODS = ("MUSLIM_WORLD_LEAGUE", "NORTH_AMERICA")
```

All rows are mid-latitude enough that both ports produce all six prayers (the
London 51.5° solstice rows produce them only via the high-latitude fallback, so
they depend on the 3c `MIDDLE_OF_THE_NIGHT` pin above); no cancellation rule;
`PolarCircleRule` is ours only and the grid does not exercise it (every row is
defined on our side); elevation 0; UTC values only. 12 rows × 2 methods = 24
entries per source.

**3b. Vector schema** (resolves the spec's under-specified shape): each
`tests/benchmark/vectors/<source>.json` is an object with
`source`, `version`, `sha`, `generator`, `seconds_procedure`,
`rounded_rounding`, `high_latitude_rule`, and `entries`; each entry is
`{city, latitude, longitude, date, method, unrounded?, rounded}` with prayer
names `fajr/sunrise/dhuhr/asr/maghrib/isha` and ISO-8601 UTC values.
`unrounded` is present only for `fractional`/`second` sources and is
whole-second (or ms) truncated — never fabricated. `rounded` is the port's own
minute-rounded output (for the Kotlin source that is the separate
`Rounding.NEAREST` pass, not the `Rounding.NONE` values). `high_latitude_rule`
records the pin from 3c (`MIDDLE_OF_THE_NIGHT`) so the tier comparison is
like-for-like.

**3c. Generators** (committed records, not collected by pytest):
- `tests/benchmark/generate_adhanpy.py`: creates a venv, `pip install
  git+https://github.com/alphahm/adhanpy@f9cfed51a857cb6a8436ad4f5685e7ac27896782`,
  imports the grid, writes `vectors/adhanpy.json` with `rounded` only. Runnable
  end-to-end.
- `tests/benchmark/generate_adhan_kotlin.py`: emits a `Main.kt` (pinned SHA;
  iterates `GRID`/`METHODS`; derives per-method parameters via
  `CalculationMethod.<METHOD>.parameters.copy(
  highLatitudeRule = HighLatitudeRule.MIDDLE_OF_THE_NIGHT)` — never the bare
  constructor — and emits **two** runs per entry —
  `rounding = Rounding.NONE` → `unrounded`
  and `rounding = Rounding.NEAREST` → `rounded`) plus the exact `gradle`
  invocation, runs it in a scratch build dir, writes
  `vectors/adhan_kotlin.json`. Document the JDK/Gradle versions used in the
  file header.

**3d. Harness** — `tests/benchmark/test_cross_port.py`:

```python
ASTRONOMICAL = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")
DERIVED = ("imsak", "ishraq", "dhuha")

def _boundary_minute_equal(our_rounded, our_unrounded, their_rounded, their_unrounded):
    if our_rounded == their_rounded:
        return True
    if abs((our_rounded - their_rounded).total_seconds()) != 60:
        return False
    # A minute flip needs a pre-round second within 1 s of the :30 boundary.
    return any(abs(v.second + v.microsecond / 1e6 - 30) <= 1
               for v in (our_unrounded, their_unrounded))


def _minute_only_equal(our_rounded, our_unrounded, their_rounded):
    if our_rounded == their_rounded:
        return True
    # adhanpy CalendarUtil.rounded_minute does
    #   replace(minute=int(minute + round(second / 60)), second=0)
    # which raises ValueError at minute 59 / second >= 30 and falls back to
    # replace(second=0): it truncates instead of rolling the hour (unlike our
    # CalendarUtil.rounded_minute). Accept exactly that artifact and nothing
    # wider: our side rolled to the next hour, theirs stayed at :59.
    return (
        our_unrounded.minute == 59
        and our_unrounded.second >= 30
        and their_rounded == our_unrounded.replace(second=0, microsecond=0)
        and (our_rounded - their_rounded).total_seconds() == 60
    )
```

Parametrize over every vector file and entry. Tier-(a): for each of the six
astronomical prayers compare `time_for_prayer_unrounded` (UTC) to the vector's
`unrounded` at ≤1 s (floor fractional port values to whole seconds first);
assert on failure with `(source, city, date, prayer, delta)` and track max
delta. Tier-(b): compare the public rounded field via
`_boundary_minute_equal`, using the 6.4 accessor for our seconds and the
vector's `unrounded` for the port's. For `minute-only` vectors the port side
has no seconds, so use `_minute_only_equal` instead — never bare exact-minute
equality, which is deterministically red for the three known adhanpy rollover
entries (London 2024-12-21 `fajr` MWL and `dhuhr` MWL/NA at :59:37/:59:49).
The rollover result is a characterization of adhanpy's rounding, not a licence
to widen the bar. This deliberately supersedes spec §3.2's "bare exact-minute
for `rounded`-only vectors" sentence (recorded deviation, same rationale as
the spec's own boundary note: the port has a deterministic 60 s artifact that
exact-minute equality cannot represent). Include `syuruk` at tier-(b) only via `sunrise`.
Derived markers (`imsak/ishraq/dhuha`) tier-(b) only. Assert the vectors cover
exactly `grid.GRID × grid.METHODS` so drift is caught. Import only the public
API + the accessor; never a private setter. Read `tests/` paths only.

**3e. Baseline report** — create
`docs/development/baseline/2026-10-12-phase6-benchmark.md` (scratch; no link
from any code/doc): vector count, tier results, max deltas, and the pinned
SHAs. Extend it with before/after cache timings in Task 5.

**Verify:** `pytest tests/benchmark --no-cov` then the full four gates. Confirm
`pytest` does not collect `generate_*.py` and that `testpaths="tests"`,
`packages=["src/alfalak"]` are untouched.

---

## Task 4 (PR 4) — 6.3 tz matrix remainder + 6.5 docs & `tzdata` pin

**4a. CI pin** — add `tzdata==2026.5` to `requirements.txt` (dev/test only;
never a package runtime dep) and force the pinned DB on the pytest step:

```yaml
      - name: Test with pytest
        env:
          PYTHONTZPATH: ""
        run: pytest --cov-fail-under=95
```

Preferred env-var form. If `zoneinfo.reset_tzpath()` is used instead, it must
run in a fixture that saves/restores global `TZPATH` in `try/finally`, and
`pytest.importorskip("tzdata")` when absent. In-test diagnostics log
`zoneinfo.TZPATH` and `importlib.metadata.version("tzdata")`; never assert
equality.

**4b. Matrix** — create `tests/test_timezone_matrix.py` with behavior asserts
(never "no crash"), each stating expected behavior:
- High-latitude rows toward 60°+ exercising polar rules (Sydney kept as smoke
  only); reuse the `test_polar_circle.py` fixture shape.
- Modern political/DST rule change against the pinned DB: e.g.
  `America/Mexico_City` 2023-04-02 (DST abolition) asserting the year-round
  UTC−06 offset; `Pacific/Kiritimati` (+14) asserting the UTC-date↔local-date
  shift (same trap as the Takwim convention).
- Spring-forward row (`America/New_York` 2015-03-08) asserting the
  nonexistent-local-time policy in-test: the build constructs UTC instants then
  `astimezone`s, so no local wall time in the gap is ever constructed; assert
  every output is a valid local time with the post-transition offset.

**4c. Docs (extend, never duplicate):**
- `docs/user/timezone.md`: add the nonexistent-local-time policy and the
  local-date-boundary note; the Windows `pip install tzdata` wording at
  `:71-76` is already present.
- `docs/user/getting-started.md`: add the missing Windows install-step note
  (`pip install tzdata`) — it currently mentions neither.
- `docs/user/high-latitude.md`: add the high-latitude risk note.
- `docs/user/cli.md:124-125,:217-220` and `debian/al-falak.1:53` already
  document the `--city` tz-default — do not touch.

**Verify:** `PYTHONTZPATH="" pytest tests/test_timezone_matrix.py --no-cov`;
confirm `zoneinfo.TZPATH == ()` and the logged tzdata version in the test
output; then the full four gates under the forced path.

---

## Task 5 (PR 5) — 6.6: solar-coords cache + seeded fuzz

**5a. Cache** — add to `src/alfalak/astronomy/SolarTime.py`:

```python
@functools.lru_cache(maxsize=512)
def _solar_coords_for_date(
    year: int, month: int, day: int, day_offset: int = 0
) -> SolarCoordinates:
    return SolarCoordinates(julian_day(year, month, day) + day_offset)


def clear_solar_coords_cache() -> None:
    _solar_coords_for_date.cache_clear()
```

In `SolarTime.__init__` replace the three direct constructions
(`julian_date - 1`, `julian_date`, `julian_date + 1`) with
`_solar_coords_for_date(year, month, day, day_offset=-1/0/+1)`, and **delete
the now-unused `julian_date` local** (`SolarTime.py:32-34`) or `ruff` (F841)
reds the gate.

Why `day_offset` rather than `datetime(y, m, d) ± timedelta(days=1)`: current
`SolarTime` accepts `DateComponents(1, 1, 1)` (only year 9999 overflows today,
later in `PrayerTimes.__init__`), whereas `date(1, 1, 1) - timedelta(days=1)`
raises `OverflowError` — a new failure mode. Computing the neighbour via
`julian_day(y, m, d) ± 1` keeps the JD arithmetic total and exact (adjacent
calendar days differ by exactly 1.0, and ±1 is exact on the `.5` midnight
floats), preserves byte-identical output, and still keys on the calendar-date
ints — satisfying the spec's "no `int(jd)` key" discipline. `day_offset` is a
discipline marker, not a JD key; do **not** convert it to an `int(jd)` lookup.

**`maxsize=512` rationale (spec §3.6 asks for a hit-rate note):** a
`PrayerTimes` build touches three dates and the `SunnahTimes` tomorrow-rebuild
re-touches the neighbour, so hits come from repeated builds and multi-day
sweeps, not within a single build. 512 entries ≈ 170–256 distinct dates at
~2–3 cache lines per date (the `(y,m,d,offset)` key allows a date to appear as
both `offset=0` and a neighbour's `offset=±1`); the per-eval payload is ~µs of
trig, so this is a correctness-neutral perf trade-off. Note that the
`_schedule_defined` bisection and `_nearest_date_with_sunrise_sunset`'s
day-scan can churn the cache; that is acceptable (bounded, no behavior change).
Record the measured hit rate in the Task 3/5 baseline report.

Add a regression test asserting `_solar_coords_for_date(y, m, d, offset)` for
adjacent dates equals `SolarCoordinates(julian_day(y, m, d) ± 1)` on the
compared attributes, including `DateComponents(1, 1, 1)` (proving no new
`OverflowError`) and year/month/leap boundaries
(`tests/astronomy/test_solar_time.py`), plus a `clear_solar_coords_cache()`
call in the test to avoid cross-test state.

**5b. Fuzz** — `tests/test_fuzz_ordering.py`, stdlib `random`, fixed seed
(e.g. `20261012`), `N=2000`, config fixed here:
`calculation_method=MUSLIM_WORLD_LEAGUE`, `PolarCircleRule.NONE`, `Madhab.SHAFI`,
elevation ∈ [0, 3000], a small fixed tz **tuple** (not a `set`/`dict` — set
iteration order is affected by `PYTHONHASHSEED`, which would break
"twice, same seed → identical"), latitude ∈ [−89.9, 89.9] (exclude the exact
poles), longitude ∈ [−180, 180], dates spanning a few years. Gate on the public
seam only:

```python
try:
    pt = PrayerTimes(coords, date, calculation_parameters=params)
except AstronomicalError:
    continue  # expected on undefined days under NONE
assert pt.fajr <= pt.sunrise <= pt.dhuhr <= pt.asr <= pt.maghrib <= pt.isha
```

Assert no NaN in outputs; on failure print seed + the case. Never import the
private `_schedule_defined`. Deterministic under the fixed seed.

**5c. Benchmark note** — extend
`docs/development/baseline/2026-10-12-phase6-benchmark.md` with before/after
ms on the Task 3 grid (profile first; no % target promised).

**Verify:** `pytest tests/test_fuzz_ordering.py tests/astronomy/test_solar_time.py
--no-cov` (twice, same seed → identical), then the full four gates.

---

## Task 6 (PR 6) — docs sweep

Consolidate the durable user-facing knowledge landed piecewise: the rounding
canon + two-tier tolerance policy (Task 1/2 wording) into
`docs/user/api-reference.md` and reflect it in `docs/user/citations.md`; the
timezone policy + local-date note in `docs/user/timezone.md`; the high-latitude
risk note in `docs/user/high-latitude.md`; the Windows install step in
`docs/user/getting-started.md`. No `docs/development/` references anywhere.
Frozen `docs/user/vX/` snapshots untouched. If a new page is added, register it
in the `docs_site/astro.config.mjs` sidebar (the sidebar is an explicit list)
and use relative links only (`getting-started/`, not `/getting-started/`).

**Verify:** `pytest --cov-fail-under=95` (docs gate
`test_docs_cover_public_api`), and the four gates.

---

## PR order (stacked, dependency-ordered)

1. Task 1 — 6.4 accessor + rounding canon (unblocks 6.1 tier-(a)).
2. Task 2 — 6.2 goldens (needs 6.4 for the tier asserts).
3. Task 3 — 6.1 harness + vectors + baseline (needs 6.4).
4. Task 4 — 6.3 matrix + 6.5 docs/`tzdata` pin (independent; parallelizable).
5. Task 5 — 6.6 cache + fuzz (needs the 6.1 grid for the benchmark note).
6. Task 6 — docs sweep.

## QA / acceptance per PR

- All four gates green locally, same commands as CI: `black --check src/`,
  `ruff check src/ tests/`, `mypy src`, `pytest --cov-fail-under=95`.
- Every behavior change has a named test with a concrete expectation (no
  "no crash" only); golden citations carry edition + page/URL.
- Accessor round-trips hold on default and tz-aware builds and on both clamp
  days; `night_fraction` default output byte-identical.
- Harness reads `tests/` only and prints max-delta diagnostics; vectors cover
  the fixed grid exactly; `generate_*.py` not collected.
- CI runs only under the forced `PYTHONTZPATH` DB with `tzdata` installed.
- Fuzz is deterministic under the fixed seed.
- `docs/development/` is referenced by nothing durable.

## Risks / notes

- **Golden pass bar:** the transit lock (11:46:18 UT ±10 s) differs from the
  repo's `SolarTime.transit` by ~7 s today; if the implementer's derivation
  lands outside ±10 s, reconcile the arithmetic before touching the bar. It is
  a chain-consistency lock (labelled as such), not independent physical truth.
- **Port drift (resolved for the grid, not eliminated):** `adhan-kotlin` is the
  `adhan2` rewrite. Its `highLatitudeRule` default is
  `HighLatitudeRule.recommendedFor(coordinates)` (`SEVENTH_OF_THE_NIGHT` above
  48°), unlike our fixed `MIDDLE_OF_THE_NIGHT`; the generator pins
  `MIDDLE_OF_THE_NIGHT` for like-for-like comparison and records the difference
  as an out-of-scope port finding. `adhanpy`'s `rounded_minute` truncates at
  minute 59 (`replace(minute=60)` → `ValueError` fallback), handled by the
  narrow `_minute_only_equal` artifact rule — if a grid row diverges beyond
  tier-(a) for any other reason, record it as a finding (not a silent widening,
  and not an executable action for a red assert).
- **`tzdata` pin is dev-only:** keeps runtime deps at zero; Windows end users
  still install `tzdata` themselves (documented, not packaged).
- **Cache invalidation:** elevation is applied downstream in `SolarTime` (not
  in `SolarCoordinates`), so the date-keyed cache needs no elevation key; the
  test clear hook follows the `UmmAlQuraCalendar`/`MabimsCalendar` precedent.
