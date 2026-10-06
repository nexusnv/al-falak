import re
import subprocess
import sys

import pytest
from alfalak.__main__ import main
from alfalak.exceptions import ConfigurationError


def test_cli_prints_iso_times(capsys):
    main(
        [
            "--latitude",
            "35.7750",
            "--longitude",
            "-78.6336",
            "--date",
            "2015-07-12",
            "--method",
            "NORTH_AMERICA",
        ]
    )

    lines = dict(
        line.split("=", 1) for line in capsys.readouterr().out.strip().splitlines()
    )
    assert set(lines) == {
        "imsak",
        "fajr",
        "sunrise",
        "syuruk",
        "ishraq",
        "dhuha",
        "dhuhr",
        "asr",
        "maghrib",
        "isha",
    }
    assert lines["fajr"] == "2015-07-12T08:42:00+00:00"
    assert lines["imsak"] == "2015-07-12T08:32:00+00:00"
    assert lines["syuruk"] == lines["sunrise"]
    assert lines["ishraq"] == "2015-07-12T10:23:00+00:00"
    assert lines["dhuha"] == "2015-07-12T10:36:00+00:00"


def test_cli_defaults_to_today(capsys):
    main(["--latitude", "35.7750", "--longitude", "-78.6336"])

    assert "fajr=" in capsys.readouterr().out


def test_cli_rejects_unknown_method():
    with pytest.raises(SystemExit) as excinfo:
        main(["--latitude", "35", "--longitude", "-78", "--method", "BOGUS"])

    assert excinfo.value.code == 2


def test_cli_rejects_bad_date():
    with pytest.raises(SystemExit) as excinfo:
        main(["--latitude", "35", "--longitude", "-78", "--date", "not-a-date"])

    assert excinfo.value.code == 2


def test_cli_rejects_datetime_for_date():
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "--latitude",
                "35",
                "--longitude",
                "-78",
                "--date",
                "2015-07-12T00:00:00",
            ]
        )

    assert excinfo.value.code == 2


def test_cli_requires_coordinates():
    with pytest.raises(SystemExit) as excinfo:
        main(["--latitude", "35"])

    assert excinfo.value.code == 2


