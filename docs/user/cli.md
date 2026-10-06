---
title: CLI Usage
description: Use the al-falak command-line interface for quick prayer time output.
---

# CLI Usage

Al-Falak includes a command-line interface for quick terminal output.

## Basic usage

```bash
python -m alfalak --latitude 35.7750 --longitude -78.6336
```

Output (one `name=ISO-8601` line per marker, in chronological order):

```
imsak=2026-09-29T09:48:00+00:00
fajr=2026-09-29T09:58:00+00:00
sunrise=2026-09-29T11:08:00+00:00
syuruk=2026-09-29T11:08:00+00:00
ishraq=2026-09-29T11:23:00+00:00
dhuha=2026-09-29T11:36:00+00:00
dhuhr=2026-09-29T17:06:00+00:00
asr=2026-09-29T20:26:00+00:00
maghrib=2026-09-29T23:01:00+00:00
isha=2026-09-30T00:11:00+00:00
```

`syuruk` is sunrise under its MY/SG name, so it always equals `sunrise`.
`imsak` defaults to Fajr − 10 minutes; `ishraq`/`dhuha` default to
sunrise + 15/+ 28 minutes (see [Calculation Methods](/calculation-methods/)).

> Script consumers note: output used to be 6 lines (`fajr` through `isha`).
> It is now 10 lines with the added `imsak`/`syuruk`/`ishraq`/`dhuha`
> markers. Parse by `name=` key, not by line position.

## With date and method

```bash
python -m alfalak \
  --latitude 35.7750 \
  --longitude -78.6336 \
  --date 2015-07-12 \
  --method NORTH_AMERICA
```

## Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--latitude` | Yes | — | Latitude (-90 to 90) |
| `--longitude` | Yes | — | Longitude (-180 to 180) |
| `--date` | No | Today | Date as YYYY-MM-DD |
| `--method` | No | MUSLIM_WORLD_LEAGUE | Calculation method |

## Available methods

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

## Hijri conversion

```bash
python -m alfalak hijri --date 2025-03-01 --calendar tabular
```

Output (exactly two lines):

```
hijri=1446-09-01
calendar=tabular
```

### Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--date` | No | Today (UTC) | Gregorian date as YYYY-MM-DD; also accepted before the subcommand (`--date X hijri ...`) |
| `--calendar` | Yes | — | Hijri calendar rule: `tabular`, `uqu`, or `mabims` |
| `--country` | With `mabims` only | — | MABIMS country: `MY`, `ID`, `BN`, `SG` (case-insensitive; required with `--calendar mabims`, rejected otherwise) |
| `--adjustment-days` | No | `0` | Tabular day shift in [-2, 2] (only with `--calendar tabular`) |
| `--sunset-transition` | No | Off | Roll the Hijri day over at Maghrib (requires `--lat`, `--lon`, `--time`) |
| `--lat` / `--lon` | With `--sunset-transition` | — | Observer coordinates for sunset rollover (rejected without it) |
| `--time` | With `--sunset-transition` | — | Wall-clock time as HH:MM[:SS] on `--date`; naive, treated as UTC (rejected without it) |
| `--offsets` | No | — | JSON offset file (`{"YYYY-MM": shift}`) applied last |

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
> observed date. See [Hijri Converter](/hijri-converter/).

## Error handling

The prayer-times command exits with code 2 for invalid input:

```bash
$ python -m alfalak --latitude 35 --longitude -78 --method BOGUS
usage: al-falak [-h] --latitude LATITUDE --longitude LONGITUDE [--date DATE]
             [--method {MUSLIM_WORLD_LEAGUE,NORTH_AMERICA,...}]
al-falak: error: argument --method: invalid choice: 'BOGUS'
```

The `hijri` subcommand follows the same convention: unknown calendars,
bad dates/times, `--latitude`/`--longitude` (use `--lat`/`--lon`
with `--sunset-transition`), and gate misuse (missing
`--country` with `mabims`, `--country` without it, `--adjustment-days`
outside `tabular`, `--time`/`--lat`/`--lon` without
`--sunset-transition`, unreadable `--offsets` files, out-of-range
coordinates, pre-floor dates) all exit with code 2 via an argparse error.

## See also

- [Getting Started](/getting-started/) — Python API usage
- [Calculation Methods](/calculation-methods/) — method details
- [Hijri Converter](/hijri-converter/) — Gregorian↔Hijri conversion rules
