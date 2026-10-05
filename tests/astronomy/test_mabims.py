import math
from datetime import date

import pytest
from alfalak.astronomy.CrescentGeometry import crescent_geometry_at_sunset
from alfalak.astronomy.Mabims import is_mabims_1992, is_neo_mabims_2021
from alfalak.astronomy.Odeh import odeh_class, odeh_v
from alfalak.astronomy.Yallop import yallop_q, yallop_zone
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import ValidationError


def test_neo_needs_both_thresholds():
    assert is_neo_mabims_2021(4.0, 7.0) is True
    assert is_neo_mabims_2021(2.9, 7.0) is False
    assert is_neo_mabims_2021(4.0, 6.3) is False


def test_old_rule_age_or_branch():
    assert is_mabims_1992(2.5, 3.5, 2.0) is True
    assert is_mabims_1992(1.0, 1.0, 9.0) is True
    assert is_mabims_1992(1.0, 1.0, 2.0) is False


BAD_REALS = [True, False, "3", None, float("inf"), -float("inf"), float("nan")]
BAD_IDS = ["bool-true", "bool-false", "string", "none", "inf", "neg-inf", "nan"]


@pytest.mark.parametrize("bad", BAD_REALS, ids=BAD_IDS)
def test_neo_rejects_bad_altitude(bad):
    with pytest.raises(ValidationError, match="(?i)real|finite"):
        is_neo_mabims_2021(bad, 7.0)


@pytest.mark.parametrize("bad", BAD_REALS, ids=BAD_IDS)
def test_neo_rejects_bad_elongation(bad):
    with pytest.raises(ValidationError, match="(?i)real|finite"):
        is_neo_mabims_2021(4.0, bad)


@pytest.mark.parametrize("bad", BAD_REALS, ids=BAD_IDS)
def test_old_rejects_bad_altitude(bad):
    with pytest.raises(ValidationError, match="(?i)real|finite"):
        is_mabims_1992(bad, 3.5, 2.0)


@pytest.mark.parametrize("bad", BAD_REALS, ids=BAD_IDS)
def test_old_rejects_bad_elongation(bad):
    with pytest.raises(ValidationError, match="(?i)real|finite"):
        is_mabims_1992(2.5, bad, 2.0)


@pytest.mark.parametrize("bad", BAD_REALS, ids=BAD_IDS)
def test_old_rejects_bad_age(bad):
    with pytest.raises(ValidationError, match="(?i)real|finite"):
        is_mabims_1992(2.5, 3.5, bad)


def test_neo_exact_boundaries():
    assert is_neo_mabims_2021(3.0, 6.4) is True
    assert is_neo_mabims_2021(2.999, 6.4) is False
    assert is_neo_mabims_2021(3.0, 6.399) is False


def test_old_exact_boundaries():
    assert is_mabims_1992(2.0, 3.0, 0.0) is True
    assert is_mabims_1992(1.999, 3.0, 0.0) is False
    assert is_mabims_1992(2.0, 2.999, 0.0) is False
    assert is_mabims_1992(0.0, 0.0, 8.0) is True
    assert is_mabims_1992(0.0, 0.0, 7.999) is False


# MABIMS takes the Moon's topocentric altitude, which
# CrescentGeometry now exposes directly (no ARCV-minus-sunset proxy).
def test_criteria_agreement_matrix():
    # Goldens recorded 2026-10-05 from a live run at local sunset (see
    # CrescentGeometry.crescent_geometry_at_sunset), verified sane: Makkah
    # 2025-02-28 (Ramadan-eve crescent, ARCL ~8.4 deg, moon_alt ~6.2 deg)
    # is visible under both MABIMS rules (Odeh C: optical aid); KL on the
    # same evening (ARCL ~6.2 deg, moon_alt ~3.9 deg, age ~10 h) passes
    # old-MABIMS (alt/elong branch, and the age>=8 h branch) but not
    # Neo-MABIMS (elongation below 6.4); 2025-03-29 (solar-eclipse new
    # moon) is invisible under every criterion (Yallop F, Odeh D).
    cases = [
        (date(2025, 2, 28), 3.1390, 101.6869, "F", "D", False, True),
        (date(2025, 2, 28), 21.4225, 39.8262, "F", "C", True, True),
        (date(2025, 3, 29), 3.1390, 101.6869, "F", "D", False, False),
        (date(2025, 3, 29), 21.4225, 39.8262, "F", "D", False, False),
    ]
    assert len(cases) == 4
    for day, lat, lon, exp_zone, exp_odeh, exp_neo, exp_old in cases:
        g = crescent_geometry_at_sunset(day, Coordinates(lat, lon))
        zone = yallop_zone(yallop_q(g.arcv_geo_deg, g.width_arcmin))
        odeh = odeh_class(odeh_v(g.arcv_topo_deg, g.width_arcmin), g.arcl_deg)
        moon_alt = g.moon_alt_topo_deg
        neo = is_neo_mabims_2021(moon_alt, g.arcl_deg)
        old = is_mabims_1992(moon_alt, g.arcl_deg, g.moon_age_days * 24.0)
        assert type(neo) is bool
        assert type(old) is bool
        assert math.isfinite(moon_alt)
        assert (zone, odeh, neo, old) == (exp_zone, exp_odeh, exp_neo, exp_old)