def test_cli_module_entry_point():
    # smoke test: the installed package runs as python -m alfalak
    result = subprocess.run(
        [sys.executable, "-m", "alfalak", "--latitude", "35", "--longitude", "-78"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "fajr=" in result.stdout


def test_cli_bare_prayer_byte_identical(capsys):
    main(
        [
            "--latitude",
            "35.7750",
            "--longitude",
            "-78.6336",
            "--date",
            "2015-07-12",
            "--method",
            "NORTH_AMERICA",
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


def test_cli_hijri_two_line_output(capsys):
    main(["hijri", "--date", "2025-03-01", "--calendar", "tabular"])

    assert capsys.readouterr().out == "hijri=1446-09-01\ncalendar=tabular\n"


def test_cli_hijri_country_required_iff_mabims():
    with pytest.raises(ConfigurationError, match="(?i)country"):
        main(["hijri", "--date", "2025-03-01", "--calendar", "mabims"])
    with pytest.raises(ConfigurationError, match="(?i)country"):
        main(
            [
                "hijri",
                "--date",
                "2025-03-01",
                "--calendar",
                "tabular",
                "--country",
                "MY",
            ]
        )


def test_cli_hijri_country_case_insensitive(capsys):
    main(
        [
            "hijri",
            "--date",
            "2025-03-01",
            "--calendar",
            "mabims",
            "--country",
            "my",
        ]
    )
    out = capsys.readouterr().out
    assert re.fullmatch(r"hijri=\d{4}-\d{2}-\d{2}\ncalendar=mabims-MY\n", out)


def test_cli_hijri_rejects_top_level_coordinates():
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "--latitude",
                "3.1390",
                "--longitude",
                "101.6869",
                "hijri",
                "--date",
                "2025-03-01",
                "--calendar",
                "tabular",
            ]
        )
    assert excinfo.value.code == 2


def test_cli_hijri_time_required_iff_transition():
    base = ["hijri", "--date", "2025-03-01", "--calendar", "tabular"]
    with pytest.raises(ConfigurationError, match="(?i)sunset|transition|time"):
        main(base + ["--sunset-transition", "--lat", "3.1390", "--lon", "101.6869"])
    with pytest.raises(ConfigurationError, match="(?i)sunset|transition|lat|lon"):
        main(base + ["--sunset-transition", "--time", "19:30"])
    with pytest.raises(ConfigurationError, match="(?i)sunset|transition"):
        main(base + ["--time", "19:30"])


def test_cli_hijri_sunset_transition_two_lines(capsys):
    main(
        [
            "hijri",
            "--date",
            "2025-03-01",
            "--calendar",
            "tabular",
            "--sunset-transition",
            "--lat",
            "3.1390",
            "--lon",
            "101.6869",
            "--time",
            "00:00",
        ]
    )

    assert capsys.readouterr().out == "hijri=1446-09-01\ncalendar=tabular\n"


def test_cli_hijri_adjustment_days_only_tabular():
    with pytest.raises(ConfigurationError, match="(?i)adjustment"):
        main(
            [
                "hijri",
                "--date",
                "2025-03-01",
                "--calendar",
                "uqu",
                "--adjustment-days",
                "1",
            ]
        )


def test_cli_hijri_unknown_calendar_rejected():
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--date", "2025-03-01", "--calendar", "BOGUS"])
    assert excinfo.value.code == 2


def test_cli_hijri_offsets_file(tmp_path, capsys):
    offsets = tmp_path / "offsets.json"
    offsets.write_text('{"1446-09": 1}', encoding="utf-8")
    main(
        [
            "hijri",
            "--date",
            "2025-03-01",
            "--calendar",
            "tabular",
            "--offsets",
            str(offsets),
        ]
    )

    assert capsys.readouterr().out == "hijri=1446-09-02\ncalendar=tabular\n"


def test_cli_hijri_help_states_distinctions(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--help"])
    assert excinfo.value.code == 0
    text = capsys.readouterr().out
    assert "UMM_AL_QURA" in text  # calendar-vs-prayer-preset distinction
    assert "1-2" in text  # tabular-vs-observed caveat
    assert "UTC" in text  # naive wall-clock treated as UTC


def test_cli_hijri_invalid_time_rejected():
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "hijri",
                "--date",
                "2025-03-01",
                "--calendar",
                "tabular",
                "--sunset-transition",
                "--lat",
                "3.1390",
                "--lon",
                "101.6869",
                "--time",
                "bogus",
            ]
        )
    assert excinfo.value.code == 2


def test_cli_hijri_defaults_to_today(capsys):
    main(["hijri", "--calendar", "tabular"])
    out = capsys.readouterr().out
    assert re.fullmatch(r"hijri=\d{4}-\d{2}-\d{2}\ncalendar=tabular\n", out)


def test_cli_hijri_rejects_bad_date():
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--date", "not-a-date", "--calendar", "tabular"])
    assert excinfo.value.code == 2


def test_cli_hijri_lat_lon_require_transition():
    with pytest.raises(ConfigurationError, match="sunset-transition"):
        main(
            [
                "hijri",
                "--date",
                "2025-03-01",
                "--calendar",
                "tabular",
                "--lat",
                "3.1390",
                "--lon",
                "101.6869",
            ]
        )


def test_cli_main_guard(monkeypatch, capsys):
    import runpy

    monkeypatch.setattr(
        sys, "argv", ["al-falak", "--latitude", "35", "--longitude", "-78"]
    )
    runpy.run_module("alfalak", run_name="__main__")
    assert "fajr=" in capsys.readouterr().out
