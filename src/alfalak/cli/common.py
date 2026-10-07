"""Shared parsing, builders, and emitters for the al-falak CLI."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from alfalak import CalculationMethod, PrayerTimes
from alfalak.calculation.CalculationParameters import CalculationParameters
from alfalak.calculation.HighLatitudeRule import HighLatitudeRule
from alfalak.calculation.Madhab import Madhab
from alfalak.calculation.PolarCircleRule import PolarCircleRule
from alfalak.calculation.PrayerAdjustments import PrayerAdjustments
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AlFalakError

_ADJUST_RE = re.compile(
    r"^(imsak|fajr|sunrise|dhuhr|asr|maghrib|isha|ishraq|dhuha)=(-?\d+)$"
)
_PRAYER_KEYS = (
    "imsak",
    "fajr",
    "sunrise",
    "syuruk",
    "ishraq",
    "dhuha",
    "dhuhr",
    "asr",
    "maghrib",
    "isha",
)


def add_coord_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--latitude", "--lat", type=float, required=True)
    parser.add_argument("--longitude", "--lon", type=float, required=True)


def add_date_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--date",
        default=None,
        help="Calendar date as YYYY-MM-DD (defaults to today, UTC).",
    )


def add_json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one compact JSON object instead of key=value lines.",
    )


def add_prayer_args(parser: argparse.ArgumentParser) -> None:
    add_coord_args(parser)
    add_date_arg(parser)
    parser.add_argument(
        "--method",
        default=CalculationMethod.MUSLIM_WORLD_LEAGUE.name,
        choices=sorted(m.name for m in CalculationMethod),
    )
    parser.add_argument("--madhab", default="SHAFI", choices=["SHAFI", "HANAFI"])
    parser.add_argument(
        "--high-latitude-rule",
        default="MIDDLE_OF_THE_NIGHT",
        choices=[r.name for r in HighLatitudeRule],
    )
    parser.add_argument(
        "--polar-rule",
        default="NEAREST_LATITUDE",
        choices=[r.name for r in PolarCircleRule],
    )
    parser.add_argument("--fajr-angle", type=float, default=None)
    parser.add_argument("--isha-angle", type=float, default=None)
    parser.add_argument("--isha-interval", type=int, default=None)
    parser.add_argument("--imsak-offset", type=int, default=10)
    parser.add_argument("--ishraq-offset", type=int, default=15)
    parser.add_argument("--dhuha-offset", type=int, default=28)
    parser.add_argument("--elevation", type=float, default=0.0)
    parser.add_argument("--ramadan", action="store_true")
    parser.add_argument("--timezone", default=None)
    parser.add_argument("--adjust", action="append", default=[], metavar="NAME=MIN")


def parse_date(raw: str | None, parser: argparse.ArgumentParser) -> datetime:
    if raw is None:
        return datetime.now(timezone.utc)
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        parser.error(f"invalid --date (expected YYYY-MM-DD): {raw}")


def parse_adjustments(
    specs: list[str], parser: argparse.ArgumentParser
) -> PrayerAdjustments:
    adjustments = PrayerAdjustments()
    for spec in specs:
        match = _ADJUST_RE.match(spec)
        if match is None:
            parser.error(
                f"invalid --adjust (expected NAME=MINUTES): {spec} "
                "(NAME in imsak,fajr,sunrise,dhuhr,asr,"
                "maghrib,isha,ishraq,dhuha)"
            )
        setattr(adjustments, match.group(1), int(match.group(2)))
    return adjustments


def parse_timezone(raw: str | None, parser: argparse.ArgumentParser) -> ZoneInfo | None:
    if raw is None:
        return None
    try:
        return ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        parser.error(f"unknown --timezone: {raw}")


def build_prayer_times(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> PrayerTimes:
    params = CalculationParameters(method=CalculationMethod[args.method])
    params.madhab = Madhab[args.madhab]
    params.high_latitude_rule = HighLatitudeRule[args.high_latitude_rule]
    params.polar_circle_rule = PolarCircleRule[args.polar_rule]
    if args.fajr_angle is not None:
        params.fajr_angle = args.fajr_angle
    if args.isha_angle is not None:
        params.isha_angle = args.isha_angle
    if args.isha_interval is not None:
        params.isha_interval = args.isha_interval
    params.imsak_offset = args.imsak_offset
    params.ishraq_offset = args.ishraq_offset
    params.dhuha_offset = args.dhuha_offset
    params.elevation_m = args.elevation
    params.is_ramadan = args.ramadan
    params.adjustments = parse_adjustments(args.adjust, parser)
    try:
        return PrayerTimes(
            Coordinates(args.latitude, args.longitude),
            parse_date(args.date, parser),
            calculation_parameters=params,
            time_zone=parse_timezone(args.timezone, parser),
        )
    except AlFalakError as exc:
        parser.error(str(exc))


def emit(mapping: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(mapping))
    else:
        for key, value in mapping.items():
            print(f"{key}={value}")
