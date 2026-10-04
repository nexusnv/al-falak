from datetime import date

from alfalak.astronomy.CrescentGeometry import crescent_geometry_at_sunset
from alfalak.astronomy.Mabims import is_mabims_1992, is_neo_mabims_2021
from alfalak.astronomy.Odeh import odeh_class, odeh_v
from alfalak.astronomy.Yallop import yallop_q, yallop_zone
from alfalak.data.Coordinates import Coordinates


def test_neo_needs_both_thresholds():
    assert is_neo_mabims_2021(4.0, 7.0) is True
    assert is_neo_mabims_2021(2.9, 7.0) is False
    assert is_neo_mabims_2021(4.0, 6.3) is False


def test_old_rule_age_or_branch():
    assert is_mabims_1992(2.5, 3.5, 2.0) is True
    assert is_mabims_1992(1.0, 1.0, 9.0) is True
    assert is_mabims_1992(1.0, 1.0, 2.0) is False


def test_criteria_agreement_matrix():
    rows = []
    for day in (date(2025, 2, 28), date(2025, 3, 29)):
        for lat, lon in ((3.1390, 101.6869), (21.4225, 39.8262)):
            g = crescent_geometry_at_sunset(day, Coordinates(lat, lon))
            rows.append(
                (
                    yallop_zone(yallop_q(g.arcv_geo_deg, g.width_arcmin)),
                    odeh_class(odeh_v(g.arcv_topo_deg, g.width_arcmin), g.arcl_deg),
                )
            )
    assert len(rows) == 4
