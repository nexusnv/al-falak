from __future__ import annotations

import argparse
import math
from datetime import datetime
from typing import Any

from alfalak import (
    crescent_geometry_at_sunset,
    is_mabims_1992,
    is_neo_mabims_2021,
    odeh_class,
    odeh_v,
    yallop_q,
    yallop_zone,
)
from alfalak.cli.common import add_coord_args, add_json_arg, emit
from alfalak.data.Coordinates import Coordinates
from alfalak.exceptions import AlFalakError


def register(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser(
        "moon-sighting", help="Print crescent visibility scores."
    )
    add_coord_args(parser)
    parser.add_argument(
        "--date",
        required=True,
        help="Crescent evening as YYYY-MM-DD (required; no default).",
    )
    parser.add_argument(
        "--delta-t-override",
        type=float,
        default=None,
        help="Delta-T override in seconds for the TT conversion "
        "(default: built-in polynomial).",
    )
    add_json_arg(parser)
    parser.set_defaults(func=run)


def _json_float(value: float) -> float | None:
    return value if math.isfinite(value) else None


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        try:
            day = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            parser.error(f"invalid --date (expected YYYY-MM-DD): {args.date}")
        try:
            coordinates = Coordinates(args.latitude, args.longitude)
        except AlFalakError as exc:
            parser.error(str(exc))
        geometry = crescent_geometry_at_sunset(
            day, coordinates, delta_t_override=args.delta_t_override
        )
        q = yallop_q(geometry.arcv_geo_deg, geometry.width_arcmin)
        zone = yallop_zone(q)
        v = odeh_v(geometry.arcv_topo_deg, geometry.width_arcmin)
        klass = odeh_class(v, geometry.arcl_deg)
        neo_mabims = is_neo_mabims_2021(geometry.moon_alt_topo_deg, geometry.arcl_deg)
        # No moonset on this civil date: moon_age_at_moonset_days is NaN
        # (see CrescentGeometry). The 1992 age branch is undefined there,
        # so fall back to the altitude/elongation branch (age treated as
        # false) instead of failing. Only NaN takes this path; other
        # non-finite inputs still raise via the predicates below.
        age_hours = geometry.moon_age_at_moonset_days * 24.0
        if math.isnan(age_hours):
            mabims_1992 = geometry.moon_alt_topo_deg >= 2.0 and geometry.arcl_deg >= 3.0
        else:
            mabims_1992 = is_mabims_1992(
                geometry.moon_alt_topo_deg,
                geometry.arcl_deg,
                age_hours,
            )
    except AlFalakError as exc:
        parser.error(str(exc))
    floats: dict[str, float] = {
        "arcl_deg": geometry.arcl_deg,
        "arcv_geo_deg": geometry.arcv_geo_deg,
        "arcv_topo_deg": geometry.arcv_topo_deg,
        "sun_alt_deg": geometry.sun_alt_deg,
        "moon_alt_topo_deg": geometry.moon_alt_topo_deg,
        "daz_deg": geometry.daz_deg,
        "width_arcmin": geometry.width_arcmin,
        "illumination": geometry.illumination,
        "lag_hours": geometry.lag_hours,
        "moon_age_days": geometry.moon_age_days,
        "moon_age_at_moonset_days": geometry.moon_age_at_moonset_days,
        "used_delta_t_s": geometry.used_delta_t_s,
        "sunset_jd_utc": geometry.sunset_jd_utc,
        "yallop_q": q,
        "odeh_v": v,
    }
    if args.json:
        mapping: dict[str, Any] = {
            key: _json_float(value) for key, value in floats.items()
        }
        mapping["yallop_zone"] = zone
        mapping["odeh_class"] = klass
        mapping["neo_mabims"] = neo_mabims
        mapping["mabims_1992"] = mabims_1992
        emit(mapping, True)
        return
    text: dict[str, Any] = {key: repr(value) for key, value in floats.items()}
    text["yallop_zone"] = zone
    text["odeh_class"] = klass
    text["neo_mabims"] = str(neo_mabims).lower()
    text["mabims_1992"] = str(mabims_1992).lower()
    emit(text, False)
