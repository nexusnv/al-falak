"""Subcommand registrars for the al-falak CLI (stdlib only)."""

from typing import Any

from alfalak.cli import astro, hijri, moon_sighting, prayer, qibla, sunnah

__all__ = ["register_all"]


def register_all(subparsers: Any) -> None:
    prayer.register(subparsers)
    qibla.register(subparsers)
    sunnah.register(subparsers)
    hijri.register(subparsers)
    moon_sighting.register(subparsers)
    astro.register(subparsers)
