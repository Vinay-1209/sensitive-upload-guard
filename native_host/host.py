#!/usr/bin/env python3
"""Native messaging host for Sensitive Upload Guard."""

from __future__ import annotations

import base64
import logging
import sys
from pathlib import Path

# Allow running as script: add repo root to path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from native_host.dialog import ask_user
from native_host.protocol import read_message, send_message
from native_host.scan.detect import MARKER, scan_bytes, scan_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [sug-host] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("sug-host")


def handle(msg: dict) -> dict:
    op = msg.get("op")
    req_id = msg.get("id")

    if op == "ping":
        return {"id": req_id, "ok": True, "pong": True, "marker": MARKER}

    if op == "check_prompt":
        text = msg.get("text") or ""
        result = scan_text(text, source="prompt")
        if not result.found:
            return {
                "id": req_id,
                "ok": True,
                "found": False,
                "decision": "continue",
            }
        decision = ask_user(
            source="prompt",
            detail=result.detail,
            error=result.error,
        )
        return {
            "id": req_id,
            "ok": True,
            "found": True,
            "decision": decision,
            "source": "prompt",
            "detail": result.detail,
        }

    if op == "check_file":
        filename = msg.get("filename") or "upload"
        mime = msg.get("mime") or ""
        b64 = msg.get("data_base64") or ""
        try:
            data = base64.b64decode(b64, validate=False)
        except Exception as exc:
            decision = ask_user(
                source="file",
                detail=filename,
                filename=filename,
                error=f"Could not decode file ({exc})",
            )
            return {
                "id": req_id,
                "ok": True,
                "found": True,
                "decision": decision,
                "source": "file",
                "detail": filename,
            }

        result = scan_bytes(data, filename, mime)
        if not result.found:
            return {
                "id": req_id,
                "ok": True,
                "found": False,
                "decision": "continue",
            }
        decision = ask_user(
            source="file",
            detail=result.detail or filename,
            filename=filename,
            error=result.error,
        )
        return {
            "id": req_id,
            "ok": True,
            "found": True,
            "decision": decision,
            "source": "file",
            "detail": filename,
        }

    return {"id": req_id, "ok": False, "error": f"unknown op: {op}"}


def main() -> None:
    logger.info("Sensitive Upload Guard native host started")
    while True:
        msg = read_message()
        if msg is None:
            break
        try:
            reply = handle(msg)
        except Exception as exc:
            logger.exception("handler error")
            reply = {"id": msg.get("id"), "ok": False, "error": str(exc), "decision": "cancel"}
        send_message(reply)
    logger.info("native host exiting")


if __name__ == "__main__":
    main()
