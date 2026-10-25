#!/usr/bin/env python3
"""Generate adhanpy cross-port vectors (Phase 6.1).

Installs adhanpy at the pinned SHA below (or reuses a local checkout via
``--source-dir``), computes the fixed grid in :mod:`grid`, and writes
``tests/benchmark/vectors/adhanpy.json``.

adhanpy rounds to the minute and exposes no sub-minute value, so its vectors
declare ``seconds_procedure: "minute-only"`` and contain no ``unrounded``
key. The harness exercises the minute-only tier-(b) branch, including
adhanpy's documented minute-59 rollover artifact.

Usage:
    python tests/benchmark/generate_adhanpy.py
    python tests/benchmark/generate_adhanpy.py --source-dir /path/to/adhanpy
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grid  # noqa: E402  (path set above)

PIN = grid.SOURCE_PINS["adhanpy"]
SHA = PIN["sha"]
PKG = f"git+https://github.com/alphahm/adhanpy@{SHA}"
VECTOR_PATH = HERE / "vectors" / "adhanpy.json"

INNER_SCRIPT = r"""
import datetime as dt
import json
import os
from pathlib import Path

from grid import GRID, METHODS, SOURCE_PINS

from adhanpy.calculation import CalculationMethod, CalculationParameters
from adhanpy.calculation.HighLatitudeRule import HighLatitudeRule
from adhanpy.PrayerTimes import PrayerTimes

PIN = SOURCE_PINS["adhanpy"]


def to_utc_iso(value):
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


entries = []
for city, latitude, longitude, date_string in GRID:
    year, month, day = (int(part) for part in date_string.split("-"))
    date = dt.datetime(year, month, day, tzinfo=dt.timezone.utc)
    for method_name in METHODS:
        params = CalculationParameters(method=CalculationMethod[method_name])
        params.high_latitude_rule = HighLatitudeRule.MIDDLE_OF_THE_NIGHT
        prayer_times = PrayerTimes(
            (latitude, longitude), date, calculation_parameters=params
        )
        entries.append(
            {
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                "date": date_string,
                "method": method_name,
                "rounded": {
                    prayer: to_utc_iso(getattr(prayer_times, prayer))
                    for prayer in (
                        "fajr",
                        "sunrise",
                        "dhuhr",
                        "asr",
                        "maghrib",
                        "isha",
                    )
                },
            }
        )

payload = {
    "source": "adhanpy",
    "version": PIN["version"],
    "sha": PIN["sha"],
    "generator": "tests/benchmark/generate_adhanpy.py",
    "seconds_procedure": PIN["seconds_procedure"],
    "rounded_rounding": (
        "adhanpy CalendarUtil.rounded_minute "
        "(round-half-even on second/60; minute-59 truncation fallback)"
    ),
    "high_latitude_rule": PIN["high_latitude_rule"],
    "entries": entries,
}
out = Path(os.environ["ADHANPY_VECTORS_OUT"])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(out)
"""


def _interpreter(source_dir: str | None) -> tuple[str, dict[str, str]]:
    env = os.environ.copy()
    if source_dir is not None:
        source_root = Path(source_dir).resolve()
        grid.assert_pinned_head(source_root, SHA)
        src = source_root / "src"
        if not (src / "adhanpy").is_dir():
            raise SystemExit(f"no adhanpy package under {src}")
        env["PYTHONPATH"] = str(src)
        return sys.executable, env

    venv_dir = Path(tempfile.mkdtemp(prefix="adhanpy-venv-"))
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    python = venv_dir / ("Scripts" if os.name == "nt" else "bin") / "python"
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-deps", PKG],
        check=True,
    )
    return str(python), env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        help="Existing adhanpy checkout at the pinned SHA (offline generation)",
    )
    args = parser.parse_args()

    python, env = _interpreter(args.source_dir)
    env["ADHANPY_VECTORS_OUT"] = str(VECTOR_PATH)
    subprocess.run(
        [python, "-c", INNER_SCRIPT],
        cwd=HERE,
        env=env,
        check=True,
    )
    data = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    expected = len(grid.GRID) * len(grid.METHODS)
    if len(data["entries"]) != expected:
        raise SystemExit(
            f"generated {len(data['entries'])} entries, expected {expected}"
        )
    print(f"wrote {VECTOR_PATH} ({len(data['entries'])} entries)")


if __name__ == "__main__":
    main()
