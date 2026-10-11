from __future__ import annotations

import argparse
from typing import Any

from alfalak import Qibla
from alfalak.cli.common import (
    add_city_args,
    add_coord_args,
    add_json_arg,
    emit,
    resolve_location,
)
from alfalak.exceptions import AlFalakError


def register(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("qibla", help="Print Qibla direction.")
    add_coord_args(parser)
    add_city_args(parser)
    parser.add_argument(
        "--method",
        default="spherical",
        choices=["spherical", "ellipsoidal"],
        help="Earth model: spherical trigonometry (default) or "
        "WGS84 ellipsoidal geodesic.",
    )
    parser.add_argument(
        "--declination",
        type=float,
        default=None,
        help="Local magnetic declination in degrees, positive east of true "
        "north (negative west); prints the compass heading as magnetic=.",
    )
    add_json_arg(parser)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        coordinates, _tz = resolve_location(
            city=getattr(args, "city", None),
            lat=args.latitude,
            lon=args.longitude,
            timezone_raw=None,
            parser=parser,
        )
        qibla = Qibla(coordinates, method=args.method)
        magnetic = (
            None
            if args.declination is None
            else qibla.magnetic_direction(args.declination)
        )
    except AlFalakError as exc:
        parser.error(str(exc))
    if args.json:
        mapping: dict[str, Any] = {
            "direction": qibla.direction,
            "distance_km": qibla.distance_to_makkah_km,
            "method": qibla.method,
        }
        if magnetic is not None:
            mapping["magnetic"] = magnetic
        emit(mapping, True)
        return
    text: dict[str, Any] = {
        "direction": f"{qibla.direction:.6f}",
        "distance_km": f"{qibla.distance_to_makkah_km:.3f}",
        "method": qibla.method,
    }
    if magnetic is not None:
        text["magnetic"] = f"{magnetic:.6f}"
    emit(text, False)
