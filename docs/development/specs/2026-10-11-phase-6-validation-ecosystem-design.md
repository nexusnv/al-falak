# Phase 6 — Performance, Validation & Ecosystem: Design Spec

- Date: 2026-10-11
- Status: approved design, pre-plan
- Scope: full Phase 6 (slices 6.1–6.6) in one spec, implemented as stacked PRs.
- Decisions locked during brainstorming: full-phase scope (Phase-5 precedent);
  architecture A (additive hardening, no pipeline refactor); 6.4 read-only
  accessor (no constructor flag, default output byte-identical); 6.1 vendored
  golden vectors with pinned SHAs (no live port checkout); 6.3/6.5 docs + CI
  `tzdata` pin (no packaging dependency change, zero-deps preserved); 6.6 cache
  hygiene + report (no % speedup promise).

## 1. Background and goals

Phases 1–5 are landed (`src/alfalak/` ≈ prayer + qibla + sunnah + lunar +
calendar + 6-subcommand CLI with `--timezone`/`--city`). The 2026-10-02 slice
doc (`MILESTONE_PHASES_AND_SLICES.md` §Phase 6) is the baseline; parts are now
stale:

- 6.3/6.5 are mostly done: spring-forward + fall-back (`fold == 1`) tests exist
  (`tests/test_sunnah_times.py`), CLI `--timezone` with `--city` tz-default
  exists (`src/alfalak/cli/common.py`), city zones validated (`tests/test_cities.py`).
- 6.2 is partial: JD golden `2448908.5`, lunar Ex.47.a, JAKIM Takwim anchors,
  EoT Ch.28 formulation test exist; solar Ex.25.a / transit / USNO locks missing.
- 6.1, 6.4, 6.6 are still TODO: no benchmark harness, no unrounded accessor
  (`rounded_minute` post-offset is load-bearing in `PrayerTimes._rounded_minute`
  and `SunnahTimes.night_fraction`), no solar-coords cache, no seeded fuzz
  beyond fixed ≤200 sweeps.

Goals: (a) make the two-tier tolerance policy measurable (correction 2:
internal unrounded ≤1 s port-fidelity vs. public exact-minute agreement);
(b) lock independent truth (Meeus/USNO/Takwim) with edition-pinned goldens;
(c) close the timezone remainder (nonexistent-time policy, `tzdata` pin,
Windows guidance, high-latitude matrix); (d) hygiene perf + deterministic fuzz.
Non-goals: new astronomy, new calendars, pipeline refactor, live-port CI,
new runtime dependencies, public-output format changes.

## 2. Architecture (approach A: additive hardening)

No new packages. Changes per slice:

- 6.4: setters store the pre-rounding instant in a `_unrounded` map before
  calling `rounded_minute`; read-only accessor exposes them. No setter logic
  changes; rounding order canon documented once (offsets → half-up round →
  `astimezone`).
- 6.1: `tests/benchmark/` + `scripts/` harness reads vendored JSON vectors
  (each vector records source project, version tag, commit SHA, city×date grid)
  and compares tier-(a) unrounded outputs; failures print the max-delta case.
  Harness imports only the 6.4 accessor + public API (never private setters).
- 6.2: golden tests appended to existing modules (`tests/astronomy/`,
  `tests/test_prayer_times.py`); no new infrastructure.
- 6.3/6.5: one tz-matrix test file + docs edits (`docs/user/…`, man page note)
  + CI `tzdata` pin; no packaging dependency change.
- 6.6: bounded `functools.lru_cache` on JD-day `SolarCoordinates` reused
  within a `PrayerTimes` build (plus test-clear hook); seeded fuzz module over
  the public `PrayerTimes` seam only.

`alfalak.__init__` gains only the accessor names (added to `__all__`, fully
typed per `mypy --disallow-untyped-defs`). CLI gains no new subcommands;
only docs/help-text notes.

## 3. Components

### 3.1 Slice 6.4 — second-precision accessor

- `PrayerTimes.unrounded(prayer: Prayer) -> datetime` (tz-aware UTC, never
  rounded) backed by `self._unrounded: dict[Prayer, datetime]` filled in each
  `_set_*` before `_rounded_minute`. Unknown prayer → `ConfigurationError`
  (same contract as `time_for_prayer`).
- `SunnahTimes.unrounded_fraction(f, start=None, end=None) -> datetime`:
  same computation as `night_fraction` minus the `rounded_minute` call.
- Invariant (tested): `rounded_minute(unrounded(p)) == time_for_prayer(p)`
  for all prayers; `night_fraction(f) == rounded_minute(unrounded_fraction(f))`.
- Canonical rounding order locked in docs: per-prayer offsets applied
  pre-rounding, half-up minute rounding, `astimezone` last.

### 3.2 Slice 6.1 — cross-port benchmark harness

- Vendored vectors: `tests/benchmark/vectors/*.json`, each entry
  `{source, version, sha, city, date, method, unrounded:{…}, rounded:{…}}`.
  Adhan ports share the truncated-Meeus core with this repo (lineage:
  BatoulApps adhan-java root; Kotlin/Swift/JS official; adhanpy third-party),
  so deltas assert port fidelity, not physical truth — stated in-file.
- Fixed city×date grid (recorded in the harness); tier-(a) assert ≤1 s on
  unrounded vs. vectors; tier-(b) exact-minute on public rounded outputs.
- Baseline report committed under `docs/development/baseline/` next to
  `2026-09-24-baseline.md`; CI runs the harness; failures print max-delta case
  (city, date, prayer, delta).

### 3.3 Slice 6.2 — independent-reference goldens

- Meeus 2nd ed. (Willmann-Bell, 1998) Ex.25.a p.165: JDE 2448908.5 →
  α = 13h13m31.4s, δ = −7°47′06″; transit assertion; each cites page + edition.
