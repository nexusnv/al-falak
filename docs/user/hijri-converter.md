---
title: Hijri Converter
description: Convert Gregorian dates to Hijri dates with tabular, Umm al-Qura, and MABIMS calendars.
---

# Hijri Converter

Convert Gregorian dates to Hijri dates on one of three calendar rules.
All computation is offline and deterministic (standard library only);
observational calendars resolve month starts by walking their rule
forward from a verified anchor.

> Tabular dates routinely differ from observed (sighting-based) months
> by ±1–2 days. Never present a tabular date as an observed date, or
> vice versa.

## Quick start

```python
from datetime import datetime, timezone
from alfalak import get_calendar, gregorian_to_hijri

cal = get_calendar("tabular")
hijri = gregorian_to_hijri(
    datetime(2025, 3, 1, 12, 0, tzinfo=timezone.utc),
    calendar=cal,
)
print(hijri.isoformat())  # 1446-09-01
```

## The three calendars

| Calendar | Key | Rule | Support floor |
|---|---|---|---|
| `TabularCalendar` | `"tabular"` | Arithmetic Type IIa ("Kuwaiti" pattern); unbounded below by 1 Muharram 1 AH (622-07-19 proleptic) | 1 Muharram 1 AH |
| `UmmAlQuraCalendar` | `"uqu"` | 1423H month-start rule evaluated at Makkah (conjunction before Makkah sunset + moonset after sunset → 29-day month, else 30) | Gregorian 2002-03-15 (1 Muharram 1423H) |
| `MabimsCalendar` | `"mabims"` | Neo-MABIMS 2021 evaluated at a per-country proxy (altitude ≥ 3° and elongation ≥ 6.4° → 29-day month, else 30); `country` required (one of `MY`, `ID`, `BN`, `SG`) | 1 Muharram 1445H (2023-07-19) |

```python
from alfalak import get_calendar

uqu = get_calendar("uqu")
my = get_calendar("mabims", country="MY")
```

`country` is required for — and only for — `"mabims"`;
`adjustment_days` (in [-2, 2]) is accepted only by `"tabular"`.
Any other combination raises `ConfigurationError`.

### Tabular adjustments

