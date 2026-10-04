from alfalak.astronomy.Yallop import yallop_q, yallop_zone


def test_yallop_zone_boundaries():
    assert yallop_zone(0.3) == "A"
    assert yallop_zone(0.216) == "B"
    assert yallop_zone(0.0) == "B"
    assert yallop_zone(-0.014) == "C"
    assert yallop_zone(-0.16) == "D"
    assert yallop_zone(-0.232) == "E"
    assert yallop_zone(-0.293) == "F"
    assert yallop_zone(-1.0) == "F"


def test_yallop_q_sign():
    assert yallop_q(10.0, 0.5) > yallop_q(2.0, 0.05)
