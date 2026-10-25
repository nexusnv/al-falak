import pytest
from alfalak.calculation.CalculationMethod import CalculationMethod
from alfalak.calculation.CalculationParameters import CalculationParameters
from alfalak.calculation.HighLatitudeRule import HighLatitudeRule
from alfalak.calculation.PrayerAdjustments import PrayerAdjustments
from alfalak.exceptions import ConfigurationError


@pytest.mark.parametrize(
    "calculation_method, fajr_angle, isha_angle, isha_interval",
    [
        (CalculationMethod.MUSLIM_WORLD_LEAGUE, 18, 17, 0),
        (CalculationMethod.EGYPTIAN, 19.5, 17.5, 0),
        (CalculationMethod.KARACHI, 18, 18, 0),
        (CalculationMethod.UMM_AL_QURA, 18.5, 0, 90),
        (CalculationMethod.DUBAI, 18.2, 18.2, 0),
        (CalculationMethod.MOON_SIGHTING_COMMITTEE, 18, 18, 0),
        (CalculationMethod.NORTH_AMERICA, 15, 15, 0),
        (CalculationMethod.KUWAIT, 18, 17.5, 0),
        (CalculationMethod.QATAR, 18, 0, 90),
        (CalculationMethod.SINGAPORE, 20, 18, 0),
        (CalculationMethod.UOIF, 12, 12, 0),
        (CalculationMethod.JAKIM, 18, 18, 0),
    ],
)
def test_calculation_method(calculation_method, fajr_angle, isha_angle, isha_interval):
    # Arrange, Act
    params = CalculationParameters(method=calculation_method)

    # Assert
    assert params.fajr_angle == pytest.approx(fajr_angle, abs=1e-6)
    assert params.isha_angle == pytest.approx(isha_angle, abs=1e-6)
    assert params.isha_interval == isha_interval
    assert params.method == calculation_method


@pytest.mark.parametrize(
    "fajr_angle, isha_angle, latitude_rule, night_portions_fajr, night_portions_isha",
    [
        (18, 18, HighLatitudeRule.MIDDLE_OF_THE_NIGHT, 0.5, 0.5),
        (18.0, 18.0, HighLatitudeRule.SEVENTH_OF_THE_NIGHT, 1.0 / 7.0, 1.0 / 7.0),
        (10.0, 15.0, HighLatitudeRule.TWILIGHT_ANGLE, 10.0 / 60.0, 15.0 / 60.0),
    ],
)
def test_night_portion(
    fajr_angle, isha_angle, latitude_rule, night_portions_fajr, night_portions_isha
):
    # Arrange, Act
    parameters = CalculationParameters(fajr_angle=fajr_angle, isha_angle=isha_angle)
    parameters.high_latitude_rule = latitude_rule

    # Assert
    assert parameters.night_portions().fajr == pytest.approx(
        night_portions_fajr, abs=1e-3
    )
    assert parameters.night_portions().isha == pytest.approx(
        night_portions_isha, abs=1e-3
    )


def test_night_portion_with_invalid_high_latitude_rule():
    # Arrange
    parameters = CalculationParameters(fajr_angle=18, isha_angle=18)
    parameters.high_latitude_rule = None

    # Act, Assert
    with pytest.raises(ConfigurationError, match="Invalid high latitude rule"):
        parameters.night_portions()


def test_method_is_always_set():
    # Arrange
    params_method_none = CalculationParameters(
        method=None, fajr_angle=18, isha_angle=18
    )
    params_no_method = CalculationParameters(fajr_angle=18, isha_angle=18)

    # Act, Assert
    assert params_method_none.method is CalculationMethod.NONE
    assert params_no_method.method is CalculationMethod.NONE


def test_when_method_is_not_other_parameters_are_not_overwritten():
    # Arrange
    params_method_none = CalculationParameters(method=None, fajr_angle=18)
    params_no_method = CalculationParameters(
        fajr_angle=18, isha_angle=18, isha_interval=90
    )

    # Act, Assert
    assert params_method_none.fajr_angle == 18
    assert params_no_method.fajr_angle == 18
    assert params_no_method.isha_angle == 18
    assert params_no_method.isha_interval == 90


def test_method_has_precedence_over_other_parameters():
    # Arrange
    params = CalculationParameters(
        method=CalculationMethod.MOON_SIGHTING_COMMITTEE, fajr_angle=10
    )

    # Act, Assert
    # MOON_SIGHTING_COMMITTEE has a fajr_angle of 18 and should overwrite fajr_angle provided
    assert params.fajr_angle == 18


def test_invalid_method_type_raises():
    with pytest.raises(ConfigurationError, match="(?i)CalculationMethod"):
        CalculationParameters(method="bogus", fajr_angle=18)


def test_method_adjustments_are_independent_between_instances():
    first = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)
    second = CalculationParameters(method=CalculationMethod.MUSLIM_WORLD_LEAGUE)

    assert first.method_adjustments is not second.method_adjustments

    first.method_adjustments.dhuhr = 99

    assert second.method_adjustments.dhuhr == 1
    assert (
        CalculationParameters(
            method=CalculationMethod.MUSLIM_WORLD_LEAGUE
        ).method_adjustments.dhuhr
        == 1
    )


def test_caller_provided_adjustments_are_copied():
    shared = PrayerAdjustments(fajr=2)
    first = CalculationParameters(
        method=CalculationMethod.NORTH_AMERICA, adjustments=shared
    )
    second = CalculationParameters(
        method=CalculationMethod.NORTH_AMERICA, adjustments=shared
    )

    first.adjustments.fajr = 99

    assert second.adjustments.fajr == 2
    assert shared.fajr == 2
