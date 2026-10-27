# Phase 6 benchmark baseline

Status: Task 3 (6.1) and Task 5 (6.6) complete; vectors are vendored and the
harness runs offline.

## Cross-port grid

- Directory: `tests/benchmark/` with `README.md`, `grid.py`,
  `generate_adhan_kotlin.py`, `generate_adhanpy.py`, `test_cross_port.py`,
  and committed vectors under `vectors/`.
- Grid: 12 rows × 2 methods = 24 entries per source (Raleigh×2, London×2,
  Singapore, Tokyo, Sydney, Nairobi, New York, Cape Town, Madrid,
  Kuala Lumpur).
- Sources pinned:
  - **adhan_kotlin** (`batoulapps/adhan-kotlin`, the maintained adhan2):
    SHA `e23d14385f6203954256b935ef91dc3c6565de34` (2026-08-21).
    Generated twice per entry: `Rounding.NONE` → `unrounded`
    (`seconds_procedure="second"`) and `Rounding.NEAREST` → `rounded`.
    High-latitude rule pinned to `MIDDLE_OF_THE_NIGHT` via
    `CalculationMethod.<METHOD>.parameters.copy(highLatitudeRule=...)`.
    Reproduced locally with Temurin JDK 21.0.13 and Gradle 9.5.1.
  - **adhanpy** (`alphahm/adhanpy`): SHA
    `f9cfed51a857cb6a8436ad4f5685e7ac27896782` (2024-04-06), minute-only
    (`seconds_procedure="minute-only"`), no `unrounded` key.
- Comparison: tier-(a) ≤ 1 s vs vector `unrounded` (floor fractional to whole
  seconds) for the six astronomical prayers; tier-(b) uses
  `_boundary_minute_equal`, and minute-only sources use
  `_minute_only_equal` (accepts adhanpy's minute-59 / second ≥ 30 truncation
  artifact instead of rolling the hour). `syuruk` is checked as the sunrise
  alias; grid coverage is asserted exactly.

## Results (2026-10-24, Linux x86_64, CPython 3.13)

| Source | Entries | Max tier-(a) delta | Tier-(b) exact | Boundary flips | Minute-only artifacts |
|---|---:|---:|---:|---:|---:|
| adhan_kotlin | 24 | 0.000 s | 144 / 144 | 0 | — |
| adhanpy | 24 | — | 141 / 144 | 0 | 3 |

The three adhanpy artifacts are the known minute-59 rollovers; they are
accepted only by `_minute_only_equal`, never by blanket minute equality.
No tier-(a) or tier-(b) mismatch required a tolerance widening.

## Solar-coordinate cache (Task 5)

`_solar_coords_for_date` is an `lru_cache(maxsize=512)` keyed on
`(year, month, day, day_offset)`; `SolarTime` asks for offsets −1/0/+1.
Elevation is applied downstream in `SolarTime`, so it is not part of the key.
`clear_solar_coords_cache()` is the test hook.

Measured with the cache bypassed via the wrapped function vs enabled, five
repetitions, best-of/median (same machine/process):

| Workload | Before (no cache) | After | Median speed-up |
|---|---:|---:|---:|
| Task 3 grid (24 entries) | 5.46 ms | 3.31 ms | 1.65× |
| Raleigh 2024, 365 days × 1 method | 78.67 ms | 60.33 ms | 1.30× |

Cache hit rate over the grid benchmark: 1368 hits / 72 misses = 0.950.
Over the 365-day sweep: 16410 / 5490 = 0.749 (the `(y,m,d,offset)` key stores
each date under up to three offsets, and the 512-entry cap is reached during
the sweep). Both are correctness-neutral: the cache is a pure memo of
`SolarCoordinates(julian_day(...) + offset)`.

## Known gaps

- **Task 2b (USNO spot rows)**: the USNO one-day-table endpoint reset the TCP
  connection from this environment on 2026-10-12 and again on 2026-10-24.
  Per the plan's fallback, no unverifiable numbers were substituted; the
  existing Raleigh USNO-derived row remains the independent reference.
- **Derived markers** (`imsak`/`ishraq`/`dhuha`) are not exported by either
  port's vectors, so they remain covered by the existing golden/ordering
  suites rather than this harness.
