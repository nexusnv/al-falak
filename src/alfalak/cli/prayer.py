from __future__ import annotations

import argparse
from typing import Any

from alfalak.cli.common import (
    _PRAYER_KEYS,
    add_json_arg,
    add_prayer_args,
    build_prayer_times,
    emit,
)
from alfalak.exceptions import AlFalakError


def register(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("prayer", help="Print prayer times.")
    add_prayer_args(parser)
    add_json_arg(parser)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        prayer_times = build_prayer_times(args, parser)
        emit(
            {key: getattr(prayer_times, key).isoformat() for key in _PRAYER_KEYS},
            args.json,
        )
    except AlFalakError as exc:
        parser.error(str(exc))
