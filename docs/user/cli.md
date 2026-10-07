---
title: CLI Usage
description: Use the al-falak command-line interface for prayer times, Qibla, Sunnah markers, Hijri dates, moon sighting, and ephemeris values.
---

# CLI Usage

Al-Falak includes a command-line interface for quick terminal output.
It has six explicit subcommands:

```
al-falak <subcommand> [options] [--json]
  prayer         Print prayer times.
  qibla          Print Qibla direction.
  sunnah         Print Sunnah night markers.
  hijri          Convert a Gregorian date to a Hijri date (and back).
  moon-sighting  Print crescent visibility scores.
  astro          Print lunar position and Delta-T.
```

Every subcommand accepts `--json` to emit the same keys as one compact
JSON object (in the same key order) instead of `key=value` lines.
Datetimes print as ISO-8601 with offset (UTC by default, or `--timezone`
where supported). Floats print with full precision in text (`nan`
lowercase) and as `null` in JSON; booleans print lowercase in text and
as JSON booleans.

## Bare invocation was removed

Running `al-falak` without a subcommand exits with code 2. The fix is
one word — insert `prayer`:

```bash
# Before (no longer works)
python -m alfalak --latitude 35.7750 --longitude -78.6336

# After
python -m alfalak prayer --latitude 35.7750 --longitude -78.6336
```

```
al-falak: error: a subcommand is required (did you mean 'prayer'? try: al-falak prayer --latitude 35.7750 --longitude -78.6336)
```

Pasting an old command with flags fails differently — argparse treats
the first flag value as the subcommand and exits with code 2:

```
usage: al-falak [-h] <subcommand> ...
al-falak: error: argument <subcommand>: invalid choice: '35' (choose from prayer, qibla, sunnah, hijri, moon-sighting, astro)
```

Exit codes follow the argparse convention: `0` on success, `2` on
anything user-fixable (bad flags, out-of-range coordinates/angles,
unknown timezones, polar day/night, moon-sighting evenings with no
sunset). Warnings never fail: an out-of-range `astro delta-t` year
prints a `UserWarning` to stderr but still prints the value with exit 0.

## prayer

```bash
python -m alfalak prayer --latitude 35.7750 --longitude -78.6336 --date 2015-07-12 --method NORTH_AMERICA
```

Output (one `name=ISO-8601` line per marker, in chronological order):

```
imsak=2015-07-12T08:32:00+00:00
fajr=2015-07-12T08:42:00+00:00
sunrise=2015-07-12T10:08:00+00:00
syuruk=2015-07-12T10:08:00+00:00
ishraq=2015-07-12T10:23:00+00:00
dhuha=2015-07-12T10:36:00+00:00
dhuhr=2015-07-12T17:21:00+00:00
asr=2015-07-12T21:09:00+00:00
maghrib=2015-07-13T00:32:00+00:00
isha=2015-07-13T01:57:00+00:00
```

`syuruk` is sunrise under its MY/SG name, so it always equals `sunrise`.
`imsak` defaults to Fajr − 10 minutes; `ishraq`/`dhuha` default to
sunrise + 15/+ 28 minutes (see [Calculation Methods](calculation-methods/)).

> Script consumers note: output used to be 6 lines (`fajr` through `isha`).
> It is now 10 lines with the added `imsak`/`syuruk`/`ishraq`/`dhuha`
> markers. Parse by `name=` key, not by line position.

### Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--latitude` / `--lat` | Yes | — | Latitude (-90 to 90) |
| `--longitude` / `--lon` | Yes | — | Longitude (-180 to 180) |
| `--date` | No | Today (UTC) | Calendar date as YYYY-MM-DD |
| `--method` | No | MUSLIM_WORLD_LEAGUE | Calculation method (see below) |
| `--madhab` | No | SHAFI | `SHAFI` or `HANAFI` |
| `--high-latitude-rule` | No | MIDDLE_OF_THE_NIGHT | `MIDDLE_OF_THE_NIGHT`, `SEVENTH_OF_THE_NIGHT`, or `TWILIGHT_ANGLE` |
| `--polar-rule` | No | NEAREST_LATITUDE | `NONE`, `NEAREST_LATITUDE`, `NEAREST_DAY`, or `MAKKAH` |
| `--fajr-angle` | No | From method | Override the method's Fajr angle |
| `--isha-angle` | No | From method | Override the method's Isha angle |
| `--isha-interval` | No | From method | Override the method's Isha interval (minutes) |
| `--imsak-offset` | No | `10` | Minutes before Fajr for Imsak |
| `--ishraq-offset` | No | `15` | Minutes after sunrise for Ishraq |
| `--dhuha-offset` | No | `28` | Minutes after sunrise for start of Dhuha window |
| `--elevation` | No | `0.0` | Observer eye height in metres (dip correction) |
| `--ramadan` | No | Off | Umm al-Qura Ramadan mode (120 min Isha total; preset only) |
| `--timezone` | No | UTC | IANA timezone name for display (e.g. `Asia/Kuala_Lumpur`) |
| `--adjust NAME=MIN` | No | — | Repeatable per-prayer minute offset; `NAME` in `imsak,fajr,sunrise,dhuhr,asr,maghrib,isha,ishraq,dhuha` (no `syuruk` slot by design — sunrise flows through). Negatives need the `=` form: `--adjust isha=-1` |
| `--json` | No | Off | Emit one compact JSON object instead of `key=value` lines |

Explicit `--fajr-angle`/`--isha-angle`/`--isha-interval` override the
`--method` preset exactly like `CalculationParameters(method=...)` then
attribute assignment.

### Available methods

```
MUSLIM_WORLD_LEAGUE
NORTH_AMERICA
EGYPTIAN
KARACHI
UMM_AL_QURA
DUBAI
MOON_SIGHTING_COMMITTEE
KUWAIT
QATAR
SINGAPORE
UOIF
JAKIM
```

## qibla

```bash
python -m alfalak qibla --latitude 35.7750 --longitude -78.6336 --method ellipsoidal
```

```
direction=55.739247
distance_km=10961.846
method=ellipsoidal
```

Text prints the direction to 6 decimals and the distance to 3;
`--json` carries the raw floats. With `--declination`, a fourth
`magnetic=` line (compass heading) is added.

### Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--latitude` / `--lat` | Yes | — | Latitude (-90 to 90) |
| `--longitude` / `--lon` | Yes | — | Longitude (-180 to 180) |
| `--method` | No | `spherical` | Earth model: `spherical` or `ellipsoidal` (WGS84 geodesic) |
| `--declination` | No | — | Local magnetic declination in degrees, positive east (negative west); also prints `magnetic=` |
| `--json` | No | Off | Emit one compact JSON object instead of `key=value` lines |

See [Qibla Direction](qibla/) for the spherical/ellipsoidal error budget
and the declination sign convention.

## sunnah

```bash
python -m alfalak sunnah --latitude 35.7750 --longitude -78.6336 --date 2015-07-12 --method NORTH_AMERICA
```

```
middle_of_the_night=2015-07-13T04:38:00+00:00
first_third_of_the_night=2015-07-13T03:16:00+00:00
last_third_of_the_night=2015-07-13T05:59:00+00:00
tahajjud_start=2015-07-13T05:59:00+00:00
tahajjud_end=2015-07-13T08:43:00+00:00
```

With `--fraction F` (in the open interval 0–1), the block collapses to a
single line:

```bash
python -m alfalak sunnah --latitude 35.7750 --longitude -78.6336 --date 2015-07-12 --method NORTH_AMERICA --fraction 0.5
```

```
night_fraction=2015-07-13T04:38:00+00:00
```

### Options

`sunnah` accepts all `prayer` location and parameter flags
(`--latitude`/`--longitude`, `--date`, `--method`, `--madhab`,
`--high-latitude-rule`, `--polar-rule`, `--fajr-angle`, `--isha-angle`,
`--isha-interval`, `--imsak-offset`, `--ishraq-offset`, `--dhuha-offset`,
`--elevation`, `--ramadan`, `--timezone`, `--adjust`), plus:

