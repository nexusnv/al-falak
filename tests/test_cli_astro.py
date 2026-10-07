import json
import warnings

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


def test_astro_lunar_bad_jd_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["astro", "lunar-position", "--julian-day", "nan"])
    assert excinfo.value.code == 2
    assert capsys.readouterr().err != ""


def test_astro_delta_t_json(capsys):
    main(["astro", "delta-t", "--year", "2025.5", "--json"])
    assert json.loads(capsys.readouterr().out) == {"delta_t": 74.76958225}


def test_astro_delta_t_override_passthrough(capsys):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        main(["astro", "delta-t", "--year", "1800.5"])
    without_override = capsys.readouterr().out
    main(["astro", "delta-t", "--year", "1800.5", "--override", "20.5"])
    with_override = capsys.readouterr().out
    assert with_override == "delta_t=20.5\n"
    assert without_override != with_override


def test_astro_bare_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["astro"])
    assert excinfo.value.code == 2
    assert capsys.readouterr().err != ""
