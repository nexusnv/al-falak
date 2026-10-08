from __future__ import annotations

import argparse
import math
from typing import Any

from alfalak import LunarCoordinates, delta_t
from alfalak.cli.common import add_json_arg, emit
from alfalak.exceptions import AlFalakError


def register(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("astro", help="Print lunar position and Delta-T.")
    nested = parser.add_subparsers(
        dest="astro_command", metavar="<astro-command>", required=True
    )
    lunar = nested.add_parser(
        "lunar-position",
        help="Print geocentric Moon position for a Julian Day (TT).",
    )
    lunar.add_argument(
        "--julian-day",
        type=float,
        required=True,
        help="Julian Day in Terrestrial Time (e.g. 2460000.5).",
    )
    add_json_arg(lunar)
    lunar.set_defaults(func=run_lunar)
    delta_t_parser = nested.add_parser(
        "delta-t",
        help="Print Delta-T (TT minus UT1) in seconds for a decimal year.",
    )
    delta_t_parser.add_argument(
        "--year",
        type=float,
        required=True,
        help="Decimal year (e.g. 2025.5).",
    )
    delta_t_parser.add_argument(
        "--override",
        type=float,
        default=None,
        help="Delta-T override in seconds (e.g. an IERS observed value).",
    )
    add_json_arg(delta_t_parser)
    delta_t_parser.set_defaults(func=run_delta_t)


def _json_float(value: float) -> float | None:
    return value if math.isfinite(value) else None


def run_lunar(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        moon = LunarCoordinates(args.julian_day)
    except AlFalakError as exc:
        parser.error(str(exc))
    except (ValueError, OverflowError) as exc:
        parser.error(f"invalid --julian-day {args.julian_day}: {exc}")
    if args.json:
        emit(
            {
                "longitude": _json_float(moon.longitude),
                "latitude": _json_float(moon.latitude),
                "distance_km": _json_float(moon.distance_km),
                "right_ascension": _json_float(moon.right_ascension),
                "declination": _json_float(moon.declination),
            },
            True,
        )
        return
    emit(
        {
            "longitude": repr(moon.longitude),
            "latitude": repr(moon.latitude),
            "distance_km": repr(moon.distance_km),
            "right_ascension": repr(moon.right_ascension),
            "declination": repr(moon.declination),
        },
        False,
    )


def run_delta_t(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        value = delta_t(args.year, args.override)
    except AlFalakError as exc:
        parser.error(str(exc))
    except (ValueError, OverflowError) as exc:
        parser.error(f"invalid --year/--override: {exc}")
    if not math.isfinite(value):
        parser.error(f"invalid --year {args.year}: Delta-T out of range.")
    emit({"delta_t": _json_float(value) if args.json else repr(value)}, args.json)
