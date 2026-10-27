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
calendar + 7-subcommand CLI (prayer, qibla, sunnah, hijri, moon_sighting,
astro, cities) with `--timezone`/`--city`). The 2026-10-02 slice
doc (`MILESTONE_PHASES_AND_SLICES.md` §Phase 6) is the baseline; parts are now
stale:

- 6.3/6.5 are mostly done: spring-forward + fall-back (`fold == 1`) tests exist
  (`tests/test_sunnah_times.py`), CLI `--timezone` with `--city` tz-default
  exists (`src/alfalak/cli/common.py`), city zones validated (`tests/test_cities.py`).
- 6.2 is partial: JD golden `2448908.5`, solar Ex.25.a unit golden
  (α/δ/λ at abs=1e-5 deg in `tests/astronomy/test_astronomical.py::
  test_solar_coordinates`), lunar Ex.47.a, JAKIM computed 20/18 anchors,
  EoT Ch.28 chain (±10.2 s), USNO Raleigh rise/set/transit/twilight spot
  (`tests/astronomy/test_solar_time.py`) exist; missing is the independent
  transit golden at a stated longitude/zone, the formal two-tier tolerance
  mapping on existing goldens, and published Takwim values with source URLs.
- 6.1, 6.4, 6.6 are still TODO: no benchmark harness, no unrounded accessor
  (`rounded_minute` post-offset is load-bearing in `PrayerTimes._rounded_minute`
  and `SunnahTimes.night_fraction`), no solar-coords cache, no seeded fuzz
  beyond fixed ≤200 sweeps.

Goals: (a) make the two-tier tolerance policy measurable (correction 2:
internal unrounded ≤1 s port-fidelity vs. public boundary-aware minute
agreement per §3.2);
(b) lock independent truth (Meeus/USNO/Takwim) with edition-pinned goldens;
(c) close the timezone remainder (nonexistent-time policy, `tzdata` pin,
Windows guidance, high-latitude matrix); (d) hygiene perf + deterministic fuzz.
Non-goals: new astronomy, new calendars, pipeline refactor, live-port CI,
new runtime dependencies, public-output format changes.

## 2. Architecture (approach A: additive hardening)

No new packages. Changes per slice:

- 6.4: setters store the post-offset (post-`adjustments` +
  `method_adjustments`) pre-rounding UTC instant in a `_unrounded` map —
  i.e. the value after offset application, immediately before half-up
  rounding, not the raw input to `_rounded_minute`. Both Asr clamp sites
  (`asr < dhuhr` in `_set_asr`, `asr > maghrib` in `__init__`) re-assign
  `_unrounded[Prayer.ASR]` together with the public field (a clamped asr's
  unrounded equals the already-rounded clamp source; clamp-day asr is
  excluded from tier-(a)). Derived markers store the same post-offset
  pre-round value: `imsak`/`ishraq`/`dhuha` store the input to their final
  rounding (which embeds the already-rounded `fajr`/`sunrise` by design, so
  tier-(a) does not apply to them — tier-(b) only); `syuruk` shares
  `sunrise`'s unrounded instant (alias, no second rounding). No setter
  astronomy changes; rounding order canon documented once
  (offsets → half-up round in UTC → `astimezone` last).
- 6.1: `tests/benchmark/` vectors + pytest harness (no new top-level
  `scripts/`; generator scripts per source live under `tests/benchmark/`
  as non-pytest helpers, e.g. `generate_adhan_java.py` with pinned source
  SHA + toolchain, so vectors remain re-derivable offline with no live port
  checkout in CI; `testpaths = "tests"` and `packages = ["src/alfalak"]`
  are unaffected, with a separate CI step only if a non-pytest entry point
  is added). Each vector records source project, version tag, commit SHA,
  `generator` script + `seconds_procedure` (`fractional` ms preferred;
  `minute-only` sources are `rounded`-only with no `unrounded` key),
  and city×date grid; tier-(a) compares unrounded outputs for the six
  astronomical prayers only (`syuruk` covered by `sunrise`; derived markers
  tier-(b) only), tier-(b) uses the
  boundary-aware minute rule in §3.2 (bare exact-minute for `rounded`-only
  vectors). Harness reads `tests/` inputs only and
  imports only the 6.4 accessor + public API (never private setters).
