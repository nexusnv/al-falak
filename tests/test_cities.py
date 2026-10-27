"""City table + pure lookup tests (Task 1)."""

import pytest
from zoneinfo import ZoneInfo

from alfalak.data.Cities import CITY_TABLE, normalize_city_key, resolve_city
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import ValidationError


def test_normalize_variants():
    assert normalize_city_key("Kuala Lumpur,MY") == "kuala lumpur,MY"
    assert normalize_city_key("Kuala Lumpur , MY") == "kuala lumpur,MY"
    assert normalize_city_key("  kuala  LUMPUR,my  ") == "kuala lumpur,MY"
    assert normalize_city_key("kuala\tLUMPUR, MY") == "kuala lumpur,MY"
    assert normalize_city_key("A,B,CD") == "a,b,CD"


def test_normalize_empty_and_missing():
    with pytest.raises(ValidationError, match="expected NAME,CC"):
        normalize_city_key("Kuala Lumpur")
    with pytest.raises(ValidationError, match="expected NAME,CC"):
        normalize_city_key("Kuala Lumpur,")
    with pytest.raises(ValidationError, match="expected NAME,CC"):
        normalize_city_key(",MY")
    with pytest.raises(ValidationError, match="expected NAME,CC"):
        normalize_city_key(" , ")
    with pytest.raises(ValidationError, match="expected NAME,CC"):
        normalize_city_key("")


def test_bad_cc_precedence_over_lookup():
    # Well-formed CC check takes precedence: even though Paris,XX cannot
    # match, the error must be the format hint, never the cities hint.
    for raw in ["Paris,FRA", "Paris,1A", "Paris,M", "Paris,M Y", "Paris,"]:
        try:
            normalize_city_key(raw)
        except ValidationError as exc:
            assert "expected NAME,CC" in str(exc)
            assert "cities --country" not in str(exc)
        else:
            raise AssertionError(f"expected ValidationError for {raw!r}")


def test_unknown_interpolates_cc():
    with pytest.raises(ValidationError) as excinfo:
        resolve_city("Nowhereville,ZZ")
    msg = str(excinfo.value)
    assert "unknown --city" in msg
    assert "cities --country ZZ" in msg
    # Malformed input gets format hint, never the cities hint.
    with pytest.raises(ValidationError) as excinfo2:
        resolve_city("BareName")
    msg2 = str(excinfo2.value)
    assert "expected NAME,CC" in msg2
    assert "cities --country" not in msg2


def test_mecca_unknown_makkah_known():
    city = resolve_city("Makkah,SA")
    assert city.country == "SA"
    assert city.name == "Makkah"
    with pytest.raises(ValidationError, match="cities --country SA"):
        resolve_city("Mecca,SA")


def test_table_count_300_no_dup_keys():
    assert len(CITY_TABLE) == 300
    # Keys must already be normalized; no duplicates possible in a dict,
    # but assert the normalization invariant explicitly.
    for key, city in CITY_TABLE.items():
        assert key == f"{city.name.lower()},{city.country.upper()}" or (
            # Name may contain collapsed whitespace; recompute via helper
            key
            == normalize_city_key(f"{city.name},{city.country}")
        )
    assert len(set(CITY_TABLE.keys())) == 300


def test_every_tz_loads():
    for key, city in CITY_TABLE.items():
        ZoneInfo(city.timezone)


def test_every_latlon_validates():
    for key, city in CITY_TABLE.items():
        Coordinates(city.latitude, city.longitude)
        assert -90 <= city.latitude <= 90
        assert -180 <= city.longitude <= 180
