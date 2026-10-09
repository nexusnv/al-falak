import json

import pytest

from alfalak.__main__ import main


def test_qibla_spherical_two_lines(capsys):
    main(["qibla", "--latitude", "35.7750", "--longitude", "-78.6336"])
    assert capsys.readouterr().out == (
        "direction=55.825083\n" "distance_km=10943.598\n" "method=spherical\n"
    )


def test_qibla_ellipsoidal_and_magnetic(capsys):
    main(
        [
            "qibla",
            "--latitude",
            "35.7750",
            "--longitude",
            "-78.6336",
            "--method",
            "ellipsoidal",
            "--declination",
            "-8.0",
        ]
    )
    out = capsys.readouterr().out
    assert "direction=55.739247\n" in out
    assert "distance_km=10961.846\n" in out
    assert "magnetic=63.739247\n" in out


def test_qibla_json(capsys):
    main(["qibla", "--latitude", "35.7750", "--longitude", "-78.6336", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["method"] == "spherical"
    assert abs(data["direction"] - 55.82508273783204) < 1e-9


def test_qibla_bad_method_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "qibla",
                "--latitude",
                "35",
                "--longitude",
                "-78",
                "--method",
                "BOGUS",
            ]
        )
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--method" in err
    assert "BOGUS" in err


def test_qibla_latitude_out_of_range_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["qibla", "--latitude", "100", "--longitude", "0"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "Latitude" in err
    assert "100" in err


def test_qibla_nan_declination_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "qibla",
                "--latitude",
                "35",
                "--longitude",
                "-78",
                "--declination",
                "nan",
            ]
        )
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "eclination" in err
    assert "nan" in err


def test_qibla_json_includes_magnetic_with_declination(capsys):
    main(
        [
            "qibla",
            "--latitude",
            "35.7750",
            "--longitude",
            "-78.6336",
            "--declination",
            "-8.0",
            "--json",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    assert "magnetic" in data
    assert abs(data["magnetic"] - 63.82508273783204) < 1e-9