- 6.2: golden tests appended to existing modules (`tests/astronomy/`,
  `tests/test_prayer_times.py`) preserving existing tighter bars; no new infrastructure.
- 6.3/6.5: one tz-matrix test file + docs edits (`docs/user/…`, man page note)
  + forced CI `tzdata` pin (`PYTHONTZPATH`-empty / `reset_tzpath()` so the
  pin is the DB under test); no packaging dependency change.
- 6.6: module-level cached factory for `SolarTime` midnight evaluations
  only, keyed on the calendar date — `_solar_coords_for_date(y, m, d)` with
  `functools.lru_cache` — which internally computes `julian_day(y, m, d)`
  (always exactly X.5 for midnight) and returns
  `SolarCoordinates(jd)`. No integer-JD variant: `SolarCoordinates(int(jd))`
  would evaluate 12 h early (midnight X.5 truncates to noon X), and keying on
  `int(jd)` while evaluating the raw float lets distinct JDs collide. (The
  .5 midnights are exactly representable as floats, so float keys would be
  safe; we key on date ints by discipline, not necessity.)
  `SolarCoordinates.__init__` itself unchanged. Explicitly out of scope:
  `CrescentGeometry` non-midnight evaluations (`_arcl_at_jd`,
  sunset/moonset JDs) must never use this cache (~1°/day error ≈ 2 min RA).
  Elevation needs no invalidation (it applies downstream in
  `SolarTime` altitude, not in `SolarCoordinates`). Bounded `maxsize` chosen
  at plan time with hit-rate note; `cache_clear` hook for tests, following
  the `UmmAlQuraCalendar`/`MabimsCalendar` precedent. Seeded fuzz module over
  the public `PrayerTimes` seam only via try/except `AstronomicalError`
  (never the private `_schedule_defined` gate — substitution rules succeed
  exactly when the requested grid is undefined), with explicit config in
  §3.6. Per-`PrayerTimes` overhead is ~10 datetimes plus the tomorrow
  rebuild — negligible, noted not optimized.

No `__all__` change: the 6.4 accessors are methods, not top-level exports.
If any top-level name is added later, update `__all__` +
`tests/test_public_api.py` exact-list assert +
`docs/user/api-reference.md` (enforced by `test_docs_cover_public_api`)
together; the new methods always require extending that test's hard-coded
method tuple plus `api-reference.md` regardless. CLI gains no new subcommands; only docs/help-text notes.

## 3. Components

### 3.1 Slice 6.4 — second-precision accessor

- `PrayerTimes.time_for_prayer_unrounded(prayer: Prayer) -> datetime`
  (preferred explicit name; bare `unrounded(prayer)` accepted as an alias
  only if the plan records it — the value is adjusted, not raw astronomy)
  returning tz-aware UTC, never rounded, backed by
  `self._unrounded: dict[Prayer, datetime]` filled with the post-offset
  (post-`adjustments` + `method_adjustments`) pre-rounding instant. `syuruk`
  shares the `sunrise` entry (alias, no second rounding). `Prayer.NONE` and
  any non-`Prayer` input → `ConfigurationError` (same contract as
  `time_for_prayer`, which already rejects `NONE`). Both Asr clamp sites
  update `_unrounded[Prayer.ASR]` together with `self.asr`; a clamped asr's
  stored value is the already-rounded clamp source.
- `SunnahTimes.night_fraction_unrounded(f, start=None, end=None) -> datetime`
  (preferred explicit name; bare `unrounded_fraction` accepted as an alias
  only if the plan records it) returning tz-aware UTC, never rounded: same
  computation as `night_fraction` minus the `rounded_minute` call and minus
  the final `astimezone` (reuses `_coerce_utc` anchor validation and the
  `(0, 1)` exclusive `ValidationError` checks).
