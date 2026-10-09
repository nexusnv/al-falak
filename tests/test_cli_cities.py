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


def test_cities_text_shape(capsys):
    _run(["cities"])
    out = capsys.readouterr().out
    assert out and not out.endswith("\n\n")
    assert not out.endswith("\n\n")
    blocks = out.split("\n\n")
    assert len(blocks) == 300
    # sort by (country, name.lower()) byte order
    keys = []
    for block in blocks:
        lines = block.splitlines()
        assert len(lines) == 5
        assert lines[0].startswith("city=")
        assert lines[1].startswith("country=")
        assert lines[2].startswith("latitude=")
        assert lines[3].startswith("longitude=")
        assert lines[4].startswith("timezone=")
        city_disp = lines[0].split("=", 1)[1]
        country = lines[1].split("=", 1)[1]
        name = city_disp.rsplit(",", 1)[0]
        keys.append((country, name.lower()))
        # 4-decimal values
        lat_s = lines[2].split("=", 1)[1]
        lon_s = lines[3].split("=", 1)[1]
        assert "." in lat_s and len(lat_s.split(".")[1]) == 4
        assert "." in lon_s and len(lon_s.split(".")[1]) == 4
    assert keys == sorted(keys)
    # spot-check pinned entries
    assert "city=Kuala Lumpur,MY\ncountry=MY\n" in out
    assert "city=Makkah,SA\ncountry=SA\n" in out


def test_cities_json_shape(capsys):
    import json

    _run(["cities", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 300
    for obj in data:
        assert set(obj) == {"city", "country", "latitude", "longitude", "timezone"}
    # same sort as text
    keys = [(o["country"], o["city"].rsplit(",", 1)[0].lower()) for o in data]
    assert keys == sorted(keys)


def test_cities_country_filter(capsys):
    import json

    _run(["cities", "--country", "my"])
    out_my = capsys.readouterr().out
    _run(["cities", "--country", "MY"])
    out_MY = capsys.readouterr().out
    assert out_my == out_MY
    assert "country=MY" in out_my
    _run(["cities", "--country", "  my  ", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data and all(o["country"] == "MY" for o in data)


def test_cities_bad_country_exit2(capsys):
    with pytest.raises(SystemExit) as e:
        _run(["cities", "--country", "M"])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e2:
        _run(["cities", "--country", "MY1"])
    assert e2.value.code == 2


def test_cities_unmatched_empty_success(capsys):
    _run(["cities", "--country", "ZZ"])
    assert capsys.readouterr().out == ""
    _run(["cities", "--country", "ZZ", "--json"])
    assert capsys.readouterr().out.strip() == "[]"
