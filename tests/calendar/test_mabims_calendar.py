"""Tests for MabimsCalendar (Neo-MABIMS 2021, per-country) (phase-5 task 3)."""

from datetime import date

import pytest

from alfalak.astronomy.CrescentGeometry import crescent_geometry_at_sunset
from alfalak.astronomy.Mabims import is_mabims_1992, is_neo_mabims_2021
from alfalak.calendar import MabimsCalendar, get_calendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import ConfigurationError

# Announced month starts (civil Gregorian dates of Hijri day 1).
# MY sources: Penyimpan Mohor Besar Raja-Raja announcements relayed by
# Astro Awani (12 Mar 2024), TV3/BuletinTV3 (2 Mar 2025, 31 Mar 2025),
# JAKIM "Tarikh-Tarikh Penting Dalam Islam" takwim 2025 (2 Mar / 31 Mar 2025).
# ID sources: Kemenag sidang isbat relayed by setkab.go.id (12 Mar 2024),
# tirto.id (10 Apr 2024), Bisnis.com/detik.com (1 Mar 2025 Ramadan,
# 31 Mar 2025 Syawal; Ramadan 1446 "disempurnakan menjadi 30 hari").
# Tolerance note: the calendar evaluates Neo-MABIMS at a single national
# proxy (Jakarta for ID); official ID dates fold in 30+ rukyat points across
# three time zones plus actual sighting reports, so a +/-1 day delta against
# the announcement is expected physics/practice variance, not a code bug.
# Observed deltas (first run, deterministic): all +0d except ID 1446-09
# (+1d: Jakarta-proxy geometry on 28 Feb 2025 eve is alt +3.88 / elong 6.03
# -> Neo-2021 False -> Sha'ban completes 30 days, while the national isbat
# -- using western stations where the crescent stood higher -- opened
# Ramadan on 1 Mar; cf. "Indonesia Mulai Puasa Lebih Dulu" coverage).
GOLDENS: tuple[tuple[str, int, int, date, str], ...] = (
    ("MY", 1445, 9, date(2024, 3, 12), "Penyimpan Mohor Besar, 12 Mar 2024"),
    ("MY", 1445, 10, date(2024, 4, 10), "Aidilfitri announcement, 10 Apr 2024"),
    ("MY", 1446, 9, date(2025, 3, 2), "Penyimpan Mohor Besar, 2 Mar 2025"),
    ("MY", 1446, 10, date(2025, 3, 31), "JAKIM takwim 2025, 31 Mar 2025"),
    ("ID", 1445, 9, date(2024, 3, 12), "Kemenag isbat, 12 Mar 2024"),
    ("ID", 1445, 10, date(2024, 4, 10), "Kemenag isbat, 10 Apr 2024"),
    ("ID", 1446, 9, date(2025, 3, 1), "Kemenag isbat, 1 Mar 2025"),
    ("ID", 1446, 10, date(2025, 3, 31), "Kemenag isbat, 31 Mar 2025"),
)


def test_mabims_ramadan_syawal_1to2years_deltas_listed() -> None:
    deltas: list[str] = []
    for country, year, month, expected, _source in GOLDENS:
        cal = MabimsCalendar(country=country)
        got = cal.to_gregorian(HijriDate(year, month, 1))
        delta = (got - expected).days
        deltas.append(
            f"{country} {year}-{month:02d}: computed {got} vs "
            f"announced {expected} (delta {delta:+d}d)"
        )
        assert abs(delta) <= 1, f"{country} {year}-{month:02d}: delta {delta}d"
        # Self-consistency is exact even when the announcement delta is not:
        # the computed start converts back to day 1 of the same month.
        assert cal.from_gregorian(got) == HijriDate(year, month, 1)
        assert cal.to_gregorian(cal.from_gregorian(got)) == got
    print("\n" + "\n".join(deltas))


def test_mabims_bad_country_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        get_calendar("mabims")
    with pytest.raises(ConfigurationError):
        get_calendar("mabims", country="XX")
    with pytest.raises(ConfigurationError):
        MabimsCalendar(country="XX")
    with pytest.raises(ConfigurationError):
        MabimsCalendar(country="")
    with pytest.raises(ConfigurationError):
        MabimsCalendar()  # type: ignore[call-arg]
    with pytest.raises(ConfigurationError):
        MabimsCalendar(country=None)  # type: ignore[arg-type]


def test_mabims_case_insensitive() -> None:
    cal = MabimsCalendar(country="my")
    assert cal.country == "MY"
    assert cal.name == "mabims"
    assert get_calendar("mabims", country="my").name == "mabims"
    assert MabimsCalendar(country="Id").country == "ID"


def test_mabims_month_length_29_or_30_full_year_all_refs() -> None:
    for country in ("MY", "ID", "BN", "SG"):
        cal = MabimsCalendar(country=country)
        lengths = [cal.month_length(1446, m) for m in range(1, 13)]
        assert all(length in (29, 30) for length in lengths)
        assert sum(lengths) in (354, 355)
        # Spot round-trips through the year stay self-consistent.
        for sample in (date(2024, 7, 7), date(2024, 12, 1), date(2025, 3, 15)):
            assert cal.to_gregorian(cal.from_gregorian(sample)) == sample


def test_mabims_1992_vs_2021_flip_comment() -> None:
    # Same-eve flip, Kuala Lumpur 2025-02-28 (29th Sha'ban 1446 under the
    # computed MY chain): altitude clears both generations of thresholds
    # but elongation 6.17 sits between the 1992 3-degree and Neo-2021
    # 6.4-degree bars. The 1992 Labuan rule would have ended Sha'ban at
    # 29 days (1 Ramadan = 1 Mar 2025); Neo-MABIMS 2021 completes 30 days
    # (1 Ramadan = 2 Mar 2025, as announced). The old rule is intentionally
    # NOT implemented -- it is recorded here as the superseded predecessor.
    eve = date(2025, 2, 28)
    kl = Coordinates(3.1390, 101.6869)
    geometry = crescent_geometry_at_sunset(eve, kl)
    assert 4.0 <= geometry.moon_alt_topo_deg <= 4.5
    assert 6.0 <= geometry.arcl_deg <= 6.4
    assert (
        is_mabims_1992(
            geometry.moon_alt_topo_deg,
            geometry.arcl_deg,
            geometry.moon_age_at_moonset_days * 24.0,
        )
        is True
    )
    assert is_neo_mabims_2021(geometry.moon_alt_topo_deg, geometry.arcl_deg) is False
