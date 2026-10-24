---
title: Citations
description: Attribution and references for al-falak.
---

# Citations

## Original authors and projects

- **batoulapps** — Original `adhan` library in [Java](https://github.com/batoulapps/adhan-java), [JavaScript](https://github.com/batoulapps/adhan-js), [Swift](https://github.com/batoulapps/adhan-swift), and [Kotlin](https://github.com/batoulapps/adhan-kotlin). The astronomical calculation methods, formulas, and overall architecture are derived from these implementations.
- **alphahm** — Original [adhanpy](https://github.com/alphahm/adhanpy) Python port. This fork continues from that work.

## Astronomical calculation sources

The prayer time calculation methods, mathematical formulas, and computational steps are derived from:

- **Jean Meeus** — *Astronomical Algorithms* (2nd ed., Willmann-Bell, 1998). The core astronomical formulas for solar position, equation of time, and hour angle calculations.
- **US Naval Observatory (USNO)** — Solar position algorithms and twilight calculations. Reference: [aa.usno.navy.mil](https://aa.usno.navy.mil/)
- **PrayTimes.org** — Standard prayer time calculation methods and Fajr/Isha angle conventions. Reference: [praytimes.org](https://praytimes.org/)

## Moon-sighting sources

The crescent geometry and visibility criteria are derived from:

- **Jean Meeus** — *Astronomical Algorithms* (2nd ed.), Ch. 47 low-precision lunar position (Tables 47.A/47.B); validated against Example 47.a.
- **Fred Espenak (NASA)** — Delta-T polynomial for 2005–2050 (`62.92 + 0.32217·t + 0.005589·t²`, `t` = years since 2000), as published with the NASA eclipse predictions; known ~5–6 s high vs IERS observed values by 2024–2025.
- **Bernard Yallop** — `q`-criterion and visibility zones A–F from geocentric ARCV and crescent width.
- **Mohammad Odeh** — `V`-criterion and classes A–D from topocentric ARCV and crescent width, with the 6.4° elongation (Danjon) floor.
- **MABIMS** (Malaysia, Brunei, Indonesia, Singapore) — 1992 rule (altitude ≥ 2° and elongation ≥ 3°, or age ≥ 8 h) and Neo-MABIMS 2021 (altitude ≥ 3° and elongation ≥ 6.4°).

## Hijri calendar sources

The calendar rules and cross-check oracles behind the converter are:

- **Umm al-Qura 1423H rule** — month-start rule in force since 1423H / 15 Mar 2002 (geocentric conjunction before Makkah sunset and moonset after Makkah sunset → new month; see R. H. van Gent's survey of the Umm al-Qura variants and KACST publications). Earlier variants (1392H scheme, 1420–1422H interim criteria) are out of scope.
- **Neo-MABIMS 2021** — criteria adopted at the 2016 KBIR (Informal Meeting of MABIMS Ministers of Religion) and enforced from 2021: at local sunset, topocentric lunar altitude ≥ 3° and elongation ≥ 6.4°. Supersedes the 1992 Labuan rule (listed above, not implemented).
- **Tabular Type IIa ("Kuwaiti") pattern** — 30-year arithmetic cycle with 11 leap years (years 2, 5, 7, 10, 13, 16, 18, 21, 24, 26, 29); the same construction underlying e.g. Microsoft .NET `HijriCalendar` before per-install `HijriAdjustment`.
- **Cross-check oracles** — published Umm al-Qura month starts cross-checked against the `hijri-converter` (v2.3.2) and `hijridate` UQU tables over 1445–1446H; MABIMS spot checks against JAKIM / Penyimpan Mohor Besar Malaysia and Kemenag Indonesia announcements (±1 day proxy variance documented).

## Geodesy and geomagnetism sources

The Qibla direction, distance, and compass-heading calculations are derived from:

- **Charles F. F. Karney** — *Algorithms for geodesics*, *J. Geodesy* 87, 43–55 (2013). DOI: [10.1007/s00190-012-0578-z](https://doi.org/10.1007/s00190-012-0578-z). The ellipsoidal inverse is vendored from [GeographicLib](https://geographiclib.sourceforge.io/) (MIT licensed).
- **T. Vincenty** — *Direct and inverse solutions of geodesics on the ellipsoid with application of nested equations*, *Survey Review* 23(176), 88–93 (1975). DOI: [10.1179/sre.1975.23.176.88](https://doi.org/10.1179/sre.1975.23.176.88). Deliberately not used: documented non-convergence for nearly-antipodal points.
- **National Geospatial-Intelligence Agency (NGA)** — WGS 84 defining constants (`a = 6378137.0 m` exact, `f = 1/298.257223563` exact).
- **I. Todhunter** — *Spherical Trigonometry for the Use of Colleges and Schools* (p. 50). The spherical bearing formula.
- **Spherical-vs-ellipsoidal bearing comparisons** — reported worst-case figures repeated from the `Qibla` docstring lineage; full primary references to be pinned before quoting specific studies.
- **NOAA National Centers for Environmental Information (NCEI)** — magnetic declination sign convention (positive east) and the World Magnetic Model (WMM2025, 5-year cycle).

## Calculation method sources
| Method | Source |
|---|---|
| Muslim World League | Fajr angle 18°, Isha angle 17° |
| ISNA (North America) | Fajr angle 15°, Isha angle 15° |
| Egyptian | Fajr angle 19.5°, Isha angle 17.5° |
| Karachi | Fajr angle 18°, Isha angle 18° |
| Umm al-Qura | Fajr angle 18.5°, Isha interval 90 minutes |
| Moonsighting Committee | Fajr angle 18°, Isha angle 18°, seasonal adjustments |
| Kuwait | Fajr angle 18°, Isha angle 17.5° |
| Qatar | Fajr angle 18°, Isha interval 90 minutes |
| Singapore | Fajr angle 20°, Isha angle 18° |
| UOIF | Fajr angle 12°, Isha angle 12° |

## Golden test references

Tolerances are two-tier and deliberately narrow:

- **Transit / equation-of-time full-chain**: ±10 s. The Greenwich transit case is a chain-consistency lock derived from the published Meeus examples, not an independent physical truth.
- **USNO rise/set**: ±60 s, matching the resolution of the published one-day tables.
- **Takwim / e-solat**: exact agreement after subtracting a documented per-prayer administrative delta (JAKIM applies minute-level adjustments).
- **Unchanged tighter bars**: Meeus Ex. 25.a right ascension `abs=1e-5` deg and the equation-of-time golden `abs=0.17` min (±10.2 s).

- Meeus, J. — *Astronomical Algorithms* (2nd ed., Willmann-Bell, 1998), Ex. 25.a (p. 165) and Ex. 28.a (p. 183). Used for the Greenwich solar transit chain-consistency test on 1992-10-13 (±10 s tolerance).
- Pejabat Mufti Wilayah Persekutuan — *Jadual Waktu Solat Wilayah Persekutuan Kuala Lumpur dan Putrajaya bagi Tahun 2025* (Sumber: Almanak Falak Syarie JAKIM), 16 January row (06:03 06:13 07:24 13:26 16:48 19:23 20:37). Zone `WLY01`, local MYT (UTC+8), retrieved 2026-10-24. URL: `https://muftiwp.gov.my/images/falak/takwim/jadual-waktu-solat/KL-dan-Putrajaya/JADUAL-WAKTU-SOLAT-WPKLPTJ-2025.pdf`
- Jabatan Kemajuan Islam Malaysia (JAKIM) e-solat XML feed — Kota Kinabalu/Ranau/Kota Belud/Tuaran/Penampang/Papar/Putatan zone `SBH07`, 16 January 2025 (local MYT UTC+8), retrieved 2026-10-24. Archived snapshot: `https://web.archive.org/web/20250116103115/https://www.e-solat.gov.my/index.php?r=esolatApi/xmlfeed&zon=SBH07`

## License

This project is licensed under the MIT License — see [LICENSE](https://github.com/nexusnv/al-falak/blob/main/LICENSE) for details.
