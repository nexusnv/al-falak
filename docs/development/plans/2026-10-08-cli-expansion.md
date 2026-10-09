# CLI Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Widen the `al-falak` CLI to six explicit subcommands covering almost all of `alfalak.__all__`, for the Debian/apt release.

**Architecture:** Split `src/alfalak/__main__.py` (226 lines) into a thin dispatcher plus a stdlib-only `src/alfalak/cli/` package with one module per subcommand sharing `common.py` (coordinate/date/timezone/`--adjust` parsing, `CalculationParameters`/`PrayerTimes` builders, `key=value`/`--json` emitters). Bare invocation becomes an exit-2 error pointing at `prayer`; `hijri` keeps its flags and gains `--reverse`/`--month-length`.

**Tech Stack:** Python 3.11+, stdlib only (`argparse`, `json`, `zoneinfo`, `re`, `math`), no new runtime dependencies; gates: `black --check src/`, `ruff check src/ tests/`, `mypy src`, `pytest --cov-fail-under=95`.

**References:** Spec `docs/development/specs/2026-10-08-cli-expansion-design.md`; current CLI `src/alfalak/__main__.py:1-226`; goldens verified against the live API (see values inline below).

**Branch:** `feature/cli-expansion` from `main`.

---

## File Structure

- Create: `src/alfalak/cli/__init__.py` — re-exports `register_all`.
- Create: `src/alfalak/cli/common.py` — shared parsing/builders/emitters.
- Create: `src/alfalak/cli/prayer.py`, `qibla.py`, `sunnah.py`, `hijri.py`, `moon_sighting.py`, `astro.py` — one `register(subparsers)` + one `run(args, parser)` each.
- Modify: `src/alfalak/__main__.py` — thin dispatcher only (no per-command logic).
- Modify: `tests/test_cli.py` — bare-invocation calls gain the `prayer` subcommand; top-level-date test replaced with a rejection test.
- Create: `tests/test_cli_prayer.py`, `test_cli_qibla.py`, `test_cli_sunnah.py`, `test_cli_hijri.py`, `test_cli_moon.py`, `test_cli_astro.py`.
- Modify: `docs/user/cli.md` — full rewrite (Task 7).
- Modify: `docs/user/migration.md`, `docs/user/api-reference.md`, `docs/user/moon-sighting.md`, `docs/user/qibla.md`, `docs/user/sunnah-times.md` — one-line cross-pointers each.
- Modify: `CHANGES.md` — Unreleased entry.
- Create: `debian/al-falak.1`, `debian/completions/al-falak.bash`, `debian/completions/al-falak.zsh`.

No Python API changes. No new dependencies.

---

### Task 1: Package skeleton, shared helpers, `prayer` subcommand, dispatcher

**Files:**
- Create: `src/alfalak/cli/__init__.py`
- Create: `src/alfalak/cli/common.py`
- Create: `src/alfalak/cli/prayer.py`
- Create: `src/alfalak/cli/hijri.py` (moved verbatim from `__main__.py:114-183`, same behavior; only the registration changes)
- Modify: `src/alfalak/__main__.py:1-226` (rewrite as dispatcher)
- Modify: `tests/test_cli.py` (bare calls gain `"prayer"`; top-level-date test replaced)
- Test: `tests/test_cli_prayer.py` (new)

