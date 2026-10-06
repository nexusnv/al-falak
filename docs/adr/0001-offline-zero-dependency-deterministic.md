# ADR-0001: Offline, Zero-Dependency, Deterministic Computation as Project Invariants

## Status

Accepted

## Date

2026-10-06

## Context

`al-falak` is an offline Islamic-astronomy library: coordinates + date +
method parameters go in, prayer times and Hijri dates come out, with no
network calls and no runtime dependencies beyond the Python standard
library. Building the Hijri converter raised the question explicitly:
month-start resolution by forward-walking an observational rule from an
epoch costs ~30s cold for modern UQU dates, and two tempting shortcuts
appeared — ship a precomputed month-start table, or speed up the
crescent geometry with coarser approximations. Both would trade away
properties the rest of the design already assumes (deterministic
goldens, offline CLI use, minute-stable outputs). This ADR records the
three properties as invariants so future performance work optimizes
within them instead of around them.

## Decision Drivers

- **Must stay offline**: users run this on machines without IANA data
  (Windows needs `tzdata` as an environment install), without network,
  and inside CLI one-shots. Anything requiring a download breaks them.
- **Must stay dependency-free**: `ARCHITECTURE.md` and the review gates
  enforce zero runtime dependencies. No NumPy/Skyfield-style speedup is
  available; geometry runs in pure-stdlib code.
- **Must stay deterministic**: golden tests pin exact dates against
  published tables. Any change that moves outputs (even by minutes at a
  knife-edge month) is a behavior change, not an optimization.

## Considered Options

### Option 1: Enshrine the invariants; optimize structurally (chosen)

Keep first-principles computation as the only conversion path. Address
cold-start cost with structural changes that preserve exact outputs:
re-anchor walks near the present (cf. MABIMS's 1445H anchor), retain
intermediate results in bounded caches, and only accept geometry
changes proven output-identical by the goldens.

### Option 2: Ship precomputed month-start tables

Bundle lookup data (e.g. official UMM-al-Qura tables) and compute only
past the table edge.

- **Pros**: instant cold conversions within coverage.
- **Cons**: coverage cliff (beyond the table you still need the walk, so
  two code paths plus fallback logic plus table versioning); provenance
  risk — at knife-edge months the published tables disagree with
  first-principles computation by a day (see `ALLOWED_DELTAS` in
  `tests/calendar/test_uqu.py`), so shipping a table bakes someone
  else's judgment into our outputs and can produce discontinuities at
  the table boundary.

### Option 3: Faster approximate geometry

Coarsen the conjunction search or trim iterations in the shared
crescent-geometry path.

- **Pros**: speeds up every observational calendar at once.
- **Cons**: directly threatens the documented knife-edge months where
  ±minutes flip a 29/30-day decision; contradicts the deterministic
  golden suite.

## Decision

**Offline, zero-dependency, deterministic computation are project
invariants.** Performance work must preserve all three: no network or
data-file dependencies, no new runtime packages, and byte-identical
outputs on every golden.

## Rationale

Two examples from the Hijri work show why the invariants pull their
weight:

1. **Unbounded horizon.** The UQU walk answers any date — 2030, 2060,
   2100 — with no data refresh. A table would need perpetual releases
   just to keep converting future dates, and every refresh would
   re-open the provenance question.
2. **Single source of truth.** With one computation path, a mismatch
   against a published table has exactly one explanation to
   investigate (model vs. reference, documented per month in
   `ALLOWED_DELTAS`). With a table + fallback, the same mismatch could
   be a stale table, a boundary discontinuity, or a model error —
   three explanations, and the goldens cannot distinguish them.

## Consequences

### Positive

- One code path per calendar: fewer failure modes, goldens that
  actually pin behavior, no data-pipeline maintenance.
- The library keeps working unchanged in air-gapped, embedded, and
  minimal-container environments.

### Negative

- Cold-start latency for observational calendars is a permanent
  engineering constraint, not a bug to wish away: it must be managed
  (anchors, caches) rather than eliminated (tables, approximations).
- Pure-stdlib geometry sets a floor on per-evaluation cost (~100ms
  order); walk length is the lever, not evaluation speed.

### Example of working within the invariants

The UQU re-anchor (walk modern targets from the verified 1445H anchor
instead of the 1423H epoch, keeping 1423H as the support floor) cut
cold-walk evaluations ~10x with zero output change — the 1445–1446
goldens pass unmodified, which is exactly the proof the invariants
demand.

## Related Decisions

- Future performance proposals touching `astronomy/` or `calendar/`
  must cite this ADR and show golden-identical outputs.

## References

- `ARCHITECTURE.md` — zero-dependency and error-hierarchy constraints
- `AGENTS.md` — review gates (`black`, `ruff`, `mypy`,
  `pytest --cov-fail-under=95`)
- `src/alfalak/calendar/UmmAlQuraCalendar.py` — epoch vs. walk-anchor
  design and the 1423H support floor
- `src/alfalak/calendar/MabimsCalendar.py` — 1445H anchor precedent
- `tests/calendar/test_uqu.py` — `ALLOWED_DELTAS` knife-edge record
