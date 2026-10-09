import pytest

from alfalak.__main__ import main


def test_prayer_subcommand_byte_identical(capsys):
    main(
        [
            "prayer",
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


def test_prayer_full_parity_adjust_madhab_timezone(capsys):
    main(
        [
            "prayer",
            "--latitude",
            "3.1390",
            "--longitude",
            "101.6869",
            "--date",
            "2025-03-01",
            "--method",
            "SINGAPORE",
            "--madhab",
            "HANAFI",
            "--adjust",
            "fajr=2",
            "--adjust",
            "isha=-1",
            "--timezone",
            "Asia/Kuala_Lumpur",
        ]
    )
    out = capsys.readouterr().out
    assert "fajr=2025-03-01T06:09:00+08:00\n" in out
    assert "isha=2025-03-01T20:36:00+08:00\n" in out
    assert out.endswith("+08:00\n")


def test_prayer_json_keys_match_text(capsys):
    import json

    main(
        [
            "prayer",
            "--latitude",
            "35.7750",
            "--longitude",
            "-78.6336",
            "--date",
            "2015-07-12",
            "--method",
            "NORTH_AMERICA",
            "--json",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    assert list(data) == [
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
    ]
    assert data["fajr"] == "2015-07-12T08:42:00+00:00"


def test_bare_invocation_points_at_prayer(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2
    assert "prayer" in capsys.readouterr().err


def test_flags_before_subcommand_get_prayer_hint(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--latitude", "35", "--longitude", "-78"])
    assert excinfo.value.code == 2
    assert "prayer" in capsys.readouterr().err


def _prayer_base(extra: list[str]) -> list[str]:
    return [
        "prayer",
        "--latitude",
        "35",
        "--longitude",
        "-78",
        "--date",
        "2015-07-12",
    ] + extra


def test_prayer_rejects_fajr_angle_out_of_range(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--fajr-angle", "200"]))
    assert excinfo.value.code == 2
    assert "--fajr-angle" in capsys.readouterr().err


def test_prayer_rejects_isha_angle_out_of_range(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--isha-angle", "200"]))
    assert excinfo.value.code == 2
    assert "--isha-angle" in capsys.readouterr().err


def test_prayer_rejects_negative_isha_interval(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--isha-interval", "-1"]))
    assert excinfo.value.code == 2
    assert "--isha-interval" in capsys.readouterr().err


def test_prayer_rejects_negative_imsak_offset(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--imsak-offset", "-3"]))
    assert excinfo.value.code == 2
    assert "--imsak-offset" in capsys.readouterr().err


def test_prayer_rejects_dhuha_below_ishraq(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--ishraq-offset", "30", "--dhuha-offset", "20"]))
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--dhuha-offset" in err or "--ishraq-offset" in err


def test_prayer_rejects_negative_elevation(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--elevation", "-5"]))
    assert excinfo.value.code == 2
    assert "--elevation" in capsys.readouterr().err


def test_prayer_rejects_negative_ishraq_offset(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--ishraq-offset", "-1"]))
    assert excinfo.value.code == 2
    assert "--ishraq-offset" in capsys.readouterr().err


def test_prayer_rejects_negative_dhuha_offset(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--dhuha-offset", "-1"]))
    assert excinfo.value.code == 2
    assert "--dhuha-offset" in capsys.readouterr().err


def test_prayer_adjust_plus_sign_accepted(capsys):
    main(_prayer_base(["--adjust", "fajr=+2"]))
    assert "fajr=" in capsys.readouterr().out


def test_prayer_rejects_huge_adjust(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(_prayer_base(["--adjust", "fajr=999999999999999"]))
    assert excinfo.value.code == 2
    assert "--adjust" in capsys.readouterr().err


def test_prayer_json_is_compact(capsys):
    import json

    main(_prayer_base([]) + ["--json"])
    out = capsys.readouterr().out
    assert json.loads(out)["fajr"]
    assert '": "' not in out
