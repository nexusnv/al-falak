import argparse
from datetime import datetime, timezone
from typing import cast

from alfalak import CalculationMethod, Prayer, PrayerTimes
from alfalak.calendar import OffsetStore, get_calendar
from alfalak.calendar.bridge import gregorian_to_hijri
from alfalak.data import Coordinates
from alfalak.exceptions import ConfigurationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="al-falak",
        description="Print prayer times (ISO-8601, UTC) for a location and date.",
    )
    parser.add_argument("--latitude", type=float, required=False, default=None)
    parser.add_argument("--longitude", type=float, required=False, default=None)
    parser.add_argument(
        "--date",
        default=None,
        help="Calendar date as YYYY-MM-DD (defaults to today, UTC).",
    )
    parser.add_argument(
        "--method",
        default=CalculationMethod.MUSLIM_WORLD_LEAGUE.name,
        choices=sorted(method.name for method in CalculationMethod),
        help="Calculation method (default: MUSLIM_WORLD_LEAGUE).",
    )
    subparsers = parser.add_subparsers(dest="command")
    hijri = subparsers.add_parser(
        "hijri",
        help="Convert a Gregorian date to a Hijri date.",
        description=(
            "Convert a Gregorian date to a Hijri date on the named calendar. "
            "Prints exactly two lines: hijri=<YYYY-MM-DD> and "
            "calendar=<name>[-<COUNTRY>]."
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
        # SUPPRESS (not None): this shares dest "date" with the top-level
        # --date, and a plain None default here would clobber a --date
        # passed before the subcommand (silently falling back to today).
        # SUPPRESS leaves the top-level value intact, so `--date X hijri`
        # and `hijri --date X` agree; when both are given the subcommand
        # value wins.
        default=argparse.SUPPRESS,
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
    return parser


def _parse_hijri_time(raw: str, parser: argparse.ArgumentParser) -> datetime:
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    parser.error(f"invalid --time (expected HH:MM[:SS]): {raw}")


def _run_hijri(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    # getattr: with the SUPPRESS default above, "date" may come from the
    # top-level --date, the subcommand --date, or neither (today, UTC).
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
    print(f"hijri={hijri.isoformat()}")
    suffix = (
        f"-{args.country.upper()}"
        if args.calendar == "mabims" and args.country is not None
        else ""
    )
    print(f"calendar={args.calendar}{suffix}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "hijri":
        if args.latitude is not None or args.longitude is not None:
            parser.error(
                "--latitude/--longitude are not used with the hijri "
                "subcommand; pass --lat/--lon with --sunset-transition."
            )
        _run_hijri(args, parser)
        return

    if args.latitude is None or args.longitude is None:
        parser.error("the following arguments are required: --latitude, --longitude")

    if args.date is None:
        date = datetime.now(timezone.utc)
    else:
        try:
            date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            parser.error(f"invalid --date (expected YYYY-MM-DD): {args.date}")

    prayer_times = PrayerTimes(
        Coordinates(args.latitude, args.longitude),
        date,
        calculation_method=CalculationMethod[args.method],
    )
    for prayer in Prayer:
        if prayer != Prayer.NONE:
            print(
                f"{prayer.name.lower()}={prayer_times.time_for_prayer(prayer).isoformat()}"
            )


if __name__ == "__main__":
    main()