| Option | Required | Default | Description |
|---|---|---|---|
| `--fraction` | No | — | Night fraction in (0, 1); prints a single `night_fraction=` line |
| `--start` | No | Maghrib | Custom night-start anchor as an ISO datetime with timezone offset (used with `--fraction`) |
| `--end` | No | Next-day Fajr | Custom night-end anchor as an ISO datetime with timezone offset (used with `--fraction`) |
| `--json` | No | Off | Emit one compact JSON object instead of `key=value` lines |

`--start`/`--end` must be timezone-aware (`2025-03-01T19:00:00+08:00`);
naive values exit with code 2. See [Sunnah Times](sunnah-times/) for the
Maghrib-to-next-day-Fajr night definition and anchor alternatives.

## hijri

Forward conversion (unchanged):

```bash
python -m alfalak hijri --date 2025-03-01 --calendar tabular
```

```
hijri=1446-09-01
calendar=tabular
```

Reverse conversion (Hijri → Gregorian):

```bash
python -m alfalak hijri --reverse 1446-09-01 --calendar tabular
```

```
gregorian=2025-03-01
calendar=tabular
```

Month length:

```bash
python -m alfalak hijri --month-length 1446-09 --calendar tabular
```

```
days=30
calendar=tabular
```

### Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--date` | No | Today (UTC) | Gregorian date as YYYY-MM-DD (forward mode) |
| `--calendar` | Yes | — | Hijri calendar rule: `tabular`, `uqu`, or `mabims` |
| `--country` | With `mabims` only | — | MABIMS country: `MY`, `ID`, `BN`, `SG` (case-insensitive; required with `--calendar mabims`, rejected otherwise) |
| `--adjustment-days` | No | `0` | Tabular day shift in [-2, 2] (only with `--calendar tabular`) |
| `--sunset-transition` | No | Off | Roll the Hijri day over at Maghrib (requires `--lat`, `--lon`, `--time`) |
| `--lat` / `--lon` | With `--sunset-transition` | — | Observer coordinates for sunset rollover (rejected without it) |
| `--time` | With `--sunset-transition` | — | Wall-clock time as HH:MM[:SS] on `--date`; naive, treated as UTC (rejected without it) |
| `--offsets` | No | — | JSON offset file (`{"YYYY-MM": shift}`) applied last (forward mode only) |
| `--reverse` | No | — | Hijri date as YYYY-MM-DD; convert back to a Gregorian date (mutually exclusive with `--date`/`--sunset-transition`/`--offsets`) |
| `--month-length` | No | — | Hijri year-month as YYYY-MM; print the month length (`29` or `30`; mutually exclusive with `--date`/`--sunset-transition`/`--offsets`) |
| `--json` | No | Off | Emit one compact JSON object instead of `key=value` lines |

Per-country conversion prints a suffixed label:

```bash
python -m alfalak hijri --date 2025-03-02 --calendar mabims --country MY
```

```
hijri=1446-09-01
calendar=mabims-MY
```

Sunset rollover switches the Hijri day at Maghrib (default prayer
parameters); `--offsets` applies official-correction shifts after the
rule. `--date`/`--time` are naive wall-clock values treated as UTC —
a local wall-clock time misplaces sunset rollover by the UTC offset.

> The `uqu` calendar (1423H month-start rule at Makkah) is not the
> `UMM_AL_QURA` prayer preset. `tabular` is arithmetic and routinely
> differs from observed months by 1–2 days — never present it as an
> observed date. See [Hijri Converter](hijri-converter/).

## moon-sighting

```bash
python -m alfalak moon-sighting --latitude 3.1390 --longitude 101.6869 --date 2025-02-28
```

