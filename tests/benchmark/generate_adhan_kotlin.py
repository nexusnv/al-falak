#!/usr/bin/env python3
"""Generate adhan-kotlin cross-port vectors (Phase 6.1).

Clones ``batoulapps/adhan-kotlin`` at the pinned SHA below (or reuses a local
checkout via ``--source-dir``), injects a scratch JVM test that runs the fixed
grid in :mod:`grid`, and writes ``tests/benchmark/vectors/adhan_kotlin.json``.

Two passes per entry:

- ``Rounding.NONE`` -> ``unrounded`` (whole-second, ``seconds_procedure``
  ``"second"``), used by tier-(a);
- ``Rounding.NEAREST`` -> ``rounded`` (adhan2's ``Float.roundToInt``,
  half-away-from-zero), used by tier-(b).

The high-latitude rule is pinned on the per-method parameter copy:

    CalculationMethod.<METHOD>.parameters.copy(
        highLatitudeRule = HighLatitudeRule.MIDDLE_OF_THE_NIGHT
    )

The bare ``CalculationParameters`` constructor is never used: it would discard
the method's angles and adjustments. adhan2's default is
``HighLatitudeRule.recommendedFor(coordinates)`` (seventh-of-the-night above
48 degrees), whereas this library fixes middle-of-the-night, so the pin is
required for a like-for-like comparison.

Requirements: JDK 17+ (``JAVA_HOME`` or ``java`` on ``PATH``) and Gradle.
The pinned revision's wrapper is Gradle 9.5.1; pass ``--gradle-bin`` to reuse
an installed Gradle instead of downloading the wrapper distribution.

Usage:
    python tests/benchmark/generate_adhan_kotlin.py
    python tests/benchmark/generate_adhan_kotlin.py --source-dir /path/to/adhan-kotlin
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grid  # noqa: E402  (path set above)

PIN = grid.SOURCE_PINS["adhan_kotlin"]
SHA = PIN["sha"]
VERSION = PIN["version"]
REPO = "https://github.com/batoulapps/adhan-kotlin"
VECTOR_PATH = HERE / "vectors" / "adhan_kotlin.json"
TEST_CLASS = "com.batoulapps.adhan2.GenerateVectorsTest"
TEST_RELATIVE_PATH = Path(
    "adhan/src/jvmTest/kotlin/com/batoulapps/adhan2/GenerateVectorsTest.kt"
)

TEST_TEMPLATE = """\
package com.batoulapps.adhan2

import com.batoulapps.adhan2.data.DateComponents
import com.batoulapps.adhan2.model.Rounding
import java.io.File
import java.time.Instant
import java.time.temporal.ChronoUnit
import kotlin.test.Test

class GenerateVectorsTest {{
  private data class Row(
    val city: String,
    val latitude: Double,
    val longitude: Double,
    val date: String
  )

  private fun iso(instant: kotlin.time.Instant): String =
    Instant.ofEpochMilli(instant.toEpochMilliseconds())
      .truncatedTo(ChronoUnit.SECONDS)
      .toString()

