from __future__ import annotations

import argparse
from datetime import datetime
from typing import Any

from alfalak import SunnahTimes
from alfalak.cli.common import (
    add_json_arg,
    add_prayer_args,
    build_prayer_times,
    emit,
)
from alfalak.exceptions import AlFalakError


def register(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("sunnah", help="Print Sunnah night markers.")
    add_prayer_args(parser)
    parser.add_argument(
        "--fraction",
        type=float,
        default=None,
        help="Night fraction in the open interval (0, 1); prints a single "
        "night_fraction= line instead of the default marker block.",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Custom night-start anchor as an ISO datetime with timezone "
        "offset (requires --fraction).",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Custom night-end anchor as an ISO datetime with timezone "
        "offset (requires --fraction).",
    )
    add_json_arg(parser)
    parser.set_defaults(func=run)


def _parse_anchor(
    raw: str | None, flag: str, parser: argparse.ArgumentParser
) -> datetime | None:
    if raw is None:
        return None
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        parser.error(f"invalid {flag} (expected ISO datetime): {raw}")
    if value.tzinfo is None or value.utcoffset() is None:
        parser.error(f"invalid {flag} (must be timezone-aware): {raw}")
    return value


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        prayer_times = build_prayer_times(args, parser)
        sunnah = SunnahTimes(prayer_times)
        start = _parse_anchor(args.start, "--start", parser)
        end = _parse_anchor(args.end, "--end", parser)
        if args.fraction is None:
            if args.start is not None or args.end is not None:
                parser.error("--start/--end require --fraction.")
            tahajjud_start, tahajjud_end = sunnah.tahajjud_window
            emit(
                {
                    "middle_of_the_night": sunnah.middle_of_the_night.isoformat(),
                    "first_third_of_the_night": (
                        sunnah.first_third_of_the_night.isoformat()
                    ),
                    "last_third_of_the_night": sunnah.last_third_of_the_night.isoformat(),
                    "tahajjud_start": tahajjud_start.isoformat(),
                    "tahajjud_end": tahajjud_end.isoformat(),
                },
                args.json,
            )
            return
        emit(
            {
                "night_fraction": sunnah.night_fraction(
                    args.fraction, start=start, end=end
                ).isoformat()
            },
            args.json,
        )
    except AlFalakError as exc:
        parser.error(str(exc))
