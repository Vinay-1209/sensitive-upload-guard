"""CLI entry: `sug` / `python -m sensitive_upload_guard`."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sug",
        description="Sensitive Upload Guard — standalone desktop DLP for ChatGPT and Perplexity",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print version and exit",
    )
    args = parser.parse_args(argv)
    if args.version:
        from sensitive_upload_guard import __version__

        print(__version__)
        return 0

    from sensitive_upload_guard.app import run

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