- Invariants (tested, timezone-aware): with `tz = self.time_zone`
  (`None` means UTC),
  `rounded_minute(time_for_prayer_unrounded(p)).astimezone(tz or UTC) ==
  time_for_prayer(p)` for every prayer including clamp days and derived
  markers (clamp-day asr holds by construction since both sides share the
  clamped value);
  `rounded_minute(night_fraction_unrounded(f, start, end)).astimezone(zone)
  == night_fraction(f, start, end)` for default and explicit anchors.
  Rounding is always in UTC, conversion last — rounding a zoned wall time
  directly is not equivalent across DST.
- Canonical rounding order locked in docs: per-prayer offsets applied
  pre-rounding, half-up minute rounding in UTC, `astimezone` last. The
  accessor returns the adjusted pre-round instant (offsets included), and
  the reference docs state this explicitly so consumers do not mistake it
  for raw solar geometry.

### 3.2 Slice 6.1 — cross-port benchmark harness

- Vendored vectors: `tests/benchmark/vectors/*.json`, each entry
  `{source, version, sha, generator, seconds_procedure, city, date, method,
  unrounded:{…}, rounded:{…}}`, where `generator` names the committed
  per-source generator script under `tests/benchmark/` (instrumented port
  checkout dumped offline — no live port checkout in CI) and
  `seconds_procedure` records how seconds were obtained (`fractional` with
  ms resolution preferred; `minute-only` sources recorded as `rounded`-only
  with no `unrounded` key). `unrounded`/`rounded` keys are prayer names
  (`fajr`, `sunrise`, `dhuhr`, `asr`, `maghrib`, `isha`; `rounded` may
  additionally carry `imsak`/`ishraq`/`dhuha`); `date` is the UTC calendar
  date the values were computed from (the §3.3 convention). Ports that expose only minute-rounded outputs are
  recorded as `rounded`-only and excluded from tier-(a); never fabricate
  seconds. Adhan ports share the truncated-Meeus core with this repo
  (lineage: BatoulApps adhan-java root; Kotlin/Swift/JS official; adhanpy
  third-party), so deltas assert port fidelity, not physical truth —
  stated in-file.
- Fixed city×date grid (recorded in the harness); tier-(a) asserts ≤1 s on
  unrounded vs. vectors for the six astronomical prayers (fajr, sunrise,
  dhuhr, asr, maghrib, isha) only — `syuruk` is `self.sunrise` by
  assignment so a separate case adds no coverage (a port deriving syuruk
  differently could spuriously fail); `imsak`/`ishraq`/`dhuha` are built
  from already-rounded `fajr`/`sunrise` so a port deriving them from
  unrounded parents can differ by a full minute at exact parent fidelity;
  derived markers get tier-(b) only. Quantization note: our unrounded side
  is whole-second-quantized (`TimeComponents` truncates to integer seconds,
  offsets are whole minutes/seconds), so a "within 1 s of a whole-second
  boundary" clause is vacuous for our side. Compare truncated-to-truncated
  at ≤1 s by default; when the vector carries fractional ms
  (`seconds_procedure: fractional`), floor the port value to whole seconds
  the same way before comparing, and document any |Δ| in (1 s, 2 s) as a
  truncation-straddle with the fractional evidence quoted — do not add a
  blanket 1-s-boundary escape. Tier-(b) boundary-aware minute rule on public
  rounded outputs: exact-minute match, except a 1-minute difference is
  accepted iff the pre-round seconds — our side from the 6.4 accessor's
  second/microsecond, the port side from the vector's `unrounded`
  second/microsecond — are within 1 s of the :30 rounding boundary
  (prevents flakes from a sub-second port delta flipping the minute). The
  rounded outputs themselves (`second == 0`) must never be used for this
  check (they sit 30 s from the boundary, so the exception could never
  fire). For `rounded`-only vectors the port side has no seconds, so the
  rule degenerates — require bare exact-minute match and state this in-file.
