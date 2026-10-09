# tests/test_cli_hijri.py
import pytest
from alfalak.__main__ import main


def test_hijri_reverse(capsys):
    main(["hijri", "--reverse", "1446-09-01", "--calendar", "tabular"])
    assert capsys.readouterr().out == (
        "gregorian=2025-03-01\ncalendar=tabular\n"
    )


def test_hijri_month_length(capsys):
    main(["hijri", "--month-length", "1446-09", "--calendar", "tabular"])
    assert capsys.readouterr().out == "days=30\ncalendar=tabular\n"


def test_hijri_reverse_rejects_forward_flags(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--reverse", "1446-09-01", "--calendar", "tabular",
              "--date", "2025-03-01"])
    assert excinfo.value.code == 2
    assert "--date" in capsys.readouterr().err


def test_hijri_reverse_bad_date_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--reverse", "1446-13-01", "--calendar", "tabular"])
    assert excinfo.value.code == 2
    assert "--reverse" in capsys.readouterr().err


def test_hijri_reverse_day_beyond_month_length_rejected(capsys):
    # Safar 1446 is 29 days on the tabular calendar.
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--reverse", "1446-02-30", "--calendar", "tabular"])
    assert excinfo.value.code == 2
    assert "--reverse" in capsys.readouterr().err


def test_hijri_month_length_bad_month_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["hijri", "--month-length", "1446-13", "--calendar", "tabular"])
    assert excinfo.value.code == 2
    assert "--month-length" in capsys.readouterr().err


def test_hijri_reverse_and_month_length_mutually_exclusive(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "hijri",
                "--reverse",
                "1446-09-01",
                "--month-length",
                "1446-09",
                "--calendar",
                "tabular",
            ]
        )
    assert excinfo.value.code == 2
    assert "mutually exclusive" in capsys.readouterr().err


def test_hijri_reverse_single_digit_month_accepted(capsys):
    main(["hijri", "--reverse", "1446-9-01", "--calendar", "tabular"])
    assert capsys.readouterr().out == ("gregorian=2025-03-01\ncalendar=tabular\n")


def test_hijri_month_length_single_digit_accepted(capsys):
    main(["hijri", "--month-length", "1446-9", "--calendar", "tabular"])
    assert capsys.readouterr().out == "days=30\ncalendar=tabular\n"


def test_hijri_reverse_with_adjustment_days_allowed(capsys):
    main(
        [
            "hijri",
            "--reverse",
            "1446-09-01",
            "--calendar",
            "tabular",
            "--adjustment-days",
            "1",
        ]
    )
    assert capsys.readouterr().out == ("gregorian=2025-02-28\ncalendar=tabular\n")


def test_hijri_reverse_huge_year_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "hijri",
                "--reverse",
                "99999999999999999999-01-01",
                "--calendar",
                "tabular",
            ]
        )
    assert excinfo.value.code == 2
    assert "--reverse" in capsys.readouterr().err


def test_hijri_month_length_with_adjustment_days_rejected(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "hijri",
                "--month-length",
                "1446-09",
                "--calendar",
                "tabular",
                "--adjustment-days",
                "1",
            ]
        )
    assert excinfo.value.code == 2
    assert "--adjustment-days" in capsys.readouterr().err
