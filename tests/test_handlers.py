import base64
from pathlib import Path

from sensitive_upload_guard.handlers import check_file, check_prompt, handle_binding
from sensitive_upload_guard.scan.detect import MARKER

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _ask_continue(**_kwargs):
    return "continue"


def _ask_cancel(**_kwargs):
    return "cancel"


def test_clean_prompt_no_dialog():
    called = []

    def ask(**kw):
        called.append(kw)
        return "cancel"

    r = check_prompt("hello there", ask=ask)
    assert r["found"] is False
    assert r["decision"] == "continue"
    assert called == []


def test_sensitive_prompt_continue():
    r = check_prompt(f"leak {MARKER} now", ask=_ask_continue)
    assert r["found"] is True
    assert r["decision"] == "continue"
    assert MARKER in r["detail"]


def test_sensitive_prompt_cancel():
    r = check_prompt(f"leak {MARKER} now", ask=_ask_cancel)
    assert r["found"] is True
    assert r["decision"] == "cancel"


def test_sensitive_txt_file_cancel():
    data = (FIXTURES / "sensitive.txt").read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    r = check_file("sensitive.txt", "text/plain", b64, ask=_ask_cancel)
    assert r["found"] is True
    assert r["decision"] == "cancel"
    assert r["detail"] == "sensitive.txt"


def test_clean_txt_file_no_dialog():
    data = (FIXTURES / "clean.txt").read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    called = []

    def ask(**kw):
        called.append(kw)
        return "cancel"

    r = check_file("clean.txt", "text/plain", b64, ask=ask)
    assert r["found"] is False
    assert r["decision"] == "continue"
    assert called == []


def test_binding_ping():
    r = handle_binding({"kind": "ping"})
    assert r["ok"] is True
    assert r["pong"] is True
    assert r["marker"] == MARKER