- Harness reads `tests/` inputs only (never `docs/development/` paths);
  baseline report is scratch under `docs/development/baseline/` next to
  `2026-09-24-baseline.md` with no code/doc links pointing at it (per the
  `docs/development/` hard rule). CI runs the harness; failures print
  max-delta case (city, date, prayer, delta).

### 3.3 Slice 6.2 — independent-reference goldens

- Preserve the existing locks; do not duplicate them at looser bars:
  Ex.25.a α/δ/λ unit golden (`test_solar_coordinates`, abs=1e-5 deg ≈
  0.036″), EoT Ch.28 chain (±10.2 s), USNO Raleigh rise/set/transit/twilight
  spot (`test_solar_time.py`), JAKIM computed 20/18 anchors. New in this
  slice: a transit golden at an explicitly stated longitude (Greenwich lon 0
  unless the plan states otherwise, with timezone stated) whose expected
  value is hand-worked from the published Ex.25.a α (13h13m31.4s) via the
  Meeus Ch.15 transit equation (page pinned at plan time) — not produced by
  running this repo's `corrected_transit` on the same JD, which would be as
  self-referential as the existing `test_equation_of_time_agrees_with_transit`
  characterization it replaces as truth evidence. If no hand-worked value is
  produced, label the case a chain-consistency lock (not independent truth)
  and cite the Ch.15 transit-equation page actually used; each golden cites
  page + edition.
- USNO spot checks (2–3 city×date, cities/dates/method fixed at plan time,
  not cherry-picked at implementation) + 2–3 published Takwim/JAKIM times
  (source URL + local date + explicit local↔UTC date mapping in-test:
  `date` is a UTC calendar date, so e.g. a KL fajr on UTC date D displays
  local D+1 — the golden pins which UTC date each published local value was
  computed from; e-solat administrative-delta caveat repeated).
- Tolerance mapping (two-tier policy): keep the existing tighter bars where
  they exist (Ex.25.a abs=1e-5 deg, EoT ±10.2 s — do not loosen to a
  generic "±1″-class"); transit/EoT full-chain ±10 s;
  USNO rise/set ±60 s (low-sun-angle amplification); Takwim spot values
  minute-agreement with documented administrative delta; public rounded
  outputs use the §3.2 boundary-aware minute rule, not bare exact-minute.

### 3.4 Slice 6.3 — timezone robustness matrix (remainder)

Already covered (kept green, not duplicated): spring-forward
(2015-03-07/08 America/New_York) and fall-back (`fold == 1`, UTC-duration >
wall-clock by 1 h, `tests/test_sunnah_times.py`). New rows: high-latitude
cases toward 60°+ exercising polar rules (the actual risk class; Sydney
kept as smoke only); modern political/DST rule-change cases against the
pinned `tzdata` (zone/date pairs fixed at plan time, with pinned version
plus the actually-used `TZPATH` logged in diagnostics — see §3.5 for why
the pin must be forced); a local-date-boundary row (e.g.
Pacific/Kiritimati +14 asserting the UTC-date vs local-date shift, same
trap as the Takwim UTC-date convention in §3.3); nonexistent-local-time
policy documented: prayer computation builds UTC instants then
`astimezone`s, so the spring-forward gap constructs no local wall time — no
raise, behavior stated in-test with one asserted case. Each case states
expected behavior, never "no crash" alone.

### 3.5 Slice 6.5 — CLI timezone + packaging (remainder)