- USNO spot checks (2–3 city×date) + 2–3 Takwim/JAKIM published times
  (source URL + date in-test, e-solat administrative-delta caveat repeated).
- Tolerances per two-tier policy: ±10 s full-chain, ±30 s coarse, ±60 s
  rise/set; public rounded outputs exact-minute.

### 3.4 Slice 6.3 — timezone robustness matrix (remainder)

Already covered (kept green, not re-specified): spring-forward
(2015-03-07/08 America/New_York) and fall-back (`fold == 1`, UTC-duration >
wall-clock by 1 h). New rows: high-latitude cases toward 60°+ exercising
polar rules (the actual risk class; Sydney kept as smoke only);
modern political/DST rule-change cases against the pinned `tzdata`;
nonexistent-local-time policy documented: prayer computation is
UTC-date-based, so the spring-forward gap constructs no local wall time —
no raise, behavior stated in-test with one asserted case. Each case states
expected behavior, never "no crash" alone.

### 3.5 Slice 6.5 — CLI timezone + packaging (remainder)

`--timezone` exists on prayer/sunnah paths with `--city` tz-default. Remainder:
Windows `tzdata` guidance in user docs (PyPI `tzdata` fallback — environment
requirement, not a package dependency); man-page + `cli.md` note; CI pins an
explicit `tzdata` version (exact version chosen at plan time and recorded in-test
alongside the matrix); unknown-zone errors keep exit-2 via
`parser.error`. No dependency or output-format change; UTC default unchanged.

### 3.6 Slice 6.6 — performance + fuzz

- Cache: `lru_cache(maxsize=…)` keyed by JD-day for `SolarCoordinates`,
  shared within a `PrayerTimes` build (prev/day/next + tomorrow rebuild in
  `SunnahTimes`); bounded only (no unbounded module dicts, no raw-float keys);
  `cache_clear` hook for tests. Benchmark note (before/after ms on the 6.1
  reference grid) committed with the PR — profile first, no % target promised
  (per-eval cost is µs of trig).
- Fuzz: `tests/test_fuzz_ordering.py`, stdlib `random` with fixed seed
  (following `test_parameterized_sweep.py` precedent), N=2000 random
  lat/lon/date across the full input ranges (lat −90…90, lon −180…180);
  asserts `fajr ≤ sunrise ≤ dhuhr ≤ asr ≤ maghrib ≤ isha`
  gated on schedule-defined days (polar NaN/non-ordering expected outside
  polar rules per PrayTimes higher-latitude docs — asserted separately);
  no NaN on defined days; failures print seed + case.

## 4. Data flow

Unrounded instants: setter computes instant → `_unrounded` store → public
accessor; rounded fields unchanged. Harness: vectors → accessor outputs →
delta report. Fuzz: seeded RNG → public `PrayerTimes` → ordering asserts.
Tz matrix: `ZoneInfo` inputs → existing UTC-duration paths → per-case asserts.
Bridge/CLI/calendar paths untouched except docs/help text.

## 5. Error handling (existing `AlFalakError` hierarchy only)

- `ConfigurationError`: accessor on unknown prayer; harness misuse
  (unknown vector source/method).
- `AstronomicalError`: propagated unwrapped from polar no-sunset paths
  (harness/fuzz surface the existing diagnostics, add none).
- `ValidationError`: fuzz never feeds invalid inputs (range-clamped
  generation); invalid `f` to `unrounded_fraction` follows
  `night_fraction` precedent.
- Harness over-threshold and fuzz counterexamples are test assertions with
  max-delta/seed diagnostics, not new error types. No bare `except`, no new
  exit codes.

## 6. Tests & docs

- Tests: accessor round-trip invariants; harness CI-green + committed
  baseline; goldens with page/URL+edition citations; tz matrix with behavior
  asserts; N=2000 seeded fuzz deterministic; new public names covered by
  `tests/test_public_api.py` + `test_blackbox_sweep.py` extensions.
- Docs: rounding-order canon + two-tier tolerance policy in user docs;
  nonexistent-time policy + Windows `tzdata` guidance + high-latitude risk
  note; frozen `docs/user/vX/` snapshots untouched; `MILESTONES.md` Phase-4
  Neo-MABIMS "≥ 4°" → "≥ 3°" fix rides along (still outstanding from 2026-10-02).
- Gates stay green: `black --check src/`, `ruff check src/ tests/`, `mypy src`
  (`--disallow-untyped-defs`), `pytest --cov-fail-under=95`.

## 7. PR order (stacked, dependency-ordered)

1. 6.4 accessor + rounding canon (unblocks 6.1 tier-(a)).
2. 6.2 goldens (independent truth early; needs 6.4 for tier asserts).
3. 6.1 harness + vendored vectors + baseline (needs 6.4).
4. 6.3 tz matrix remainder + 6.5 docs/`tzdata` pin (independent; parallelizable
   with 2–3).
5. 6.6 cache hygiene + fuzz (needs 6.1 grid for the benchmark note).
6. Baseline report + `MILESTONES.md` 4°→3° fix + docs sweep.

## 8. References

- Meeus, *Astronomical Algorithms*, 2nd ed. (Willmann-Bell, 1998):
  Ch.7 (JD) / Ch.15 (transit/rise-set) / Ch.25 (solar, Ex.25.a p.165) /
  Ch.28 p.183 (EoT) / Ch.47 (Moon, Ex.47.a).
- IANA time-zone theory.html (pre-1970 limits); Python `zoneinfo` + PyPI
  `tzdata` docs; PEP 495 (`fold`).
- BatoulApps adhan-java (lineage root); Fiqh Council NA notes (0.567°
  nominal assumption); PrayTimes higher-latitude docs (ordering gate scope).
