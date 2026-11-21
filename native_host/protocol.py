"""Chrome/Firefox native messaging framing (length-prefixed JSON)."""

from __future__ import annotations

import json
import struct
import sys
from typing import Any


def read_message() -> dict[str, Any] | None:
    raw_len = sys.stdin.buffer.read(4)
    if not raw_len or len(raw_len) < 4:
        return None
    (length,) = struct.unpack("<I", raw_len)
    if length == 0 or length > 64 * 1024 * 1024:
        return None
    data = sys.stdin.buffer.read(length)
    if len(data) < length:
        return None
    return json.loads(data.decode("utf-8"))


def send_message(msg: dict[str, Any]) -> None:
    encoded = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()