`--timezone` exists on prayer/sunnah paths with `--city` tz-default, and
that default is already documented in `docs/user/cli.md:124-125,:217-220`
and `debian/al-falak.1:53`, while `docs/user/timezone.md:71-76` already has
the Windows `pip install tzdata` wording — do not duplicate these; the docs
remainder is only the missing install-step note (e.g. in
`getting-started.md`, which currently mentions neither `tzdata` nor
Windows). CI pins an explicit `tzdata` version in CI requirements AND forces
it to be the database under test — preferred: `PYTHONTZPATH=` empty in the
CI step so the pinned PyPI package wins over `/usr/share/zoneinfo` (a bare
pip pin is a no-op on Linux runners where the system DB shadows the
package). If a `zoneinfo.reset_tzpath()` approach is used instead of the env
var, it must run in a fixture that saves/restores global `TZPATH`
(try/finally `reset_tzpath()`) so later tests are unaffected, and must skip
(`pytest.importorskip("tzdata")`) when the package is absent — otherwise a
plain Linux checkout without `tzdata` turns every subsequent `ZoneInfo(...)`
into `ZoneInfoNotFoundError`. Tests log both the used `TZPATH` and
`importlib.metadata.version("tzdata")` in diagnostics but never assert
equality, so routine database updates do not redden the suite (offset
asserts are safe because the forced path pins the DB under test);
unknown-zone errors keep exit-2 via `parser.error`. No dependency or
output-format change; UTC default unchanged.

### 3.6 Slice 6.6 — performance + fuzz

- Cache: module-level `_solar_coords_for_date(y, m, d)` with
  `functools.lru_cache` (key is the `(y, m, d)` int triple), returning
  `SolarCoordinates(julian_day(y, m, d))`; `SolarTime`-midnight-only, shared
  across the prev/day/next evaluations within a `PrayerTimes` build and the
  tomorrow rebuild in `SunnahTimes`. Never `CrescentGeometry` non-midnight
  JDs. No `int(jd)` key or `SolarCoordinates(int_jd)` call (12 h error;
  see §2). Bounded `maxsize` only (no unbounded module dicts);
  `cache_clear` hook for tests. Benchmark note (before/after ms on the 6.1
  reference grid, location: scratch `docs/development/baseline/` with no
  links pointing at it) committed with the PR — profile first, no % target
  promised (per-eval cost is µs of trig).
- Fuzz: `tests/test_fuzz_ordering.py`, stdlib `random` with fixed seed
  (following `test_parameterized_sweep.py` precedent), N=2000 with explicit
  config fixed at plan time: method (e.g. MUSLIM_WORLD_LEAGUE),
  `PolarCircleRule=NONE` (fixed — substitution rules would make the error
  branch unreachable since undefined requested grids still succeed; they are
  covered by `gen_polar_cases` in `test_parameterized_sweep.py:428-436`,
  not here), madhab, elevation, tz. Latitude range excludes the exact poles
  (e.g. ±89.9, since `|lat| == 90` has no rise/set date for the `NONE` /
  `NEAREST_DAY` path — `NEAREST_LATITUDE` would still succeed per
  `test_parameterized_sweep.py:428-436`, which is why it is not the rule
  here). Lon −180…180. Gate on the public seam only: try
  `PrayerTimes(...)`; on `AstronomicalError` pass (expected on undefined
  days for `NONE`); on success assert `fajr ≤ sunrise ≤ dhuhr ≤ asr ≤
  maghrib ≤ isha` and no NaN in outputs (public API never returns NaN —
  undefined days raise `AstronomicalError`; never import the private
  `_schedule_defined` — it classifies the requested grid, not the
  substituted one); failures print seed + case.

## 4. Data flow

Unrounded instants: setter computes instant → apply offsets → post-offset
pre-round UTC store (both Asr clamp sites update the store together) →
public accessor; rounded fields unchanged (`syuruk` aliases `sunrise`).
Harness: vectors → accessor outputs (tier-(a) six only, `syuruk` covered by
`sunrise`; derived markers tier-(b) only) → delta report (vectors carry their generator script;
rounded-only ports excluded from tier-(a)). Fuzz: seeded RNG → public
`PrayerTimes` (`PolarCircleRule=NONE`) → try/except: success asserts
ordering, `AstronomicalError` expected on undefined days.
Tz matrix: `ZoneInfo` inputs (forced `PYTHONTZPATH` DB) → existing
UTC-duration paths → per-case asserts. Bridge/CLI/calendar paths untouched
except docs/help text.

