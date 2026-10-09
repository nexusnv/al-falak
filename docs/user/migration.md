---
title: Migration
description: Migrate from adhanpy to al-falak.
---

# Migration

This guide covers migrating from the `adhanpy` package (`import adhanpy`,
[alphahm/adhanpy](https://github.com/alphahm/adhanpy)) to `al-falak`
(`import alfalak`, this library). The two are separate, independently released
libraries — not successive versions of the same package — but `al-falak`
originates from the same [`batoulapps/adhan`](https://github.com/batoulapps/adhan)
port lineage, so the public surface keeps the same class and method names and
the switch is typically frictionless: change the install, change the import,
and handle the deliberate differences listed below.

## Why a separate library

`Al-Falak` is maintained on its own so it can track currently supported Python
versions, keep development dependencies and tooling current, and let this
project's milestones evolve independently. In return you get a hardened,
fully typed codebase with explicit error handling (below) and ongoing
maintenance. Calculation math follows the same formulas, so prayer-time
values are comparable apart from the rounding fix noted in
[Changelog](changelog/).

## Package rename

```bash
# Old
pip install adhanpy

# New
pip install al-falak
```

## Import changes

```python
# Old
from adhanpy import PrayerTimes, CalculationMethod

# New
from alfalak import PrayerTimes, CalculationMethod
```

## Module structure

The internal module structure has changed:

```python
# Old
from adhanpy.calculation import CalculationMethod
from adhanpy.data import Coordinates

# New
from alfalak.calculation import CalculationMethod
from alfalak.data import Coordinates
```

All public names are also importable from the package root (`from alfalak import ...`).

## CLI: bare invocation now needs `prayer`

The command-line interface now uses explicit subcommands. A bare
`al-falak --latitude ...` call (previously the prayer-times default)
exits with code 2 — insert `prayer`:

```bash
# Old
python -m alfalak --latitude 35.7750 --longitude -78.6336

# New
python -m alfalak prayer --latitude 35.7750 --longitude -78.6336
```

Output keys and order are unchanged (the same 10 `name=` lines). The
`hijri` invocation is unchanged; five new subcommands (`qibla`,
`sunnah`, `moon-sighting`, `astro`, plus `prayer`) cover the rest of
the public API. Flags must come after the subcommand everywhere —
`--date X hijri ...` (previously tolerated) now exits with code 2.
See [CLI Usage](cli/) for the full command tree.

## Error handling

The error hierarchy was introduced in v1.0.0:

```python
# Old (adhanpy 1.x)
try:
    PrayerTimes(...)
except RuntimeError:
    ...

# New (al-falak 1.x)
from alfalak import AlFalakError, AstronomicalError

try:
    PrayerTimes(...)
except AstronomicalError:
    ...
```

Catch sites matching on the old behavior need updating: polar day/night and
undefined Asr raise `AstronomicalError`, bad method/madhab/polar-rule setup
raises `ConfigurationError`, and out-of-range coordinates/angles/intervals —
including non-numeric coordinates — raise `ValidationError`. See
[Errors](errors/) for the full tree.

## Breaking changes in v1.0.0

| Change | Old behavior | New behavior |
|---|---|---|
| Error types | `RuntimeError`, `ValueError`, `TypeError` | `AlFalakError` subclasses |
| Package name | `adhanpy` | `al-falak` |
| Import name | `import adhanpy` | `import alfalak` |
| Python support | 3.9+ | 3.11+ |

## Unchanged

- Calculation math (same formulas, same results; see the rounding fix in [Changelog](changelog/))
- Public API surface (same class and method names)
- CLI output format (same `key=value` keys, same order; the bare
  invocation now needs the `prayer` subcommand — see above)

## See also

- [Changelog](changelog/) — full version history
- [API Reference](api-reference/) — current API
