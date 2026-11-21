from native_host.host import handle


def test_ping():
    r = handle({"op": "ping", "id": "1"})
    assert r["ok"] is True
    assert r["pong"] is True
    assert r["marker"] == "WALLED_SENSITIVE"


def test_clean_prompt_auto_continues():
    r = handle({"op": "check_prompt", "id": "2", "text": "hello there"})
    assert r["found"] is False
    assert r["decision"] == "continue"
