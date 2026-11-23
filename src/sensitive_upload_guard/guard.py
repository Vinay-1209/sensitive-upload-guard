"""Playwright worker: launch browser, inject gate, bridge page ↔ handlers."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sensitive_upload_guard.handlers import handle_binding

logger = logging.getLogger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent
GATE_JS = PACKAGE_DIR / "web" / "gate.js"
DEFAULT_PROFILE = Path.home() / ".local" / "share" / "sensitive-upload-guard" / "profile"

EventCb = Callable[[str], None]


class Guard:
    """Owns an asyncio loop on a background thread."""

    def __init__(
        self,
        *,
        profile_dir: Path | None = None,
        on_event: EventCb | None = None,
        ask: Callable[..., Any] | None = None,
    ) -> None:
        self.profile_dir = profile_dir or DEFAULT_PROFILE
        self.on_event = on_event or (lambda _msg: None)
        self._ask = ask
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ctx = None
        self._lock = asyncio.Lock()
        self._started = threading.Event()
        self._error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._error = None
        self._started.clear()
        self._thread = threading.Thread(target=self._run_thread, name="sug-guard", daemon=True)
        self._thread.start()
        if not self._started.wait(timeout=60):
            raise RuntimeError(self._error or "browser failed to start")
        if self._error:
            raise RuntimeError(self._error)

    def stop(self) -> None:
        loop = self._loop
        if loop and loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self._shutdown(), loop)
            try:
                fut.result(timeout=15)
            except Exception as exc:
                logger.warning("shutdown: %s", exc)
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None
        self._loop = None
        self._ctx = None

    def open_site(self, url: str) -> None:
        loop = self._loop
        if not loop:
            raise RuntimeError("guard not started")
        asyncio.run_coroutine_threadsafe(self._open(url), loop)

    def _emit(self, msg: str) -> None:
        try:
            self.on_event(msg)
        except Exception:
            logger.exception("on_event failed")

    def _run_thread(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._start_browser())
            self._started.set()
            loop.run_forever()
        except Exception as exc:
            self._error = str(exc)
            logger.exception("guard thread failed")
            self._started.set()
        finally:
            try:
                loop.run_until_complete(self._shutdown())
            except Exception:
                pass
            loop.close()

    async def _start_browser(self) -> None:
        from playwright.async_api import async_playwright

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        gate_source = GATE_JS.read_text(encoding="utf-8")
        pw = await async_playwright().start()
        self._pw = pw

        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(self.profile_dir),
            "headless": False,
            "ignore_default_args": ["--enable-automation"],
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--start-maximized",
            ],
            "viewport": None,  # allow maximized window
            "chromium_sandbox": True,
        }

        try:
            ctx = await pw.chromium.launch_persistent_context(
                channel="chrome", **launch_kwargs
            )
            self._emit("Launched Google Chrome (no extensions).")
        except Exception as exc:
            self._emit(f"Chrome channel unavailable ({exc}); using Chromium.")
            launch_kwargs.pop("ignore_default_args", None)
            ctx = await pw.chromium.launch_persistent_context(**launch_kwargs)

        self._ctx = ctx
        await ctx.expose_binding("__sug_check", self._on_binding)
        await ctx.add_init_script(gate_source)

        # Re-inject on already-open about:blank pages after binding is ready.
        for page in ctx.pages:
            try:
                await page.add_init_script(gate_source)
            except Exception:
                pass

        ctx.on("close", lambda: self._emit("Browser closed."))
        self._emit("Guard ready. Open ChatGPT or Perplexity from the app.")

    async def _on_binding(self, source: Any, payload: Any) -> dict[str, Any]:
        async with self._lock:
            data = payload if isinstance(payload, dict) else {}
            ask_kw = {"ask": self._ask} if self._ask is not None else {}

            def run() -> dict[str, Any]:
                return handle_binding(data, **ask_kw)

            result = await asyncio.to_thread(run)
            kind = data.get("kind")
            if kind in ("check_prompt", "check_file") and result.get("found"):
                detail = result.get("detail") or ""
                decision = result.get("decision")
                src = result.get("source") or kind
                self._emit(f"{src}: {decision} — {detail[:80]}")
            return result

    async def _open(self, url: str) -> None:
        ctx = self._ctx
        if not ctx:
            return
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.bring_to_front()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self._emit(f"Opened {url}")

    async def _shutdown(self) -> None:
        ctx = self._ctx
        self._ctx = None
        if ctx:
            try:
                await ctx.close()
            except Exception:
                pass
        pw = getattr(self, "_pw", None)
        if pw:
            try:
                await pw.stop()
            except Exception:
                pass
        loop = self._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
