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

## License

This project is licensed under the MIT License — see [LICENSE](https://github.com/nexusnv/al-falak/blob/main/LICENSE) for details.
