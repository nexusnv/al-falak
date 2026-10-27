# Cross-port benchmark (Phase 6)

This directory contains reference generators and a cross-port comparison harness.

## Purpose
The harness (`test_cross_port.py`) compares the local al-Falak implementation
against vendored reference vectors produced by two ports:

- `adhan_kotlin` — `batoulapps/adhan-kotlin` (the maintained adhan2; the "adhan-java root" note is a stale citation). Pinned at `e23d14385f6203954256b935ef91dc3c6565de34` (2026-08-21). Generated twice per entry: `Rounding.NONE` -> `unrounded` (seconds_procedure: `"second"`) and `Rounding.NEAREST` -> `rounded` (adhan2's Rounder.NEAREST = Float.roundToInt, half-away-from-zero). High-latitude rule is pinned to `MIDDLE_OF_THE_NIGHT` on every method's parameters copy (never the bare constructor).
- `adhanpy` — `alphahm/adhanpy` pinned at `f9cfed51a857cb6a8436ad4f5685e7ac27896782` (2024-04-06). Minute-only output (`seconds_procedure: "minute-only"`), no `unrounded` key; exercises the minute-only tier-(b) branch including the documented rollover artifact.

## Grid
12 mid-latitude rows × 2 methods (`MUSLIM_WORLD_LEAGUE`, `NORTH_AMERICA`) = 24 entries per source. The London 51.5° solstice rows rely on the high-latitude fallback; they are defined on our side and on adhan2 under `MIDDLE_OF_THE_NIGHT`. Polar circle cases are not included. Elevation 0, UTC-only.

## Vector schema
Each `vectors/<source>.json`:
- `source`, `version`, `sha`, `generator`, `seconds_procedure` (`"fractional"` | `"second"` | `"minute-only"`), `rounded_rounding`, `high_latitude_rule`, `entries`
- each entry: `{city, latitude, longitude, date, method, unrounded?, rounded}` with prayers `fajr/sunrise/dhuhr/asr/maghrib/isha`, ISO-8601 UTC. `unrounded` only for `fractional|second`. `rounded` is the port's rounded output.

## Regenerating vectors
The generator scripts are reference implementations. They are **not** collected by pytest.

- `generate_adhanpy.py` — creates a temp venv, installs adhanpy at the pinned SHA, writes `vectors/adhanpy.json` (rounded only). Requires internet unless `--source-dir` points at a checkout of the pinned SHA.
- `generate_adhan_kotlin.py` — clones adhan-kotlin at the pinned SHA, injects a scratch JVM test, runs `:adhan:jvmTest`, and writes `vectors/adhan_kotlin.json` twice per entry (Rounding.NONE and Rounding.NEAREST). Requires JDK 17+ (`JAVA_HOME` or `java` on `PATH`) and Gradle; pass `--gradle-bin` to reuse an installed Gradle instead of downloading the pinned wrapper (Gradle 9.5.1).

**Vectors are vendored.** They are committed under `vectors/` so the harness runs offline and deterministically in CI. Regenerate only when the pinned SHA or the grid changes, and commit the resulting JSON.

## Comparison
The harness asserts that every source in `grid.SOURCE_PINS` has a committed
vector file, so deleting one cannot silently halve coverage.

- Tier-(a): for `second`/`fractional` sources, compare `time_for_prayer_unrounded` (UTC) to the vector's `unrounded` instant at ≤ 1 s (6 prayers).
- Tier-(b): compare rounded values using `_boundary_minute_equal` (allows a single ±60s flip if either side's pre-round second was within ~1 s of :30). For `minute-only` vectors, use `_minute_only_equal` to accept adhanpy's documented rollover artifact (truncates at :59 second>=30 instead of rolling hour) — never blanket exact-minute equality. Include `syuruk` only at tier-(b) via `sunrise`. Derived markers (`imsak/ishraq/dhuha`) are not present in either port's vectors, so they are exercised by the existing golden/ordering suites rather than this harness.
