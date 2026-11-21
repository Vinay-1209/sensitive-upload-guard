#!/usr/bin/env python3
"""CLI entry used by the host to show a dialog in a clean GUI subprocess."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from native_host.dialog import _ensure_display, _show  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--detail", default="")
    parser.add_argument("--filename", default=None)
    parser.add_argument("--error", default=None)
    args = parser.parse_args()
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
