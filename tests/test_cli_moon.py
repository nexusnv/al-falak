import json

import pytest

from alfalak.__main__ import main

MOON_ARGS = [
    "moon-sighting",
    "--latitude",
    "3.1390",
    "--longitude",
    "101.6869",
    "--date",
    "2025-02-28",
]


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
        "arcl_deg",
        "arcv_geo_deg",
        "arcv_topo_deg",
        "sun_alt_deg",
        "moon_alt_topo_deg",
        "daz_deg",
        "width_arcmin",
        "illumination",
        "lag_hours",
        "moon_age_days",
        "moon_age_at_moonset_days",
        "used_delta_t_s",
        "sunset_jd_utc",
        "yallop_q",
        "yallop_zone",
        "odeh_v",
        "odeh_class",
        "neo_mabims",
        "mabims_1992",
    }
    assert data["yallop_zone"] == "F"


def test_moon_sighting_polar_no_sunset(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "moon-sighting",
                "--latitude",
                "78.22",
                "--longitude",
                "15.63",
                "--date",
                "2025-06-21",
            ]
        )
    assert excinfo.value.code == 2
    assert "does not set" in capsys.readouterr().err


# Reykjavik 2025-04-02 has no moonset on that date: lag/moonset-age are NaN.
REYKJAVIK_NO_MOONSET = [
    "moon-sighting",
    "--latitude",
    "64.1466",
    "--longitude",
    "-21.9426",
    "--date",
    "2025-04-02",
]


def test_moon_sighting_no_moonset_text_nan(capsys):
    main(REYKJAVIK_NO_MOONSET)
    out = capsys.readouterr().out
    assert "lag_hours=nan\n" in out
    assert "moon_age_at_moonset_days=nan\n" in out


def test_moon_sighting_no_moonset_json_null(capsys):
    main(REYKJAVIK_NO_MOONSET + ["--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["lag_hours"] is None
    assert data["moon_age_at_moonset_days"] is None


def test_moon_sighting_nan_delta_t_override_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(MOON_ARGS + ["--delta-t-override", "nan"])
    assert excinfo.value.code == 2
    assert "override" in capsys.readouterr().err


def test_moon_sighting_bad_date_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "moon-sighting",
                "--latitude",
                "3.1390",
                "--longitude",
                "101.6869",
                "--date",
                "2025/02/28",
            ]
        )
    assert excinfo.value.code == 2
    assert "--date" in capsys.readouterr().err
