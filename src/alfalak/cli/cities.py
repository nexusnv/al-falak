"""`cities` discovery command (frozen table listing)."""

from __future__ import annotations

import argparse
import json
from typing import Any

from alfalak.data.Cities import CITY_TABLE


def register(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser(
        "cities",
        help="List the frozen --city lookup table.",
        description=(
            "List the frozen 300-entry city table backing --city "
            '(as "Name,CC" with coords + timezone).'
        ),
    )
    parser.add_argument(
        "--country",
        default=None,
        help="Filter by 2-letter country code (case-insensitive).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON array instead of text blocks.",
    )
    parser.set_defaults(func=run)


def _parse_country(raw: str | None, parser: argparse.ArgumentParser) -> str | None:
    if raw is None:
        return None
    norm = raw.strip().upper()
    if len(norm) != 2 or not norm.isascii() or not norm.isalpha():
        parser.error(f"invalid --country {raw!r} (must be 2 ASCII letters, e.g. MY).")
    return norm


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    wanted = _parse_country(getattr(args, "country", None), parser)
    rows = list(CITY_TABLE.values())
    if wanted is not None:
        rows = [c for c in rows if c.country == wanted]
    rows.sort(key=lambda c: (c.country, c.name.lower()))
    if getattr(args, "json", False):
        payload = [
            {
                "city": f"{c.name},{c.country}",
                "country": c.country,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "timezone": c.timezone,
            }
            for c in rows
        ]
        print(json.dumps(payload))
        return
    if not rows:
        return
    blocks = [
        f"city={c.name},{c.country}\n"
        f"country={c.country}\n"
        f"latitude={c.latitude:.4f}\n"
        f"longitude={c.longitude:.4f}\n"
        f"timezone={c.timezone}"
        for c in rows
    ]
    print("\n\n".join(blocks))
