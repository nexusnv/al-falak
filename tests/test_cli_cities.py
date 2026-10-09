"""CLI --city resolver + parity tests (Task 2). Hijri/cities tests land in Task 3/4."""

import pytest

from alfalak.__main__ import main


def _run(args):
    return main(args)


def test_xor_both_neither_partial(capsys):
    # both city+coords
    with pytest.raises(SystemExit) as e:
        _run(
            [
                "prayer",
                "--city",
                "Kuala Lumpur,MY",
                "--latitude",
                "3.1390",
                "--longitude",
                "101.6869",
            ]
        )
    assert e.value.code == 2
    # neither
    with pytest.raises(SystemExit) as e2:
        _run(["prayer", "--date", "2025-03-01"])
    assert e2.value.code == 2
    assert "--city" in capsys.readouterr().err
    # lat-only partial
    with pytest.raises(SystemExit) as e3:
        _run(["prayer", "--latitude", "3.1390"])
    assert e3.value.code == 2
    # city + lat-only partial
    with pytest.raises(SystemExit) as e4:
        _run(
            ["prayer", "--city", "Kuala Lumpur,MY", "--latitude", "3.1390"]
        )
    assert e4.value.code == 2


def _capture(args, capsys):
    _run(args)
    return capsys.readouterr().out


@pytest.mark.parametrize(
    "city,lat,lon,tz",
    [
        ("Kuala Lumpur,MY", "3.1390", "101.6869", "Asia/Kuala_Lumpur"),
        ("Makkah,SA", "21.4225", "39.8262", "Asia/Riyadh"),
        ("London,GB", "51.5074", "-0.1278", "Europe/London"),
    ],
)
def test_parity_a_explicit_tz(capsys, city, lat, lon, tz):
    base = ["--date", "2025-03-01", "--method", "MUSLIM_WORLD_LEAGUE"]
    out_city = _capture(
        ["prayer", "--city", city, "--timezone", tz] + base, capsys
    )
    out_coords = _capture(
        ["prayer", "--latitude", lat, "--longitude", lon, "--timezone", tz] + base,
        capsys,
    )
    assert out_city == out_coords


@pytest.mark.parametrize(
    "city,lat,lon,tz",
    [
        ("Kuala Lumpur,MY", "3.1390", "101.6869", "Asia/Kuala_Lumpur"),
        ("Makkah,SA", "21.4225", "39.8262", "Asia/Riyadh"),
        ("London,GB", "51.5074", "-0.1278", "Europe/London"),
    ],
)
def test_parity_b_bare_city_default(capsys, city, lat, lon, tz):
    base = ["--date", "2025-03-01", "--method", "MUSLIM_WORLD_LEAGUE"]
    out_city = _capture(["prayer", "--city", city] + base, capsys)
    out_coords = _capture(
        ["prayer", "--latitude", lat, "--longitude", lon, "--timezone", tz] + base,
        capsys,
    )
    assert out_city == out_coords


def test_utc_default_differs(capsys):
    base = ["--date", "2025-03-01", "--method", "MUSLIM_WORLD_LEAGUE"]
    out_city = _capture(["prayer", "--city", "Kuala Lumpur,MY"] + base, capsys)
    out_coords = _capture(
        ["prayer", "--latitude", "3.1390", "--longitude", "101.6869"] + base,
        capsys,
    )
    assert out_city != out_coords


def test_unknown_city_hint(capsys):
    with pytest.raises(SystemExit) as e:
        _run(["prayer", "--city", "Nowhereville,ZZ"])
    assert e.value.code == 2
    assert "cities --country ZZ" in capsys.readouterr().err


def test_bad_cc_format_hint(capsys):
    with pytest.raises(SystemExit) as e:
        _run(["prayer", "--city", "BareName"])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "expected NAME,CC" in err
    assert "cities --country" not in err


def test_bad_tz_wrap(monkeypatch, capsys):
    from alfalak.data import Cities as cities_mod
    from alfalak.data.Cities import City

    bad = City(
        name="Badville",
        country="XX",
        latitude=0.0,
        longitude=0.0,
        timezone="Never/Exists",
    )
    monkeypatch.setitem(dict(cities_mod.CITY_TABLE), "badville,XX", bad)
    # MappingProxyType is immutable; patch the module attribute with a new proxy
    from types import MappingProxyType

    patched = dict(cities_mod.CITY_TABLE)
    patched["badville,XX"] = bad
    monkeypatch.setattr(cities_mod, "CITY_TABLE", MappingProxyType(patched))
    with pytest.raises(SystemExit) as e:
        _run(["prayer", "--city", "Badville,XX", "--date", "2025-03-01"])
    assert e.value.code == 2


def test_hijri_city_needs_transition():
    with pytest.raises(SystemExit) as e:
        _run(
            [
                "hijri",
                "--date",
                "2025-03-01",
                "--calendar",
                "tabular",
                "--city",
                "Kuala Lumpur,MY",
            ]
        )
    assert e.value.code == 2


def test_hijri_city_clashes_with_latlon():
    with pytest.raises(SystemExit) as e:
        _run(
            [
                "hijri",
                "--date",
                "2025-03-01",
                "--calendar",
                "tabular",
                "--sunset-transition",
                "--city",
                "Kuala Lumpur,MY",
                "--lat",
                "3.1390",
                "--lon",
                "101.6869",
                "--time",
                "12:00",
            ]
        )
    assert e.value.code == 2


def test_hijri_city_needs_time():
    with pytest.raises(SystemExit) as e:
        _run(
            [
                "hijri",
                "--date",
                "2025-03-01",
                "--calendar",
                "tabular",
                "--sunset-transition",
                "--city",
                "Kuala Lumpur,MY",
            ]
        )
    assert e.value.code == 2


def test_hijri_city_sunset_parity(capsys):
    base = ["hijri", "--date", "2025-03-01", "--calendar", "tabular"]
    _run(
        base
        + [
            "--sunset-transition",
            "--city",
            "Kuala Lumpur,MY",
            "--time",
            "12:00",
        ]
    )
    out_city = capsys.readouterr().out
    _run(
        base
        + [
            "--sunset-transition",
            "--lat",
            "3.1390",
            "--lon",
            "101.6869",
            "--time",
            "12:00",
        ]
    )
    out_coords = capsys.readouterr().out
    assert out_city == out_coords
    assert out_city == "hijri=1446-09-02\ncalendar=tabular\n"


def test_hijri_city_reverse_clash():
    with pytest.raises(SystemExit) as e:
        _run(
            [
                "hijri",
                "--calendar",
                "tabular",
                "--reverse",
                "1446-09-01",
                "--city",
                "Kuala Lumpur,MY",
            ]
        )
    assert e.value.code == 2
