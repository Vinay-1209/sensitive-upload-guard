"""Scan + decide for prompts and uploads. Ask callback is injectable for tests."""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from typing import Any

from sensitive_upload_guard.dialog import Decision, ask_user
from sensitive_upload_guard.scan.detect import MARKER, scan_bytes, scan_text

logger = logging.getLogger(__name__)

AskFn = Callable[..., Decision]

# Fail closed on oversized payloads (Playwright binding / memory).
MAX_FILE_BYTES = 50 * 1024 * 1024


def check_prompt(
    text: str,
    *,
    ask: AskFn = ask_user,
) -> dict[str, Any]:
    result = scan_text(text or "", source="prompt")
    if not result.found:
        return {"ok": True, "found": False, "decision": "continue"}

    decision = ask(source="prompt", detail=result.detail, error=result.error)
    return {
        "ok": True,
        "found": True,
        "decision": decision,
        "source": "prompt",
        "detail": result.detail,
    }


def check_file(
    filename: str,
    mime: str,
    data_base64: str,
    *,
    ask: AskFn = ask_user,
) -> dict[str, Any]:
    name = filename or "upload"
    try:
        data = base64.b64decode(data_base64 or "", validate=False)
    except Exception as exc:
        decision = ask(
            source="file",
            detail=name,
            filename=name,
            error=f"Could not decode file ({exc})",
        )
        return {
            "ok": True,
            "found": True,
            "decision": decision,
            "source": "file",
            "detail": name,
        }

    if len(data) > MAX_FILE_BYTES:
        decision = ask(
            source="file",
            detail=name,
            filename=name,
            error=f"File exceeds {MAX_FILE_BYTES // (1024 * 1024)} MB scan limit",
        )
        return {
            "ok": True,
            "found": True,
            "decision": decision,
            "source": "file",
            "detail": name,
        }

    result = scan_bytes(data, name, mime or "")
    if not result.found:
        return {"ok": True, "found": False, "decision": "continue"}

    decision = ask(
        source="file",
        detail=result.detail or name,
        filename=name,
        error=result.error,
    )
    return {
        "ok": True,
        "found": True,
        "decision": decision,
        "source": "file",
        "detail": name,
    }


def handle_binding(payload: dict[str, Any], *, ask: AskFn = ask_user) -> dict[str, Any]:
    """Dispatch page → Python binding calls."""
    kind = (payload or {}).get("kind")
    if kind == "ping":
        return {"ok": True, "pong": True, "marker": MARKER}
    if kind == "check_prompt":
        return check_prompt(str(payload.get("text") or ""), ask=ask)
    if kind == "check_file":
        return check_file(
            str(payload.get("filename") or "upload"),
            str(payload.get("mime") or ""),
            str(payload.get("data_base64") or ""),
            ask=ask,
        )
    return {"ok": False, "found": True, "decision": "cancel", "error": f"unknown kind: {kind}"}
