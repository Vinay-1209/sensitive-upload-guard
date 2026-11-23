"""End-to-end gate against the local HTML harness (no live AI sites)."""

from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from sensitive_upload_guard.handlers import handle_binding
from sensitive_upload_guard.guard import GATE_JS

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "testharness"


@pytest.fixture(scope="module")
def harness_url():
    handler = partial(SimpleHTTPRequestHandler, directory=str(HARNESS))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}/"
    server.shutdown()


@pytest.mark.asyncio
async def test_harness_clean_and_sensitive_prompt(harness_url):
    decisions = {"next": "cancel"}

    def ask(**_kw):
        return decisions["next"]

    async def binding(_source, payload):
        return handle_binding(payload if isinstance(payload, dict) else {}, ask=ask)

    gate = GATE_JS.read_text(encoding="utf-8")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.expose_binding("__sug_check", binding)
        await context.add_init_script(gate)
        page = await context.new_page()
        await page.goto(harness_url, wait_until="domcontentloaded")

        # Badge present
        await page.wait_for_selector("#sug-active-badge", timeout=5000)

        # Assistant painted
        color = await page.eval_on_selector(
            "#assistant",
            "el => getComputedStyle(el).color",
        )
        assert "rgb(11, 110, 79)" in color or "11, 110, 79" in color

        # Clean prompt — page handler should receive send
        await page.fill("#composer", "hello clean world")
        await page.click("#send-btn")
        await page.wait_for_function(
            "() => document.getElementById('log').innerText.includes('PAGE received send')"
        )

        # Sensitive + Cancel — page must NOT get another send
        decisions["next"] = "cancel"
        await page.fill("#composer", "WALLED_SENSITIVE blocked")
        sends_before = await page.eval_on_selector(
            "#log",
            "el => (el.innerText.match(/PAGE received send/g) || []).length",
        )
        await page.click("#send-btn")
        await page.wait_for_timeout(1000)
        sends_after_cancel = await page.eval_on_selector(
            "#log",
            "el => (el.innerText.match(/PAGE received send/g) || []).length",
        )
        assert sends_after_cancel == sends_before

        # Sensitive + Continue — page receives send unchanged
        decisions["next"] = "continue"
        await page.fill("#composer", "WALLED_SENSITIVE allowed")
        await page.click("#send-btn")
        await page.wait_for_function(
            "() => document.getElementById('log').innerText.includes('WALLED_SENSITIVE allowed')"
        )

        await browser.close()
