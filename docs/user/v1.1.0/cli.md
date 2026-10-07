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

## Error handling

The CLI exits with code 2 for invalid input:

```bash
$ python -m alfalak --latitude 35 --longitude -78 --method BOGUS
usage: al-falak [-h] --latitude LATITUDE --longitude LONGITUDE [--date DATE]
             [--method {MUSLIM_WORLD_LEAGUE,NORTH_AMERICA,...}]
al-falak: error: argument --method: invalid choice: 'BOGUS'
```

## See also

- [Getting Started](/getting-started/) — Python API usage
- [Calculation Methods](/calculation-methods/) — method details
