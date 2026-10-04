from alfalak.astronomy.Odeh import odeh_class, odeh_v


def test_odeh_danjon_floor():
    assert odeh_class(10.0, arcl_deg=5.0) == "D"


def test_odeh_class_boundaries():
    assert odeh_class(6.0, 10.0) == "A"
    assert odeh_class(3.0, 10.0) == "B"
    assert odeh_class(0.0, 10.0) == "C"
    assert odeh_class(-2.0, 10.0) == "D"


def test_odeh_v_monotonic():
    assert odeh_v(8.0, 0.4) > odeh_v(3.0, 0.1)
