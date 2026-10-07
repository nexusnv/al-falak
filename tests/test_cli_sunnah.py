from alfalak.__main__ import main


def test_sunnah_block(capsys):
    main(
        [
            "sunnah",
            "--latitude",
            "35.7750",
            "--longitude",
            "-78.6336",
            "--date",
            "2015-07-12",
            "--method",
            "NORTH_AMERICA",
        ]
    )
    assert capsys.readouterr().out == (
        "middle_of_the_night=2015-07-13T04:38:00+00:00\n"
        "first_third_of_the_night=2015-07-13T03:16:00+00:00\n"
        "last_third_of_the_night=2015-07-13T05:59:00+00:00\n"
        "tahajjud_start=2015-07-13T05:59:00+00:00\n"
        "tahajjud_end=2015-07-13T08:43:00+00:00\n"
    )


def test_sunnah_fraction_half_equals_middle(capsys):
    main(
        [
            "sunnah",
            "--latitude",
            "35.7750",
            "--longitude",
            "-78.6336",
            "--date",
            "2015-07-12",
            "--method",
            "NORTH_AMERICA",
            "--fraction",
            "0.5",
        ]
    )
    assert capsys.readouterr().out == (
        "night_fraction=2015-07-13T04:38:00+00:00\n"
    )


def test_sunnah_naive_anchor_rejected(capsys):
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "sunnah",
                "--latitude",
                "35.7750",
                "--longitude",
                "-78.6336",
                "--date",
                "2015-07-12",
                "--start",
                "2015-07-13T00:00:00",
            ]
        )
    assert excinfo.value.code == 2
    assert "--start" in capsys.readouterr().err