  @Test
  fun generate() {{
    val rows = listOf(
{rows}
    )
    val methods = listOf({methods})
    val entries = mutableListOf<String>()

    for (row in rows) {{
      val parts = row.date.split("-")
      val dateComponents = DateComponents(
        parts[0].toInt(),
        parts[1].toInt(),
        parts[2].toInt()
      )
      val coordinates = Coordinates(row.latitude, row.longitude)
      for (methodName in methods) {{
        val method = when (methodName) {{
          "MUSLIM_WORLD_LEAGUE" -> CalculationMethod.MUSLIM_WORLD_LEAGUE
          "NORTH_AMERICA" -> CalculationMethod.NORTH_AMERICA
          else -> error("unknown method $methodName")
        }}
        val base = method.parameters
        val noRound = base.copy(
          highLatitudeRule = HighLatitudeRule.MIDDLE_OF_THE_NIGHT,
          rounding = Rounding.NONE
        )
        val nearest = base.copy(
          highLatitudeRule = HighLatitudeRule.MIDDLE_OF_THE_NIGHT,
          rounding = Rounding.NEAREST
        )
        val ptNone = PrayerTimes(coordinates, dateComponents, noRound)
        val ptNear = PrayerTimes(coordinates, dateComponents, nearest)
        entries += \"\"\"
          {{
            "city": "${{row.city}}",
            "latitude": ${{row.latitude}},
            "longitude": ${{row.longitude}},
            "date": "${{row.date}}",
            "method": "$methodName",
            "unrounded": {{
              "fajr": "${{iso(ptNone.fajr)}}",
              "sunrise": "${{iso(ptNone.sunrise)}}",
              "dhuhr": "${{iso(ptNone.dhuhr)}}",
              "asr": "${{iso(ptNone.asr)}}",
              "maghrib": "${{iso(ptNone.maghrib)}}",
              "isha": "${{iso(ptNone.isha)}}"
            }},
            "rounded": {{
              "fajr": "${{iso(ptNear.fajr)}}",
              "sunrise": "${{iso(ptNear.sunrise)}}",
              "dhuhr": "${{iso(ptNear.dhuhr)}}",
              "asr": "${{iso(ptNear.asr)}}",
              "maghrib": "${{iso(ptNear.maghrib)}}",
              "isha": "${{iso(ptNear.isha)}}"
            }}
          }}
        \"\"\".trimIndent()
      }}
    }}

    val out = File(
      System.getenv("ADHAN_VECTORS_OUT")
        ?: error("ADHAN_VECTORS_OUT is not set")
    )
    out.writeText("{{\\"entries\\":[" + entries.joinToString(",") + "]}}")
    println("WROTE ${{out.absolutePath}} (${{entries.size}} entries)")
  }}
}}
"""


def _kotlin_rows() -> str:
    lines = []
    for city, latitude, longitude, date_string in grid.GRID:
        lines.append(
            "      Row("
            f"{json.dumps(city)}, {latitude}, {longitude}, "
            f"{json.dumps(date_string)})"
        )
    return ",\n".join(lines)


def _kotlin_methods() -> str:
    return ", ".join(json.dumps(method) for method in grid.METHODS)


def _checkout(source_dir: str | None) -> tuple[Path, bool]:
    if source_dir is not None:
        repo_dir = Path(source_dir).resolve()
        if not (repo_dir / "adhan").is_dir():
            raise SystemExit(f"no adhan module under {repo_dir}")
        grid.assert_pinned_head(repo_dir, SHA)
        return repo_dir, False

    repo_dir = Path(tempfile.mkdtemp(prefix="adhan-kotlin-")) / "repo"
    subprocess.run(
        ["git", "clone", "--quiet", "--filter=blob:none", REPO, str(repo_dir)],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo_dir), "checkout", "--quiet", SHA], check=True)
    grid.assert_pinned_head(repo_dir, SHA)
    return repo_dir, True


def _gradle_command(repo_dir: Path, gradle_bin: str | None) -> list[str]:
    if gradle_bin is not None:
        return [gradle_bin]
    wrapper = repo_dir / "gradlew"
    if wrapper.is_file():
        return [str(wrapper)]
    gradle = shutil.which("gradle")
    if gradle is None:
        raise SystemExit(
            "Gradle not found: install it, pass --gradle-bin, or provide "
            "a JDK/Gradle-capable checkout with a wrapper"
        )
    return [gradle]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        help="Existing adhan-kotlin checkout at the pinned SHA (offline)",
    )
    parser.add_argument(
        "--gradle-bin",
        help="Path to a Gradle executable (skips the pinned wrapper download)",
    )
    parser.add_argument(
        "--keep-build",
        action="store_true",
        help="Keep the temporary clone and build outputs",
    )
    args = parser.parse_args()

    if not os.environ.get("JAVA_HOME") and shutil.which("java") is None:
        raise SystemExit("JDK 17+ required: set JAVA_HOME or put java on PATH")

    repo_dir, temporary = _checkout(args.source_dir)
    test_path = repo_dir / TEST_RELATIVE_PATH
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(
        TEST_TEMPLATE.format(rows=_kotlin_rows(), methods=_kotlin_methods()),
        encoding="utf-8",
    )

    entries_dir = Path(tempfile.mkdtemp(prefix="adhan-vectors-"))
    entries_path = entries_dir / "entries.json"
    env = os.environ.copy()
    env["ADHAN_VECTORS_OUT"] = str(entries_path)
    command = _gradle_command(repo_dir, args.gradle_bin) + [
        "--no-daemon",
        "--console=plain",
        ":adhan:jvmTest",
        "--tests",
        TEST_CLASS,
    ]
    subprocess.run(command, cwd=repo_dir, env=env, check=True)

    data = json.loads(entries_path.read_text(encoding="utf-8"))
    expected = len(grid.GRID) * len(grid.METHODS)
    if len(data["entries"]) != expected:
        raise SystemExit(
            f"generated {len(data['entries'])} entries, expected {expected}"
        )

    payload = {
        "source": "adhan_kotlin",
        "version": VERSION,
        "sha": SHA,
        "generator": "tests/benchmark/generate_adhan_kotlin.py",
        "seconds_procedure": PIN["seconds_procedure"],
        "rounded_rounding": (
            "Rounding.NEAREST (Float.roundToInt, half-away-from-zero)"
        ),
        "high_latitude_rule": PIN["high_latitude_rule"],
        "entries": data["entries"],
    }
    VECTOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTOR_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {VECTOR_PATH} ({len(payload['entries'])} entries)")

    if temporary and not args.keep_build:
        shutil.rmtree(repo_dir.parent, ignore_errors=True)
    shutil.rmtree(entries_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
