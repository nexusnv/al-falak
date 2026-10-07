"""Subcommand registrars for the al-falak CLI (stdlib only)."""

from typing import Any

from alfalak.cli import hijri, prayer, qibla

__all__ = ["register_all"]


def register_all(subparsers: Any) -> None:
    prayer.register(subparsers)
    qibla.register(subparsers)
    hijri.register(subparsers)