## 5. Error handling (existing `AlFalakError` hierarchy only)

- `ConfigurationError`: accessor on `Prayer.NONE`/non-`Prayer`/unknown
  prayer (same contract as `time_for_prayer`); harness misuse
  (unknown vector source/method).
- `AstronomicalError`: propagated unwrapped from polar no-sunset paths
  (harness/fuzz surface the existing diagnostics, add none).
- `ValidationError`: fuzz never feeds invalid inputs (range-clamped
  generation); invalid `f` to `night_fraction_unrounded` follows
  `night_fraction` precedent.
- Harness over-threshold and fuzz counterexamples are test assertions with
  max-delta/seed diagnostics, not new error types. No bare `except`, no new
  exit codes.

## 6. Tests & docs

- Tests: accessor round-trip invariants (timezone-aware, §3.1, including
  adjustment-bearing methods and both Asr clamp sites); harness CI-green +
  committed baseline (scratch, no code links); goldens preserve existing
  tighter bars and add page/URL+edition citations with per-golden tolerance
  mapping plus local↔UTC date pins; tz matrix with behavior asserts
  (incl. local-date-boundary row); N=2000 seeded fuzz deterministic
  (`PolarCircleRule=NONE`, gated on the public outcome); methods need no
  `__all__` change (no coverage update unless a top-level name is added, in
  which case extend `tests/test_public_api.py` + `test_blackbox_sweep.py` +
  api-reference docs together) — but the new methods must be added to the
  `test_docs_cover_public_api` hard-coded method tuple and to
  `docs/user/api-reference.md` regardless, since that gate does not read
  `__all__` for methods.
- Docs: rounding-order canon (adjusted pre-round semantics stated) +
  two-tier tolerance policy in user docs; nonexistent-time policy +
  local-date-convention note + Windows `tzdata` install wording (already
  partially present — extend, do not duplicate) + high-latitude risk note; frozen `docs/user/vX/` snapshots untouched.
- Gates stay green: `black --check src/`, `ruff check src/ tests/`, `mypy src`
  (`--disallow-untyped-defs`), `pytest --cov-fail-under=95`.

## 7. PR order (stacked, dependency-ordered)

1. 6.4 accessor + rounding canon (unblocks 6.1 tier-(a)).
2. 6.2 goldens (independent truth early; needs 6.4 for tier asserts).
3. 6.1 harness + vendored vectors + baseline (needs 6.4; baseline committed
   here, not repeated later).
4. 6.3 tz matrix remainder + 6.5 docs/`tzdata` pin (independent; parallelizable
   with 2–3).
5. 6.6 cache hygiene + fuzz (needs 6.1 grid for the benchmark note).
6. Docs sweep (rounding canon, tolerance policy, tz policy, Windows guidance).

Dropped: the `MILESTONES.md` Neo-MABIMS 4°→3° fix is already landed
(`MILESTONES.md` reads ≥3°; recorded in the v1.1.0 release note) — no
ride-along.

## 8. References

- Meeus, *Astronomical Algorithms*, 2nd ed. (Willmann-Bell, 1998):
  Ch.7 (JD) / Ch.15 (transit/rise-set) / Ch.25 (solar, Ex.25.a p.165) /
  Ch.28 p.183 (EoT) / Ch.47 (Moon, Ex.47.a).
- IANA time-zone theory.html (pre-1970 limits); Python `zoneinfo` + PyPI
  `tzdata` docs; PEP 495 (`fold`).
- BatoulApps adhan-java (lineage root); Fiqh Council NA notes (0.567°
  nominal assumption); PrayTimes higher-latitude docs (ordering gate scope).
