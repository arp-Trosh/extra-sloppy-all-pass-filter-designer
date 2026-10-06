# SPDX-License-Identifier: GPL-3.0-only
"""Command-line entry point."""

import argparse

from esapf import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="esapf", description="Extra Sloppy All Pass Filter Designer"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
