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
