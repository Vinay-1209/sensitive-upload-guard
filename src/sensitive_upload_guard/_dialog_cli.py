#!/usr/bin/env python3
"""CLI entry used to show a dialog in a clean GUI subprocess."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--detail", default="")
    parser.add_argument("--filename", default=None)
    parser.add_argument("--error", default=None)
    args = parser.parse_args()

    from sensitive_upload_guard.dialog import _ensure_display, _show

    _ensure_display()
    decision = _show(
        source=args.source,
        detail=args.detail,
        filename=args.filename,
        error=args.error,
    )
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
