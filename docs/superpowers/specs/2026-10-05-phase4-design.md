# Phase 4 Design — Advanced Hijri Calendar & Moon Sighting (4.1–4.6 core)

Date: 2026-10-05
Status: approved (brainstorming 5/5 sections)
Source slices: `docs/development/MILESTONE_PHASES_AND_SLICES.md` Phase 4 + fact-check pass 2026-10-02
Codebase baseline: `CHANGES.md` 1.1.0 (phases 1–3 landed); Phase 4 absent in `src/` (zero hits for `Hijri|Lunar|Yallop|Odeh|MABIMS|crescent|hilal`).

## 1. Decisions locked during brainstorming

- Scope: full `4.1–4.6` core (lunar + ΔT + geometry + Yallop + Odeh + MABIMS). `4.7` map export deferred.
- Consumer: both standalone and Phase 5 foundation, via pure functions first; Phase 5 calendars consume unchanged.
- ΔT: isolated to Phase 4 path. `SolarTime` / `PrayerTimes` unchanged, existing minute goldens byte-identical.
- Public API: full public. New symbols exported via `alfalak/__init__.py` `__all__`, covered by `test_public_api.py` + `test_blackbox_sweep.py`.
- Order: strict chain `4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6`, one PR per slice. No parallelization.

Global constraints (from `ARCHITECTURE.md`): stdlib only, zero runtime deps, fully typed (`mypy --disallow-untyped-defs` clean, `py.typed` shipped), errors via `AlFalakError` hierarchy, offline deterministic, public datetimes minute-rounded UTC (internal geometry unrounded for testability).

## 2. Module layout (Section 1)

New files under `src/alfalak/astronomy/` (pure math, no prayer logic):

- `LunarCoordinates.py` — `class LunarCoordinates(jd_tt)`: Meeus Ch.47 low-precision geocentric RA/Dec + distance (Tables 47.A–B). Golden Ex.47.a: JDE 2448724.5 (= 1992-04-12 0h TT) → λ=133.167265°, β=−3.229126°, Δ=368409.7 km.
- `DeltaT.py` — `delta_t(year) -> float` + explicit `override` param. Espenak-range polynomials (1986–2005 5th-degree; 2005–2050 `62.92+0.32217·t+0.005589·t²`, `t=y−2000`); Morrison/Stephenson noted for historical range; IERS-observed preferred for modern dates (documented, not bundled).
- `CrescentGeometry.py` — pure functions `sun_moon_geometry(dt_utc, coords, delta_t_override=None)` → dataclass (`ARCL, ARCV_geo, ARCV_topo_airless, DAZ, width, illumination, lag, age`) at local sunset `Ts` (existing `SolarTime`, elevation-aware) and best time `Tb = Ts + 4/9·Lag`. Topocentric vs geocentric distinguished in field names. Parallax (~54′–61.4′) corrected; Yallop takes geocentric ARCV, Odeh takes airless topocentric ARCV.
- `Yallop.py` — `yallop_q(...) -> float` + `yallop_zone(q) -> A–F` with boundaries `+0.216 / −0.014 / −0.160 / −0.232 / −0.293` (NAO TN No.69 §2–3, eq. 3.6). `ARCL` geocentric elongation, `cos ARCL = cos ARCV·cos DAZ`, topocentric width `W′ = SD′·(1−cos ARCL)`, `SD = 0.27245·π`, evaluated at `Tb`.
- `Odeh.py` — `odeh_v(...) -> float` + `odeh_class(v) -> A–D` (`V = ARCV − (−0.1018·W³ + 0.7319·W² − 6.3226·W + 7.1651)`, topocentric `W` arcmin, 737 records) + explicit `ARCL < 6.4° → D` rule. Classes `A V≥5.65 / B 2≤V<5.65 / C −0.96≤V<2 / D V<−0.96` (Exp. Astron. 18:39–64).
- `Mabims.py` — thin predicates over 4.3 outputs: `MABIMS_1992` (`alt ≥ 2° AND elong ≥ 3°`, OR `age ≥ 8h at moonset`; Labuan 1992) + `NEO_MABIMS_2021` (`alt ≥ 3° AND elong ≥ 6.4°` at sunset, age dropped; KBIR 2016 / adopted 2021). `MILESTONES.md` already reads `≥3°` — no fix needed.

## 3. Data flow (Section 2)

```
civil dt_UTC + Coordinates
  → CalendricalHelper.julian_day (Gregorian-only, unchanged)
  → JD_UTC + DeltaT.py → JD_TT (only inside Phase 4 calls)
  ├─→ SolarCoordinates(JD_TT) → Sun RA/Dec
  └─→ LunarCoordinates(JD_TT) → Moon RA/Dec + distance
  → SolarTime sunset Ts (existing, UTC, elevation-aware)
  → CrescentGeometry at Ts and Tb
  → Yallop.q / Odeh.V / Mabims predicates
  → (float q/V + zone/class enum; no datetimes — Phase 5 maps to Hijri)
```

`delta_t_override=None` defaults to polynomial; used value recorded alongside outputs used in goldens so IERS-vs-polynomial choice is auditable. No I/O, no network.

## 4. Errors + boundaries (Section 3)

- `ValidationError`: bad coordinates, NaN angles, negative width, unknown zone/method, `ΔT` year out of documented validity range.
- `AstronomicalError`: truly undefined geometry only (e.g. no sunset — polar day/night, following `PrayerTimes.py:80-85` precedent). Below-horizon Moon (negative ARCV) is valid input to q/V, not an error.
- Boundary policy: Yallop/Odeh edges + `ARCL<6.4°→D` asserted as half-open intervals with one golden per edge; arcminute lunar error stays in-zone except exactly on boundary — boundary tests document winning side.
- Degenerate azimuth (antipode): float in `[0,360)`, no raise (Qibla contract precedent).

## 5. Testing + goldens (Section 4)

- `4.1`: Ex.47.a values above; RA/Dec tolerance stated; no prayer regression.
- `4.2`: `ΔT(2025) ≈ 68.3–70.1 s` range + override respected + range docs.
- `4.3`: 2–3 known crescents (one confirmed + one negative, with announcement source + date); geo- vs topo- names asserted.
- `4.4/4.5`: published Yallop/Odeh reference cases per boundary; Yallop-vs-Odeh agreement matrix on small date×location grid (disagreements documented, not forced).
- `4.6`: both presets on same sunset instants + migration note (which historical dates flip 1992→2021).
- Every PR: `test_public_api.py` + `test_blackbox_sweep.py` updated; `black --check src/` → `ruff check src/ tests/` → `mypy src` → `pytest --cov-fail-under=95` green.

## 6. Out-of-scope + acceptance (Section 5)

Out: `4.7` map export; Phase 5 (`HijriDate`, `UmmAlQuraCalendar`, Takwim, sunset-transition, JSON deltas, `hijri` CLI); WMM/IGRF provider; ELP-2000 upgrade; IERS feed; any `SolarTime`/`PrayerTimes` behavior change.

Acceptance: six sequential PRs `4.1→4.6`, each with source-cited goldens + invariant updates; final `__all__` exposes new symbols; zero new deps.
