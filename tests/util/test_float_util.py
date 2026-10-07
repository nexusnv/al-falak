import random

import pytest
import alfalak.util.FloatUtil as FloatUtil

ANGLE_INVARIANT_SEED = 20261002
ANGLE_EDGE_CASES = [
    0.0,
    180.0,
    -180.0,
    360.0,
    -360.0,
    720.0,
    -720.0,
    2592.0,
    -2592.0,
    0.1,
    -0.1,
    359.999,
    -359.999,
    1e6,
    -1e6,
]


@pytest.mark.parametrize(
    "value, max, expected, tolerance",
    [
        (2.0, -5, -3, 1e-5),
        (-4.0, -5.0, -4, 1e-5),
        (-6.0, -5.0, -1, 1e-5),
        (-1.0, 24, 23, 1e-5),
        (1.0, 24.0, 1, 1e-5),
        (49.0, 24, 1, 1e-5),
        (361.0, 360, 1, 1e-5),
        (360.0, 360, 0, 1e-5),
        (259.0, 360, 259, 1e-5),
        (2592.0, 360, 72, 1e-5),
        (360.1, 360, 0.1, 1e-2),
    ],
)
def test_normalize_with_bound(value, max, expected, tolerance):
    assert FloatUtil.normalize_with_bound(value, max) == pytest.approx(
        expected, abs=tolerance
    )


@pytest.mark.parametrize(
    "value, expected",
    [
        (-45.0, 315),
        (361.0, 1),
        (360.0, 0),
        (259.0, 259),
        (2592.0, 72),
    ],
)
def test_unwind_angle(value, expected):
    assert FloatUtil.unwind_angle(value) == pytest.approx(expected, abs=1e-5)


@pytest.mark.parametrize(
    "angle, expected, tolerance",
    [
        (360.0, 0, 1e-6),
        (361.0, 1, 1e-6),
        (1.0, 1, 1e-6),
        (-1.0, -1, 1e-6),
        (-181.0, 179, 1e-6),
        (180.0, 180, 1e-6),
        (359.0, -1, 1e-6),
        (-359.0, 1, 1e-6),
        (1261.0, -179, 1e-6),
        (-360.1, -0.1, 1e-2),
    ],
)
def test_closest_angle(angle, expected, tolerance):
    assert FloatUtil.closest_angle(angle) == pytest.approx(expected, abs=tolerance)


def test_unwind_angle_in_range_and_idempotent():
    rng = random.Random(ANGLE_INVARIANT_SEED)
    values = list(ANGLE_EDGE_CASES) + [
        rng.uniform(-2000, 2000) for _ in range(200)
    ]
    for value in values:
        once = FloatUtil.unwind_angle(value)
        assert 0 <= once < 360
        assert FloatUtil.unwind_angle(once) == pytest.approx(once, abs=1e-9)


def test_closest_angle_in_range():
    rng = random.Random(ANGLE_INVARIANT_SEED + 1)
    values = list(ANGLE_EDGE_CASES) + [
        rng.uniform(-2000, 2000) for _ in range(200)
    ]
    for angle in values:
        assert -180 <= FloatUtil.closest_angle(angle) <= 180


def test_angle_helpers_round_trip_consistent():
    rng = random.Random(ANGLE_INVARIANT_SEED + 2)
    for value in list(ANGLE_EDGE_CASES) + [
        rng.uniform(-2000, 2000) for _ in range(200)
    ]:
        unwound = FloatUtil.unwind_angle(value)
        closest = FloatUtil.closest_angle(value)
        assert 0 <= unwound < 360
        assert -180 <= closest <= 180
        assert FloatUtil.unwind_angle(closest) == pytest.approx(
            unwound, abs=1e-9
        )


def test_require_finite_real_rejects_huge_int_overflow():
    # Huge ints are real and finite but do not fit in a float:
    # float() raises OverflowError, which must surface as ValidationError
    # per the AlFalakError contract, never a bare builtin.
    from alfalak.exceptions import ValidationError

    for bad in (10**1000, -(10**1000)):
        with pytest.raises(ValidationError, match="(?i)finite"):
            FloatUtil.require_finite_real(bad, "value")
