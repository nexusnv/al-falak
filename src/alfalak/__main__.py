import argparse

from alfalak.cli import register_all


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="al-falak",
        description="Islamic astronomy: prayer times, Hijri dates, and more.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<subcommand>")
    register_all(subparsers)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.error(
            "a subcommand is required "
            "(did you mean 'prayer'? "
            "try: al-falak prayer --latitude 35.7750 --longitude -78.6336)"
        )
    args.func(args, parser)


if __name__ == "__main__":
    main()
