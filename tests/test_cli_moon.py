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