`TabularCalendar(adjustment_days=N)` shifts the conversion by N days
(same role as .NET's `HijriAdjustment`) for regional tabular corrections:

```python
from alfalak import TabularCalendar
from datetime import date

base = TabularCalendar()
shifted = TabularCalendar(adjustment_days=1)
print(shifted.to_gregorian(base.from_gregorian(date(2025, 3, 1))))
```

### Umm al-Qura vs. the prayer preset

The `UmmAlQuraCalendar` date converter (1423H month-start rule at
Makkah) is not the `UMM_AL_QURA` prayer preset (Fajr angle / Isha
interval), which only tunes daily prayer times and never converts
dates. Earlier Umm al-Qura variants (the 1392H scheme, the 1420–1422H
interim criteria) are out of scope: inputs before 1 Muharram 1423H
raise `ValidationError` instead of returning a wrong date.

### MABIMS proxies

The four country references are national proxies (Kuala Lumpur,
Jakarta, Bandar Seri Begawan, Singapore), not per-zone truth —
Malaysia alone spans 60+ prayer zones and Indonesia spans three time
zones. Official announcements fold in zone observations and actual
sighting reports, so computed dates may differ from announced dates by
±1 day. For example, the KL proxy opens Ramadan 1446H on 2025-03-02
while tabular/UQU give 2025-03-01 — an expected one-day proxy spread,
not a bug:

```python
from datetime import date
from alfalak import get_calendar

witness = date(2025, 3, 1)
print(get_calendar("tabular").from_gregorian(witness))                 # 1446-09-01
print(get_calendar("uqu").from_gregorian(witness))                     # 1446-09-01
print(get_calendar("mabims", country="MY").from_gregorian(witness))    # 1446-08-30
```

The superseded 1992 Labuan rule (altitude ≥ 2° / elongation ≥ 3° / age
≥ 8 h) is not implemented; only Neo-MABIMS 2021 is.

## Converting dates

Calendars speak civil `date`s; the `gregorian_to_hijri` bridge handles
datetimes and the sunset rollover:

```python
from datetime import datetime, timezone
from alfalak import Coordinates, get_calendar, gregorian_to_hijri

kl = Coordinates(3.1390, 101.6869)
cal = get_calendar("mabims", country="MY")

# Civil-date mapping (default): the Hijri day follows the Gregorian date.
daytime = gregorian_to_hijri(
    datetime(2025, 3, 2, 12, 0, tzinfo=timezone.utc),
    calendar=cal,
)
print(daytime.isoformat())  # 1446-09-01

# Sunset mapping: at or after that day's Maghrib belongs to the next Hijri day
# (noon UTC is past Maghrib in Kuala Lumpur, so this rolls over).
evening = gregorian_to_hijri(
    datetime(2025, 3, 2, 12, 0, tzinfo=timezone.utc),
    calendar=cal,
    coordinates=kl,
    change_at_sunset=True,
)
print(evening.isoformat())  # 1446-09-02
```

With `change_at_sunset=True`, `coordinates` is required and Maghrib
comes from `PrayerTimes` with default parameters (pass `params=` to
override). Naive datetimes are treated as UTC — a naive datetime
carrying *local* wall-clock time misplaces the rollover by the UTC
offset, so prefer aware datetimes. A polar `AstronomicalError` from
Maghrib propagates unwrapped.

Round-trips and month lengths go through the calendar directly:

```python
from alfalak import HijriDate

h = HijriDate(1446, 9, 1)
print(cal.to_gregorian(h))        # 2025-03-02: Gregorian date of 1 Ramadan 1446H on this rule
print(cal.month_length(1446, 9))  # 29: Ramadan 1446H has 29 days on the MY proxy rule
```

`HijriDate` is a frozen, ordered value type with zero-padded
`isoformat()`. The constructor enforces day 1–30; each calendar
enforces the exact 29/30-day month length at conversion time.
Calendars reject `datetime` inputs (pass `d.date()` or use the bridge)
so a time component can never be silently dropped.

## Official-correction offsets

`OffsetStore` applies per-month (`"YYYY-MM"` of the *computed* month)
day shifts in {-2, -1, 1, 2}, loaded from a dict or a JSON file, and is
applied last by the bridge:

```python
from alfalak import OffsetStore

store = OffsetStore.from_dict({"1446-09": 1})
store = OffsetStore.from_json("offsets/my-1446.json")  # {"1446-09": 1}

hijri = gregorian_to_hijri(dt, calendar=cal, offsets=store)
```

Shifting is Hijri-day arithmetic on the same calendar's month lengths
(day 30 of a 29-day month rolls into the next month); the shifted
month is never re-looked-up, and `to_gregorian` ignores the store
(offsets are a Gregorian→Hijri display correction only). Zero is
rejected — omit no-op entries instead.

## Accuracy and limitations

- **Tabular vs. observed:** ±1–2 days by design across rules.
- **MABIMS vs. announced:** ±1 day proxy variance on top of that.
- **Observational floors:** pre-floor inputs raise `ValidationError`
  (deferred) rather than returning a wrong date.
- **Knife-edge months:** when conjunction/moonset sits within minutes
  of a threshold, published tables and first-principles computation
  can disagree by a day; known cases are recorded per month in the
  test goldens.
- **Cold-start cost:** observational calendars walk month by month
  from their anchor (modern UQU targets walk from the 1445H anchor,
  not the 1423H epoch); far-future walks cost one geometry evaluation
  per month. See the offline/deterministic ADR below.

## See also

- [API Reference](api-reference/) — full `HijriDate`, calendar, bridge, and `OffsetStore` signatures
- [CLI Usage](cli/) — `hijri` subcommand
- [Moon Sighting](moon-sighting/) — crescent geometry behind the observational rules
- [Errors](errors/) — Hijri error contracts
- [Citations](citations/) — calendar rule sources
