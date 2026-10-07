from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from typing import Any, cast

from alfalak.calendar import OffsetStore, get_calendar
from alfalak.calendar.HijriDate import HijriDate
from alfalak.calendar.bridge import gregorian_to_hijri
from alfalak.cli.common import add_json_arg, emit
from alfalak.data import Coordinates
from alfalak.exceptions import AlFalakError, ConfigurationError

_REVERSE_RE = re.compile(r"^(\d{4,})-(\d{2})-(\d{2})$")
_MONTH_LENGTH_RE = re.compile(r"^(\d{4,})-(\d{2})$")


def register(subparsers: argparse._SubParsersAction[Any]) -> None:
    hijri = subparsers.add_parser(
        "hijri",
        help="Convert between Gregorian and Hijri dates.",
        description=(
            "Convert a Gregorian date to a Hijri date on the named calendar. "
            "Prints exactly two lines: hijri=<YYYY-MM-DD> and "
            "calendar=<name>[-<COUNTRY>]. "
            "With --reverse, convert a Hijri date back to a Gregorian date "
            "(prints gregorian=<YYYY-MM-DD> and calendar=<name>). "
            "With --month-length, print the length of a Hijri month "
            "(days=<29|30> and calendar=<name>). "
            "With --json, the same mapping is emitted as one JSON object."
        ),
        epilog=(
            "Umm al-Qura calendar vs prayer preset: --calendar uqu converts dates "
            "under the 1423H Umm al-Qura month-start rule at Makkah; it is not the "
            "UMM_AL_QURA prayer preset (Fajr angle / Isha interval), which only "
            "tunes daily prayer times and never converts dates.\n\n"
            "Tabular caveat: --calendar tabular is arithmetic (Type IIa); tabular "
            "dates routinely differ from observed (sighting-based) months by 1-2 "
            "days and must never be presented as observed dates.\n\n"
            "Time handling: --date and --time are naive wall-clock values treated "
            "as UTC by the conversion bridge; a local wall-clock time misplaces "
            "sunset rollover by the UTC offset."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    hijri.add_argument(
        "--date",
        default=None,
        help="Gregorian date as YYYY-MM-DD (defaults to today, UTC).",
    )
    hijri.add_argument(
        "--calendar",
        required=True,
        choices=["tabular", "uqu", "mabims"],
        help="Hijri calendar rule.",
    )
    hijri.add_argument(
        "--country",
        default=None,
        type=str.upper,
        choices=["MY", "ID", "BN", "SG"],
        help="MABIMS country (required with --calendar mabims; rejected otherwise).",
    )
    hijri.add_argument(
        "--adjustment-days",
        type=int,
        default=0,
        help="Tabular day shift in [-2, 2] (only with --calendar tabular).",
    )
    hijri.add_argument(
        "--sunset-transition",
        action="store_true",
        help="Roll the Hijri day over at Maghrib (requires --lat/--lon/--time).",
    )
    hijri.add_argument(
        "--lat",
        type=float,
        default=None,
        help="Observer latitude for sunset rollover.",
    )
    hijri.add_argument(
        "--lon",
        type=float,
        default=None,
        help="Observer longitude for sunset rollover.",
    )
    hijri.add_argument(
        "--time",
        default=None,
        help="Wall-clock time as HH:MM[:SS] on --date; naive, treated as UTC "
        "(requires --sunset-transition).",
    )
    hijri.add_argument(
        "--offsets",
        default=None,
        help="JSON offset file ({YYYY-MM: shift}) applied last.",
    )
    hijri.add_argument(
        "--reverse",
        default=None,
        help="Hijri date as YYYY-MM-DD; convert back to a Gregorian date.",
    )
    hijri.add_argument(
        "--month-length",
        default=None,
        help="Hijri year-month as YYYY-MM; print the month length (29 or 30).",
    )
    add_json_arg(hijri)
    hijri.set_defaults(func=run)


def _parse_hijri_time(raw: str, parser: argparse.ArgumentParser) -> datetime:
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    parser.error(f"invalid --time (expected HH:MM[:SS]): {raw}")


def _calendar_suffix(args: argparse.Namespace) -> str:
    return (
        f"-{args.country.upper()}"
        if args.calendar == "mabims" and args.country is not None
        else ""
    )


def _run_reverse(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    raw: str = args.reverse
    match = _REVERSE_RE.match(raw)
    if match is None:
        parser.error(f"invalid --reverse (expected YYYY-MM-DD): {raw}")
    try:
        wanted = HijriDate(
            int(match.group(1)), int(match.group(2)), int(match.group(3))
        )
    except AlFalakError as exc:
        parser.error(f"invalid --reverse {raw}: {exc}")
    cal = get_calendar(
        args.calendar, country=args.country, adjustment_days=args.adjustment_days
    )
    try:
        civil = cal.to_gregorian(wanted)
    except AlFalakError as exc:
        parser.error(f"invalid --reverse {raw}: {exc}")
    emit(
        {
            "gregorian": civil.isoformat(),
            "calendar": f"{args.calendar}{_calendar_suffix(args)}",
        },
        args.json,
    )


def _run_month_length(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    raw: str = args.month_length
    match = _MONTH_LENGTH_RE.match(raw)
    if match is None:
        parser.error(f"invalid --month-length (expected YYYY-MM): {raw}")
    year, month = int(match.group(1)), int(match.group(2))
    cal = get_calendar(
        args.calendar, country=args.country, adjustment_days=args.adjustment_days
    )
    try:
        days = cal.month_length(year, month)
    except AlFalakError as exc:
        parser.error(f"invalid --month-length {raw}: {exc}")
    emit(
        {"days": days, "calendar": f"{args.calendar}{_calendar_suffix(args)}"},
        args.json,
    )


def _run_hijri(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    raw_date: str | None = getattr(args, "date", None)
    if raw_date is None:
        civil = datetime.now(timezone.utc).date()
    else:
        try:
            civil = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            parser.error(f"invalid --date (expected YYYY-MM-DD): {raw_date}")

    if args.time is not None and not args.sunset_transition:
        raise ConfigurationError("--time requires --sunset-transition.")
    if args.sunset_transition:
        if args.lat is None or args.lon is None:
            raise ConfigurationError("--sunset-transition requires --lat and --lon.")
        if args.time is None:
            raise ConfigurationError("--sunset-transition requires --time.")
    elif args.lat is not None or args.lon is not None:
        raise ConfigurationError("--lat/--lon require --sunset-transition.")

    if args.time is not None:
        parsed = _parse_hijri_time(args.time, parser)
        # Naive datetime: the bridge treats naive inputs as UTC (see --help).
        moment = datetime(
            civil.year,
            civil.month,
            civil.day,
            parsed.hour,
            parsed.minute,
            parsed.second,
        )
    else:
        moment = datetime(civil.year, civil.month, civil.day)

    cal = get_calendar(
        args.calendar, country=args.country, adjustment_days=args.adjustment_days
    )
    coordinates = None
    if args.sunset_transition:
        lat: float = cast(float, args.lat)
        lon: float = cast(float, args.lon)
        coordinates = Coordinates(lat, lon)
    store = OffsetStore.from_json(args.offsets) if args.offsets is not None else None
    # Maghrib (sunset rollover) uses default CalculationParameters (MWL);
    # method selection is deferred.
    hijri = gregorian_to_hijri(
        moment,
        calendar=cal,
        coordinates=coordinates,
        change_at_sunset=args.sunset_transition,
        offsets=store,
    )
    emit(
        {
            "hijri": hijri.isoformat(),
            "calendar": f"{args.calendar}{_calendar_suffix(args)}",
        },
        args.json,
    )


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        if args.reverse is not None and args.month_length is not None:
            parser.error("--reverse and --month-length are mutually exclusive.")
        if args.reverse is not None or args.month_length is not None:
            active = "--reverse" if args.reverse is not None else "--month-length"
            clashes = []
            if args.date is not None:
                clashes.append("--date")
            if args.sunset_transition:
                clashes.append("--sunset-transition")
            if args.lat is not None:
                clashes.append("--lat")
            if args.lon is not None:
                clashes.append("--lon")
            if args.time is not None:
                clashes.append("--time")
            if args.offsets is not None:
                clashes.append("--offsets")
            if args.adjustment_days != 0:
                clashes.append("--adjustment-days")
            if clashes:
                parser.error(
                    f"{active} is mutually exclusive with " f"{', '.join(clashes)}."
                )
            if args.reverse is not None:
                _run_reverse(args, parser)
            else:
                _run_month_length(args, parser)
            return
        _run_hijri(args, parser)
    except AlFalakError as exc:
        parser.error(str(exc))