**Design decisions (locked):**
1. `--adjust` is repeatable `NAME=MIN`, `NAME` in `imsak,fajr,sunrise,dhuhr,asr,maghrib,isha,ishraq,dhuha` (no `syuruk` slot by design). Negatives must use `=` form: `--adjust isha=-1`.
2. Override rule: build `CalculationParameters(method=...)` first (method template wins), then `setattr` ONLY user-passed values. Angle/interval flags default to `None` (a `0` default would clobber e.g. UMM_AL_QURA's `isha_interval=90`). `madhab`/`high-latitude-rule`/`polar-rule`/offsets/`elevation` defaults equal the library defaults, so always-set is equivalent.
3. `--json` is added to every subcommand via `common.add_json_arg`; emitters live in `common`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli_prayer.py
from alfalak.__main__ import main


def test_prayer_subcommand_byte_identical(capsys):
    main(
        [
            "prayer",
            "--latitude", "35.7750",
            "--longitude", "-78.6336",
            "--date", "2015-07-12",
            "--method", "NORTH_AMERICA",
        ]
    )
    assert capsys.readouterr().out == (
        "imsak=2015-07-12T08:32:00+00:00\n"
        "fajr=2015-07-12T08:42:00+00:00\n"
        "sunrise=2015-07-12T10:08:00+00:00\n"
        "syuruk=2015-07-12T10:08:00+00:00\n"
        "ishraq=2015-07-12T10:23:00+00:00\n"
        "dhuha=2015-07-12T10:36:00+00:00\n"
        "dhuhr=2015-07-12T17:21:00+00:00\n"
        "asr=2015-07-12T21:09:00+00:00\n"
        "maghrib=2015-07-13T00:32:00+00:00\n"
        "isha=2015-07-13T01:57:00+00:00\n"
    )


def test_prayer_full_parity_adjust_madhab_timezone(capsys):
    main(
        [
            "prayer",
            "--latitude", "3.1390",
            "--longitude", "101.6869",
            "--date", "2025-03-01",
            "--method", "SINGAPORE",
            "--madhab", "HANAFI",
            "--adjust", "fajr=2",
            "--adjust", "isha=-1",
            "--timezone", "Asia/Kuala_Lumpur",
        ]
    )
    out = capsys.readouterr().out
    assert "fajr=2025-03-01T06:28:00+08:00\n" in out
    assert "isha=" in out and out.endswith("+08:00\n")


def test_prayer_json_keys_match_text(capsys):
    import json

    main(
        [
            "prayer",
            "--latitude", "35.7750",
            "--longitude", "-78.6336",
            "--date", "2015-07-12",
            "--method", "NORTH_AMERICA",
            "--json",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    assert list(data) == [
        "imsak", "fajr", "sunrise", "syuruk", "ishraq",
        "dhuha", "dhuhr", "asr", "maghrib", "isha",
    ]
    assert data["fajr"] == "2015-07-12T08:42:00+00:00"


def test_bare_invocation_points_at_prayer(capsys):
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        main(["--latitude", "35", "--longitude", "-78"])
    assert excinfo.value.code == 2
```

(The `--adjust`/`--timezone` golden above is illustrative of shape; the worker MUST run it and pin the true values before committing — the byte-identical NORTH_AMERICA vector is pre-verified against the live API.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_prayer.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'alfalak.cli'` (use `--no-cov` for speed; full coverage gate runs in Task 9).

- [ ] **Step 3: Write `common.py` (complete)**

```python
"""Shared parsing, builders, and emitters for the al-falak CLI."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from alfalak import CalculationMethod, PrayerTimes
from alfalak.calculation.CalculationParameters import CalculationParameters
from alfalak.calculation.HighLatitudeRule import HighLatitudeRule
from alfalak.calculation.Madhab import Madhab
from alfalak.calculation.PolarCircleRule import PolarCircleRule
from alfalak.calculation.PrayerAdjustments import PrayerAdjustments
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AlFalakError

_ADJUST_RE = re.compile(
    r"^(imsak|fajr|sunrise|dhuhr|asr|maghrib|isha|ishraq|dhuha)=(-?\d+)$"
)
_PRAYER_KEYS = (
    "imsak", "fajr", "sunrise", "syuruk", "ishraq",
    "dhuha", "dhuhr", "asr", "maghrib", "isha",
)


def add_coord_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--latitude", "--lat", type=float, required=True)
    parser.add_argument("--longitude", "--lon", type=float, required=True)


def add_date_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--date", default=None,
        help="Calendar date as YYYY-MM-DD (defaults to today, UTC).",
    )


def add_json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json", action="store_true",
        help="Emit one compact JSON object instead of key=value lines.",
    )


def add_prayer_args(parser: argparse.ArgumentParser) -> None:
    add_coord_args(parser)
    add_date_arg(parser)
    parser.add_argument(
        "--method", default=CalculationMethod.MUSLIM_WORLD_LEAGUE.name,
        choices=sorted(m.name for m in CalculationMethod),
    )
    parser.add_argument("--madhab", default="SHAFI", choices=["SHAFI", "HANAFI"])
    parser.add_argument(
        "--high-latitude-rule", default="MIDDLE_OF_THE_NIGHT",
        choices=[r.name for r in HighLatitudeRule],
    )
    parser.add_argument(
        "--polar-rule", default="NEAREST_LATITUDE",
        choices=[r.name for r in PolarCircleRule],
    )
    parser.add_argument("--fajr-angle", type=float, default=None)
    parser.add_argument("--isha-angle", type=float, default=None)
    parser.add_argument("--isha-interval", type=int, default=None)
    parser.add_argument("--imsak-offset", type=int, default=10)
    parser.add_argument("--ishraq-offset", type=int, default=15)
    parser.add_argument("--dhuha-offset", type=int, default=28)
    parser.add_argument("--elevation", type=float, default=0.0)
    parser.add_argument("--ramadan", action="store_true")
    parser.add_argument("--timezone", default=None)
    parser.add_argument("--adjust", action="append", default=[],
                        metavar="NAME=MIN")


def parse_date(raw: str | None, parser: argparse.ArgumentParser) -> datetime:
    if raw is None:
        return datetime.now(timezone.utc)
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        parser.error(f"invalid --date (expected YYYY-MM-DD): {raw}")


def parse_adjustments(specs: list[str],
                      parser: argparse.ArgumentParser) -> PrayerAdjustments:
    adjustments = PrayerAdjustments()
    for spec in specs:
        match = _ADJUST_RE.match(spec)
        if match is None:
            parser.error(
                f"invalid --adjust (expected NAME=MINUTES): {spec} "
                "(NAME in imsak,fajr,sunrise,dhuhr,asr,"
                "maghrib,isha,ishraq,dhuha)"
            )
        setattr(adjustments, match.group(1), int(match.group(2)))
    return adjustments


def parse_timezone(raw: str | None,
                   parser: argparse.ArgumentParser) -> ZoneInfo | None:
    if raw is None:
        return None
    try:
        return ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        parser.error(f"unknown --timezone: {raw}")


def build_prayer_times(args: argparse.Namespace,
                       parser: argparse.ArgumentParser) -> PrayerTimes:
    params = CalculationParameters(method=CalculationMethod[args.method])
    params.madhab = Madhab[args.madhab]
    params.high_latitude_rule = HighLatitudeRule[args.high_latitude_rule]
    params.polar_circle_rule = PolarCircleRule[args.polar_rule]
    if args.fajr_angle is not None:
        params.fajr_angle = args.fajr_angle
    if args.isha_angle is not None:
        params.isha_angle = args.isha_angle
    if args.isha_interval is not None:
        params.isha_interval = args.isha_interval
    params.imsak_offset = args.imsak_offset
    params.ishraq_offset = args.ishraq_offset
    params.dhuha_offset = args.dhuha_offset
    params.elevation_m = args.elevation
    params.is_ramadan = args.ramadan
    params.adjustments = parse_adjustments(args.adjust, parser)
    try:
        return PrayerTimes(
            Coordinates(args.latitude, args.longitude),
            parse_date(args.date, parser),
            calculation_parameters=params,
            time_zone=parse_timezone(args.timezone, parser),
        )
    except AlFalakError as exc:
        parser.error(str(exc))


def emit(mapping: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(mapping))
    else:
        for key, value in mapping.items():
            print(f"{key}={value}")
```

- [ ] **Step 4: Write `prayer.py`, `__init__.py`, and the dispatcher**

```python
# src/alfalak/cli/prayer.py
import argparse
from alfalak.cli.common import (
    _PRAYER_KEYS, add_json_arg, add_prayer_args, build_prayer_times, emit,
)
from alfalak.exceptions import AlFalakError


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("prayer", help="Print prayer times.")
    add_prayer_args(parser)
    add_json_arg(parser)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        prayer_times = build_prayer_times(args, parser)
        emit(
            {key: getattr(prayer_times, key).isoformat()
             for key in _PRAYER_KEYS},
            args.json,
        )
    except AlFalakError as exc:
        parser.error(str(exc))
```

```python
# src/alfalak/cli/__init__.py
"""Subcommand registrars for the al-falak CLI (stdlib only)."""

from alfalak.cli import astro, hijri, moon_sighting, prayer, qibla, sunnah

__all__ = ["register_all"]


def register_all(subparsers: object) -> None:
    prayer.register(subparsers)  # type: ignore[arg-type]
    qibla.register(subparsers)  # type: ignore[arg-type]
    sunnah.register(subparsers)  # type: ignore[arg-type]
    hijri.register(subparsers)  # type: ignore[arg-type]
    moon_sighting.register(subparsers)  # type: ignore[arg-type]
    astro.register(subparsers)  # type: ignore[arg-type]
```

`__main__.py` becomes: `build_parser()` with NO top-level `--latitude/--date/--method` (only `hijri.py` keeps its own `--lat/--lon`), `subparsers = parser.add_subparsers(dest="command", metavar="<subcommand>")`, `register_all(subparsers)`; in `main()`, `if args.command is None: parser.error("a subcommand is required (did you mean 'prayer'? try: al-falak prayer --latitude 35.7750 --longitude -78.6336)")`, else `args.func(args, parser)`. `hijri.py` is the current `_run_hijri`/`_parse_hijri_time` moved verbatim, with its own `--date` (plain `default=None`, no SUPPRESS trick — the shared top-level `--date` is gone) registered as `hijri`.

In `tests/test_cli.py`: prefix `"prayer",` to the bare-invocation arg lists in `test_cli_prints_iso_times`, `test_cli_defaults_to_today`, `test_cli_bare_prayer_byte_identical`, `test_cli_module_entry_point` (subprocess argv), `test_cli_main_guard` (argv); replace `test_cli_hijri_top_level_date_before_subcommand` with:

```python
def test_cli_top_level_date_now_rejected():
    with pytest.raises(SystemExit) as excinfo:
        main(["--date", "2025-03-01", "hijri", "--calendar", "tabular"])
    assert excinfo.value.code == 2
```

- [ ] **Step 5: Run and commit**

Run: `pytest tests/test_cli.py tests/test_cli_prayer.py --no-cov -q`
Expected: PASS.
Run: `black --check src/ && ruff check src/ tests/ && mypy src`
Expected: clean.
Commit: `git add src/alfalak/cli tests/test_cli.py tests/test_cli_prayer.py && git commit -m "feat(cli): explicit subcommands with prayer and shared helpers"`

---

### Task 2: `qibla` subcommand

**Files:**
- Create: `src/alfalak/cli/qibla.py`
- Test: `tests/test_cli_qibla.py`

Goldens verified against the live API: Raleigh `(35.7750, -78.6336)` spherical `direction=55.825083 distance_km=10943.598`; ellipsoidal `55.739247/10961.846`; `--declination -8.0` adds `magnetic=63.825083`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_qibla.py
import json
from alfalak.__main__ import main


def test_qibla_spherical_two_lines(capsys):
    main(["qibla", "--latitude", "35.7750", "--longitude", "-78.6336"])
    assert capsys.readouterr().out == (
        "direction=55.825083\n"
        "distance_km=10943.598\n"
        "method=spherical\n"
    )


def test_qibla_ellipsoidal_and_magnetic(capsys):
    main([
        "qibla", "--latitude", "35.7750", "--longitude", "-78.6336",
        "--method", "ellipsoidal", "--declination", "-8.0",
    ])
    out = capsys.readouterr().out
    assert "direction=55.739247\n" in out
    assert "distance_km=10961.846\n" in out
    assert "magnetic=63.739247\n" in out


def test_qibla_json(capsys):
    main(["qibla", "--latitude", "35.7750",
          "--longitude", "-78.6336", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["method"] == "spherical"
    assert abs(data["direction"] - 55.82508273783204) < 1e-9


def test_qibla_bad_method_rejected():
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        main(["qibla", "--latitude", "35", "--longitude", "-78",
              "--method", "BOGUS"])
    assert excinfo.value.code == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_qibla.py --no-cov -q`
Expected: FAIL (`qibla` subcommand missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/alfalak/cli/qibla.py
import argparse
from alfalak import Qibla
from alfalak.cli.common import (
    add_coord_args, add_date_arg_unused, add_json_arg, emit,
)
```

(Full body: `--method spherical|ellipsoidal` default `spherical`; `--declination float` default `None`; text floats `f"{direction:.6f}"` / `f"{distance:.3f}"`, JSON raw floats; `magnetic=` line only when declination given; `Qibla`/`magnetic_direction` errors → `parser.error`. Note: do NOT import a nonexistent `add_date_arg_unused` — qibla takes no `--date`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_qibla.py tests/test_cli.py --no-cov -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/alfalak/cli/qibla.py tests/test_cli_qibla.py
git commit -m "feat(cli): add qibla subcommand"
```

---

### Task 3: `sunnah` subcommand

**Files:**
- Create: `src/alfalak/cli/sunnah.py`
- Test: `tests/test_cli_sunnah.py`

Goldens verified against the live API (Raleigh `2015-07-12 NORTH_AMERICA`): `middle_of_the_night=2015-07-13T04:38:00+00:00`, `first_third_of_the_night=2015-07-13T03:16:00+00:00`, `last_third_of_the_night=2015-07-13T05:59:00+00:00`, `tahajjud_start=2015-07-13T05:59:00+00:00`, `tahajjud_end=2015-07-13T08:43:00+00:00`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_sunnah.py
from alfalak.__main__ import main


def test_sunnah_block(capsys):
    main([
        "sunnah", "--latitude", "35.7750", "--longitude", "-78.6336",
        "--date", "2015-07-12", "--method", "NORTH_AMERICA",
    ])
    assert capsys.readouterr().out == (
        "middle_of_the_night=2015-07-13T04:38:00+00:00\n"
        "first_third_of_the_night=2015-07-13T03:16:00+00:00\n"
        "last_third_of_the_night=2015-07-13T05:59:00+00:00\n"
        "tahajjud_start=2015-07-13T05:59:00+00:00\n"
        "tahajjud_end=2015-07-13T08:43:00+00:00\n"
    )


def test_sunnah_fraction_half_equals_middle(capsys):
    main([
        "sunnah", "--latitude", "35.7750", "--longitude", "-78.6336",
        "--date", "2015-07-12", "--method", "NORTH_AMERICA",
        "--fraction", "0.5",
    ])
    assert capsys.readouterr().out == (
        "night_fraction=2015-07-13T04:38:00+00:00\n"
    )


def test_sunnah_naive_anchor_rejected():
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        main([
            "sunnah", "--latitude", "35.7750", "--longitude", "-78.6336",
            "--date", "2015-07-12", "--start", "2015-07-13T00:00:00",
        ])
    assert excinfo.value.code == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_sunnah.py --no-cov -q`
Expected: FAIL (`sunnah` subcommand missing).

- [ ] **Step 3: Write minimal implementation**

`sunnah.py`: all `add_prayer_args` flags (builds `PrayerTimes` via `common.build_prayer_times`) + `--fraction float` (default `None`) + `--start/--end` ISO datetimes parsed with `datetime.fromisoformat` (must carry `tzinfo`, else `parser.error`; `ValueError` → `parser.error`). Default block prints the five keys above from `SunnahTimes`; with `--fraction`, prints single `night_fraction=` via `sunnah.night_fraction(fraction, start=..., end=...)`. `AlFalakError` → `parser.error`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_sunnah.py tests/test_cli.py --no-cov -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/alfalak/cli/sunnah.py tests/test_cli_sunnah.py
git commit -m "feat(cli): add sunnah subcommand"
```

---

### Task 4: `hijri --reverse` and `--month-length`

**Files:**
- Modify: `src/alfalak/cli/hijri.py`
- Test: `tests/test_cli_hijri.py` (new)

Verified: `TabularCalendar().to_gregorian(HijriDate(1446, 9, 1))` → `2025-03-01`; `month_length(1446, 9)` → `30`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_hijri.py
import pytest
from alfalak.__main__ import main


def test_hijri_reverse(capsys):
    main(["hijri", "--reverse", "1446-09-01", "--calendar", "tabular"])
    assert capsys.readouterr().out == (
        "gregorian=2025-03-01\ncalendar=tabular\n"
    )


def test_hijri_month_length(capsys):
    main(["hijri", "--month-length", "1446-09", "--calendar", "tabular"])
    assert capsys.readouterr().out == "days=30\ncalendar=tabular\n"


def test_hijri_reverse_rejects_forward_flags():
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--reverse", "1446-09-01", "--calendar", "tabular",
              "--date", "2025-03-01"])
    assert excinfo.value.code == 2


def test_hijri_reverse_bad_date_rejected():
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--reverse", "1446-13-01", "--calendar", "tabular"])
    assert excinfo.value.code == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_hijri.py --no-cov -q`
Expected: FAIL (`--reverse` unrecognized).

- [ ] **Step 3: Write minimal implementation**

Add `--reverse HIJRI-DATE` and `--month-length HIJRI-YYYY-MM` (both default `None`, mutually exclusive with each other and with `--date/--sunset-transition/--lat/--lon/--time/--offsets/--adjustment-days`; violations → `parser.error`). `--calendar` (+ `--country` for mabims) stays required in all modes. Parse `YYYY-MM-DD` via `HijriDate(int...)` (bad shapes/months → `parser.error`); `YYYY-MM` via regex `^(\d{4,})-(\d{2})$`. Run `cal.to_gregorian(h)` / `cal.month_length(y, m)` inside `try/except AlFalakError → parser.error`. Outputs per §3.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_hijri.py tests/test_cli.py --no-cov -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/alfalak/cli/hijri.py tests/test_cli_hijri.py
git commit -m "feat(cli): hijri reverse conversion and month length"
```

---

### Task 5: `moon-sighting` subcommand

**Files:**
- Create: `src/alfalak/cli/moon_sighting.py`
- Test: `tests/test_cli_moon.py`

Verified KL vector (`2025-02-28`, `3.1390/101.6869`): `arcl≈6.17397`, `yallop_zone=F`, `odeh_class=D`, `neo_mabims=false`, `mabims_1992=true`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_moon.py
import json
from alfalak.__main__ import main

MOON_ARGS = ["moon-sighting", "--latitude", "3.1390",
             "--longitude", "101.6869", "--date", "2025-02-28"]


def test_moon_sighting_scores(capsys):
    main(MOON_ARGS)
    out = capsys.readouterr().out
    assert "yallop_zone=F\n" in out
    assert "odeh_class=D\n" in out
    assert "neo_mabims=false\n" in out
    assert "mabims_1992=true\n" in out
    assert "arcl_deg=" in out and "lag_hours=" in out


def test_moon_sighting_json_nan_is_null(capsys):
    main(MOON_ARGS + ["--json"])
    data = json.loads(capsys.readouterr().out)
    assert set(data) == {
        "arcl_deg", "arcv_geo_deg", "arcv_topo_deg", "sun_alt_deg",
        "moon_alt_topo_deg", "daz_deg", "width_arcmin", "illumination",
        "lag_hours", "moon_age_days", "moon_age_at_moonset_days",
        "used_delta_t_s", "sunset_jd_utc",
        "yallop_q", "yallop_zone", "odeh_v", "odeh_class",
        "neo_mabims", "mabims_1992",
    }
    assert data["yallop_zone"] == "F"


def test_moon_sighting_polar_no_sunset():
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        main(["moon-sighting", "--latitude", "78.22",
              "--longitude", "15.63", "--date", "2025-06-21"])
    assert excinfo.value.code == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_moon.py --no-cov -q`
Expected: FAIL (`moon-sighting` subcommand missing).

- [ ] **Step 3: Write minimal implementation**

`moon_sighting.py`: `--latitude/--longitude` (required), `--date` (required — an explicit crescent evening, no silent today default), `--delta-t-override float` (default `None`), `--json`. Parse date to `datetime.date`; `crescent_geometry_at_sunset(day, Coordinates, override)`; scores via `yallop_q/zone`, `odeh_v/class`, `is_neo_mabims_2021(alt, arcl)`. For 1992: `try: is_mabims_1992(alt, arcl, age_ms*24) except ValidationError:` (NaN moonset age when no moonset that date) → fall back to the altitude/elongation branch `(alt >= 2.0 and arcl >= 3.0)`, per `moon-sighting.md`. Text floats via `repr` (`nan` lowercase); JSON maps non-finite floats to `None`. `AlFalakError` → `parser.error`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_moon.py --no-cov -q`
Expected: PASS (Longyearbyen 2025-06-21 has midnight sun → `AstronomicalError` → exit 2; if the date ever gains a sunset, pick a verified polar-no-sunset vector instead).

- [ ] **Step 5: Commit**

```bash
git add src/alfalak/cli/moon_sighting.py tests/test_cli_moon.py
git commit -m "feat(cli): add moon-sighting subcommand"
```

---

### Task 6: `astro` subcommand (`lunar-position`, `delta-t`)

**Files:**
- Create: `src/alfalak/cli/astro.py`
- Test: `tests/test_cli_astro.py`

Verified: `delta_t(2025.5)` → `74.76958225`; `LunarCoordinates(2460000.5)` → lon `38.63857432412311`, lat `0.24775270051666204`, dist `381923.9281840365`, RA `36.175451124156034`, dec `14.615404753403455`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_astro.py
import pytest
from alfalak.__main__ import main


def test_astro_delta_t(capsys):
    main(["astro", "delta-t", "--year", "2025.5"])
    assert capsys.readouterr().out == "delta_t=74.76958225\n"


def test_astro_lunar_position(capsys):
    main(["astro", "lunar-position", "--julian-day", "2460000.5"])
    out = capsys.readouterr().out
    assert "longitude=38.63857432412311\n" in out
    assert "distance_km=381923.9281840365\n" in out


def test_astro_lunar_bad_jd_rejected():
    with pytest.raises(SystemExit) as excinfo:
        main(["astro", "lunar-position", "--julian-day", "nan"])
    assert excinfo.value.code == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_astro.py --no-cov -q`
Expected: FAIL (`astro` subcommand missing).

- [ ] **Step 3: Write minimal implementation**

`astro.py`: nested subparsers — `lunar-position --julian-day JD (required float)` → `LunarCoordinates(jd)` fields via `repr`; `delta-t --year DEC-YEAR (required float) [--override SEC]` → `delta_t(year, override)` via `repr`. `--json` on both. `UserWarning` (out-of-range years) flows to stderr untouched; value still prints. `AlFalakError` → `parser.error`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_astro.py --no-cov -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/alfalak/cli/astro.py tests/test_cli_astro.py
git commit -m "feat(cli): add astro subcommand"
```

---

### Task 7: User docs and changelog

**Files:**
- Modify: `docs/user/cli.md` (rewrite around the six subcommands)
- Modify: `docs/user/migration.md` (bare → `prayer` note)
- Modify: `docs/user/api-reference.md`, `docs/user/moon-sighting.md`, `docs/user/qibla.md`, `docs/user/sunnah-times.md` (one CLI cross-pointer line each)
- Modify: `CHANGES.md` (Unreleased entry)

Frozen `docs/user/v1.x/` snapshots stay untouched. Links relative (no leading `/`).

- [ ] **Step 1: Rewrite `docs/user/cli.md`** — six sections (`prayer`, `qibla`, `sunnah`, `hijri`, `moon-sighting`, `astro`) each with one example, the options table, and a `--json` note; keep the three standing caveats (uqu ≠ UMM_AL_QURA, tabular ±1–2d, naive-as-UTC) plus the `syuruk`/`imsak`/`ishraq`/`dhuha` script-consumer note. Example block (all verified above):

```bash
python -m alfalak prayer --latitude 35.7750 --longitude -78.6336 --date 2015-07-12 --method NORTH_AMERICA
python -m alfalak qibla --latitude 35.7750 --longitude -78.6336 --method ellipsoidal
python -m alfalak sunnah --latitude 35.7750 --longitude -78.6336 --date 2015-07-12 --method NORTH_AMERICA
python -m alfalak hijri --reverse 1446-09-01 --calendar tabular
python -m alfalak moon-sighting --latitude 3.1390 --longitude 101.6869 --date 2025-02-28
python -m alfalak astro delta-t --year 2025.5
```

- [ ] **Step 2: Migration + cross-pointers + changelog** — `migration.md` gets a `bare → prayer` section (one-word fix, before/after invocations); each of the four doc pages gets one relative link line to `cli/`; `CHANGES.md` gets an `## Unreleased` entry listing the six subcommands, `--json`, and the bare-invocation break.

- [ ] **Step 3: Verify docs build references** — no link points into `docs/development/`; run `grep -rn "development/" docs/user/ README.md` → 0 hits.

- [ ] **Step 4: Commit**

```bash
git add docs/user/cli.md docs/user/migration.md docs/user/api-reference.md docs/user/moon-sighting.md docs/user/qibla.md docs/user/sunnah-times.md CHANGES.md
git commit -m "docs: cli expansion for six subcommands"
```

---

### Task 8: Debian artifacts (man page + shell completion)

**Files:**
- Create: `debian/al-falak.1`
- Create: `debian/completions/al-falak.bash`
- Create: `debian/completions/al-falak.zsh`

- [ ] **Step 1: Write the man page** — troff with `NAME`, `SYNOPSIS` (six subcommands), one `COMMANDS` entry per subcommand listing its flags, `EXIT STATUS` (0/2 contract), `CAVEATS` (uqu ≠ UMM_AL_QURA; tabular ±1–2d; naive-as-UTC), `SEE ALSO` (`docs/user/cli.md`). Verify with `man --local-file debian/al-falak.1` rendering without warnings (or `groff -man -Tascii` if `man` is unavailable).

- [ ] **Step 2: Write completions** — bash (`complete -F`, subcommand names on first word; `--method/--madhab/--high-latitude-rule/--polar-rule/--calendar/--country` value lists; `-f` file completion after `--offsets`) and zsh (`#compdef al-falak`, `_arguments` with the same states). Smoke-test: `bash -n debian/completions/al-falak.bash` and `zsh -n debian/completions/al-falak.zsh` both exit 0.

- [ ] **Step 3: Commit**

```bash
git add debian/al-falak.1 debian/completions/al-falak.bash debian/completions/al-falak.zsh
git commit -m "feat(debian): man page and shell completions for cli"
```

---

### Task 9: Full gate verification

- [ ] **Step 1: Run the four CI gates exactly as CI does**

Run: `black --check src/`
Expected: clean.
Run: `ruff check src/ tests/`
Expected: clean.
Run: `mypy src`
Expected: `--disallow-untyped-defs` clean (note `argparse._SubParsersAction` is private — if mypy flags the `register` annotations, annotate as `argparse._SubParsersAction[Any]` with `from typing import Any`, or use the public return type of `add_subparsers()`).
Run: `pytest --cov-fail-under=95`
Expected: whole suite green, coverage gate passes.

- [ ] **Step 2: Fix anything red, then final smoke**

Run: `python -m alfalak prayer --latitude 35.7750 --longitude -78.6336 --date 2015-07-12 --method NORTH_AMERICA | head -3`
Expected: `imsak=...`, `fajr=2015-07-12T08:42:00+00:00`, `sunrise=...`.
Run: `python -m alfalak --latitude 35 --longitude -78; echo "exit=$?"`
Expected: exit 2 with the `did you mean 'prayer'` message on stderr.

---

## Self-Review

1. **Spec coverage:** §1 command tree → Tasks 1–6, 8; §2 flags → Tasks 1–6 (all flags named, incl. `--ramadan`, `--elevation`, `--adjust`, `--declination`, `--fraction`, `--start/--end`, `--reverse`, `--month-length`, `--delta-t-override`, `--julian-day`, `--year/--override`); §3 output contract → Tasks 1–6 (keys, `--json`, NaN→null, 6dp/3dp qibla); §4 errors → `parser.error` everywhere + Task 9 smoke; §5 debian/backcompat → Task 8 + Task 1 break test; §6 tests/docs → Tasks 1–7, 9.
2. **Placeholder scan:** no `TBD/TODO/appropriate/handling` — every step names files, tests, commands, expected output.
3. **Type consistency:** `run(args, parser)`, `register(subparsers)`, `common` builder/emitter names are identical across tasks; `moon_sighting` module vs `moon-sighting` CLI name is explicit.
