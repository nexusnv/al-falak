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
