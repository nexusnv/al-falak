import argparse
import sys

from alfalak.cli import register_all

_NO_COMMAND_HINT = (
    "a subcommand is required as the first argument "
    "(did you mean 'prayer'? try: al-falak prayer "
    "--latitude 35.7750 --longitude -78.6336)"
)


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
    raw = sys.argv[1:] if argv is None else argv
    if not raw or (raw[0].startswith("-") and raw[0] not in ("-h", "--help")):
        parser.error(_NO_COMMAND_HINT)
    args = parser.parse_args(argv)

    if args.command is None:
        parser.error(_NO_COMMAND_HINT)
    func = getattr(args, "func", None)
    if func is None:
        parser.error(_NO_COMMAND_HINT)
    func(args, parser)


if __name__ == "__main__":
    main()
