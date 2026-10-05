"""Tests for MabimsCalendar (Neo-MABIMS 2021, per-country) (phase-5 task 3)."""

import importlib
from datetime import date

import pytest

from alfalak.astronomy.CrescentGeometry import crescent_geometry_at_sunset
from alfalak.astronomy.Mabims import is_mabims_1992, is_neo_mabims_2021
from alfalak.calendar import MabimsCalendar, get_calendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import (
    AstronomicalError,
    ConfigurationError,
    ValidationError,
)

mabims_module = importlib.import_module("alfalak.calendar.MabimsCalendar")

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


def test_mabims_pre_anchor_raises_deferred() -> None:
    # The walk is forward-only from the 1445-01 anchor (mirror UQU's 1423H
    # epoch): a backward single-probe rule cannot reconstruct the true 29th
    # evening (visible 30th eve vs visible 29th eve are indistinguishable),
    # so pre-anchor inputs raise instead of returning a wrong date.
    cal = MabimsCalendar(country="MY")
    with pytest.raises(ValidationError, match="post-1445"):
        cal.month_length(1444, 12)
    with pytest.raises(ValidationError, match="post-1445"):
        cal.to_gregorian(HijriDate(1444, 12, 15))
    with pytest.raises(ValidationError, match="post-1445"):
        cal.from_gregorian(date(2023, 7, 18))
    # Anchor boundary itself resolves.
    assert cal.month_length(1445, 1) == 30
    assert cal.from_gregorian(date(2023, 7, 19)) == HijriDate(1445, 1, 1)


def test_mabims_far_target_iterative_walk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Beyond the 500-month cached headroom the driver walks iteratively
    # forward from the anchor. The leaf rule is stubbed to isolate the
    # driver's iteration/bounding logic (real lunar geometry is covered by
    # the golden, round-trip, and guard tests); each stubbed month is
    # 30 days, so a 502-month walk lands exactly 502*30 days out.
    # Pre-anchor far targets raise the deferred ValidationError.
    anchor = date(2023, 7, 19).toordinal()  # 1 Muharram 1445H observed.
    monkeypatch.setattr(mabims_module, "_forward_month_length", lambda s, c: 30)
    assert mabims_module.resolve_month_start("MY", 1486, 11) == anchor + 502 * 30
    with pytest.raises(ValidationError, match="post-1445"):
        mabims_module.resolve_month_start("MY", 1403, 3)


def test_mabims_month_start_ordinal_rejects_pre_anchor() -> None:
    # Defense in depth: the cached ordinal lookup itself refuses pre-1445H
    # months even though every public caller validates first.
    with pytest.raises(ValidationError, match="post-1445"):
        mabims_module._month_start_ordinal("MY", 1444, 12)


def test_mabims_from_gregorian_skips_pre_anchor_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A stale tabular seed still in Muharram for a 1 Safar 1445 target
    # (2023-08-18 observed): the offset-0 probe misses, the -1 probe
    # crosses the anchor and is skipped, and the +1 probe lands on day 1.
    safar_start = date.fromordinal(mabims_module.resolve_month_start("MY", 1445, 2))
    assert safar_start == date(2023, 8, 18)
    real_seed = mabims_module._TABULAR_SEED

    class _StaleSeed:
        def from_gregorian(self, d: date) -> HijriDate:
            return HijriDate(1445, 1, 15)

        def to_gregorian(self, h: HijriDate) -> date:
            return real_seed.to_gregorian(h)

    monkeypatch.setattr(mabims_module, "_TABULAR_SEED", _StaleSeed())
    assert MabimsCalendar(country="MY").from_gregorian(safar_start) == HijriDate(
        1445, 2, 1
    )


def test_mabims_clear_cache_is_transparent() -> None:
    cal = MabimsCalendar(country="ID")
    before = cal.month_length(1446, 9)
    mabims_module.clear_mabims_cache()
    assert cal.month_length(1446, 9) == before


def test_mabims_month_length_rejects_bad_inputs() -> None:
    cal = MabimsCalendar(country="MY")
    with pytest.raises(ValidationError):
        cal.month_length("1446", 9)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(1446, "9")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(True, 9)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(1446, False)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.month_length(0, 1)
    with pytest.raises(ValidationError):
        cal.month_length(1446, 0)
    with pytest.raises(ValidationError):
        cal.month_length(1446, 13)


def test_mabims_converters_reject_wrong_types() -> None:
    cal = MabimsCalendar(country="MY")
    with pytest.raises(ValidationError):
        cal.from_gregorian("2025-03-01")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        cal.to_gregorian("1446-09-01")  # type: ignore[arg-type]


def test_mabims_to_gregorian_rejects_30th_of_29_day_month() -> None:
    cal = MabimsCalendar(country="MY")
    assert cal.month_length(1446, 3) == 29
    with pytest.raises(ValidationError):
        cal.to_gregorian(HijriDate(1446, 3, 30))


def test_mabims_impossible_month_length_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A 28-day resolved month trips the 29-or-30 defense (synthetic probe:
    # the Neo-MABIMS rule itself only ever yields 29/30).
    start = date(2025, 3, 1).toordinal()

    def spoofed(country: str, year: int, month: int) -> int:
        return start if (year, month) == (1446, 9) else start + 28

    monkeypatch.setattr(mabims_module, "resolve_month_start", spoofed)
    with pytest.raises(AstronomicalError, match="expected 29 or 30"):
        MabimsCalendar(country="MY").month_length(1446, 9)


def test_mabims_from_gregorian_bounded_probe_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No probed month contains the target (synthetic frozen resolver): the
    # bounded probe fails loudly instead of widening silently.
    frozen = date(2020, 1, 1).toordinal()
    monkeypatch.setattr(mabims_module, "resolve_month_start", lambda c, y, m: frozen)
    with pytest.raises(AstronomicalError, match="no Hijri month contains"):
        MabimsCalendar(country="MY").from_gregorian(date(2025, 3, 1))