```
arcl_deg=6.173972051753964
arcv_geo_deg=6.088018222865059
arcv_topo_deg=5.086970505414731
sun_alt_deg=-0.8325033650264293
moon_alt_topo_deg=4.254467140388302
daz_deg=1.0278791375318406
width_arcmin=0.09531389154651401
illumination=0.002900038687049744
lag_hours=0.4120943493906335
moon_age_days=0.4166666666666667
moon_age_at_moonset_days=0.4338372645579431
used_delta_t_s=74.56305038786272
sunset_jd_utc=2460734.977337402
yallop_q=-0.5153011137332268
odeh_v=-1.4820588547825952
yallop_zone=F
odeh_class=D
neo_mabims=false
mabims_1992=true
```

Geometry first (elongation, arcs of vision, altitudes, width,
illumination, lag, moon ages, delta-T used, sunset instant), then the
three scores: Yallop zone (`F` here — not visible), Odeh class (`D`),
and the two MABIMS booleans. In JSON, non-finite floats (e.g. `NaN`
lag when no moonset occurs) become `null`.

### Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--latitude` / `--lat` | Yes | — | Latitude (-90 to 90) |
| `--longitude` / `--lon` | Yes | — | Longitude (-180 to 180) |
| `--date` | Yes | — | Crescent evening as YYYY-MM-DD (no default — an explicit evening is required) |
| `--delta-t-override` | No | Built-in polynomial | Delta-T override in seconds for the TT conversion |
| `--json` | No | Off | Emit one compact JSON object instead of `key=value` lines |

Evenings with no sunset (polar day/night) exit with code 2. See
[Moon Sighting](moon-sighting/) for how to read the scores — check
`lag_hours` first, then the criteria, and only trust the 1992 age
branch after conjunction.

## astro

Two low-level lookups behind one nested subcommand:

```bash
python -m alfalak astro delta-t --year 2025.5
```

```
delta_t=74.76958225
```

```bash
python -m alfalak astro lunar-position --julian-day 2460000.5
```

```
longitude=38.63857432412311
latitude=0.24775270051666204
distance_km=381923.9281840365
right_ascension=36.175451124156034
declination=14.615404753403455
```

### Options

| Subcommand | Option | Required | Default | Description |
|---|---|---|---|---|
| `lunar-position` | `--julian-day` | Yes | — | Julian Day in Terrestrial Time (e.g. `2460000.5`) |
| `lunar-position` | `--json` | No | Off | Emit one compact JSON object instead of `key=value` lines |
| `delta-t` | `--year` | Yes | — | Decimal year (e.g. `2025.5`) |
| `delta-t` | `--override` | No | — | Delta-T override in seconds (e.g. an IERS observed value) |
| `delta-t` | `--json` | No | Off | Emit one compact JSON object instead of `key=value` lines |

Years outside 2005–2050 emit a `UserWarning` to stderr and
extrapolate — the value still prints with exit 0. See
[API Reference](api-reference/) for `LunarCoordinates` and `delta_t`.

## Error handling

All subcommands exit with code 2 for invalid input:

```bash
$ python -m alfalak prayer --latitude 35 --longitude -78 --method BOGUS
al-falak prayer: error: argument --method: invalid choice: 'BOGUS' (choose from ...)
```

Unknown methods, bad dates/times, `--latitude`/`--longitude` (use
`--lat`/`--lon` with `hijri --sunset-transition`), gate misuse (missing
`--country` with `mabims`, `--country` without it, `--adjustment-days`
outside `tabular`, `--time`/`--lat`/`--lon` without
`--sunset-transition`, unreadable `--offsets` files, out-of-range
coordinates, pre-floor dates, naive `--start`/`--end` anchors), and
polar day/night all exit with code 2 via an argparse error.

## See also

- [Getting Started](getting-started/) — Python API usage
- [Calculation Methods](calculation-methods/) — method details
- [Qibla Direction](qibla/) — Qibla models and accuracy budget
- [Sunnah Times](sunnah-times/) — night divisions and anchors
- [Hijri Converter](hijri-converter/) — Gregorian↔Hijri conversion rules
- [Moon Sighting](moon-sighting/) — crescent geometry and visibility criteria
- [API Reference](api-reference/) — full API documentation
