#!/usr/bin/env python3
"""
Record a live desktop-app demo (ChatGPT + Perplexity) via OBS.

Output goes to ~/Videos/sensitive-upload-guard/ (not committed).
Requires: OBS running with websocket on :4455, display session, network.
"""

from __future__ import annotations

import asyncio
import base64
import os
import time
from pathlib import Path

import obsws_python as obs
from playwright.async_api import Page

from sensitive_upload_guard.dialog import ask_user
from sensitive_upload_guard.guard import Guard

OUT = Path.home() / "Videos" / "sensitive-upload-guard"
AUTO = Path("/tmp/sug_demo_auto")
AUTO_MS = Path("/tmp/sug_demo_auto_ms")
OBS_PASSWORD = os.environ.get("OBS_WS_PASSWORD", "5cj18KRbSSIgnkGG")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def set_auto(decision: str, ms: int = 4500) -> None:
    AUTO_MS.write_text(f"{ms}\n", encoding="utf-8")
    AUTO.write_text(decision + "\n", encoding="utf-8")


def clear_auto() -> None:
    for p in (AUTO, AUTO_MS):
        try:
            p.unlink()
        except OSError:
            pass


async def wait_composer(page: Page, timeout_s: float = 45.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        # Dismiss common cookie / consent chips so they don't block input.
        try:
            for label in ("Accept", "Accept all", "Got it", "Agree"):
                loc = page.get_by_role("button", name=label)
                if await loc.count():
                    await loc.first.click(timeout=1000)
                    break
        except Exception:
            pass
        ok = await page.evaluate(
            """() => !!(
              document.querySelector('div.ProseMirror[contenteditable="true"]') ||
              document.querySelector('#prompt-textarea') ||
              document.querySelector('[aria-label*="Ask ChatGPT" i]') ||
              document.querySelector('[role="textbox"][contenteditable="true"]') ||
              document.querySelector('[contenteditable="true"][aria-label*="Ask" i]') ||
              document.querySelector('textarea[placeholder*="Ask" i]') ||
              document.querySelector('#composer') ||
              document.querySelector('textarea')
            )"""
        )
        if ok:
            return
        await asyncio.sleep(0.4)
    raise RuntimeError(f"composer not found on {page.url}")


async def fill_and_send(page: Page, text: str) -> None:
    await wait_composer(page)
    await page.evaluate(
        """() => {
      const el =
        document.querySelector('div.ProseMirror[contenteditable="true"]') ||
        document.querySelector('#prompt-textarea') ||
        document.querySelector('[role="textbox"][contenteditable="true"]') ||
        document.querySelector('[contenteditable="true"][aria-label*="Ask" i]') ||
        document.querySelector('[contenteditable="true"]') ||
        document.querySelector('textarea');
      if (!el) throw new Error('no composer');
      el.focus();
      el.click();
    }"""
    )
    await page.keyboard.press("Control+a")
    await page.keyboard.press("Backspace")
    await page.keyboard.type(text, delay=20)
    await asyncio.sleep(0.8)
    sent = await page.evaluate(
        """() => {
      const sels = [
        "button[data-testid='send-button']",
        "button[aria-label='Send message']",
        "button[aria-label*='Send' i]",
        "button[aria-label*='Submit' i]",
        "#send-btn",
      ];
      for (const s of sels) {
        const b = document.querySelector(s);
        if (b && b.getClientRects().length) { b.click(); return s; }
      }
      return null;
    }"""
    )
    if not sent:
        await page.keyboard.press("Enter")


async def upload_file(page: Page, path: Path) -> None:
    await wait_composer(page)
    inputs = page.locator('input[type="file"]')
    n = await inputs.count()
    if n == 0:
        # try attach button then filechooser
        for sel in (
            'button[aria-label*="Attach" i]',
            'button[aria-label*="Upload" i]',
            'button[aria-label*="plus" i]',
        ):
            btn = page.locator(sel).first
            if await btn.count():
                async with page.expect_file_chooser(timeout=5000) as fc_info:
                    await btn.click()
                fc = await fc_info.value
                await fc.set_files(str(path))
                return
        raise RuntimeError("no file input")
    await inputs.first.set_input_files(str(path))


def drive(guard: Guard) -> None:
    loop = guard._loop
    assert loop and guard._ctx

    async def run() -> None:
        ctx = guard._ctx
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Prove no extension
        await page.goto("chrome://extensions/", wait_until="domcontentloaded")
        await asyncio.sleep(2.5)

        # --- ChatGPT ---
        await page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(3)
        await wait_composer(page, 60)
        await asyncio.sleep(1.5)

        await fill_and_send(page, "Say hello in one short sentence.")
        await asyncio.sleep(7)

        await page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(2)
        await wait_composer(page, 60)
        set_auto("cancel", 4500)
        await fill_and_send(page, "WALLED_SENSITIVE demo: do not send this blocked prompt.")
        await asyncio.sleep(8)

        set_auto("continue", 4500)
        await fill_and_send(page, "WALLED_SENSITIVE demo: continue allowed — reply with just OK.")
        await asyncio.sleep(10)

        # sensitive text upload cancel
        set_auto("cancel", 4500)
        try:
            await upload_file(page, FIXTURES / "sensitive.txt")
            await asyncio.sleep(7)
        except Exception as exc:
            print("chatgpt upload skip:", exc)

        # --- Perplexity ---
        await page.goto("https://www.perplexity.ai/", wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(4)
        try:
            await wait_composer(page, 45)
        except RuntimeError:
            print("perplexity composer wait failed; continuing briefly")
            await asyncio.sleep(3)

        try:
            await fill_and_send(page, "Say hello in one short sentence.")
            await asyncio.sleep(7)

            set_auto("cancel", 4500)
            await fill_and_send(page, "WALLED_SENSITIVE demo: block this on Perplexity.")
            await asyncio.sleep(8)

            set_auto("continue", 4500)
            await fill_and_send(page, "WALLED_SENSITIVE demo: allow on Perplexity — reply OK.")
            await asyncio.sleep(10)
        except Exception as exc:
            print("perplexity flow error:", exc)

        clear_auto()

    fut = asyncio.run_coroutine_threadsafe(run(), loop)
    fut.result(timeout=420)


def title_card(seconds: float = 3.0) -> None:
    import tkinter as tk

    root = tk.Tk()
    root.title("Sensitive Upload Guard")
    root.geometry("720x220+200+120")
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    tk.Label(root, text="Sensitive Upload Guard", font=("Sans", 22, "bold")).pack(pady=(28, 8))
    tk.Label(
        root,
        text="Standalone desktop DLP — ChatGPT & Perplexity\n(no browser extension)",
        font=("Sans", 12),
        justify="center",
    ).pack()
    root.update()
    root.after(int(seconds * 1000), root.destroy)
    root.mainloop()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    clear_auto()
    cl = obs.ReqClient(host="localhost", port=4455, password=OBS_PASSWORD, timeout=8)
    if cl.get_record_status().output_active:
        cl.stop_record()
        time.sleep(1)

    events: list[str] = []
    guard = Guard(on_event=lambda m: (print(m), events.append(m))[1])

    print("START_RECORD")
    cl.start_record()
    time.sleep(1)
    title_card(2.5)

    # Real native dialogs (auto-dismissed via /tmp/sug_demo_auto for unattended recording)
    guard.start()
    time.sleep(2)

    try:
        drive(guard)
    finally:
        clear_auto()
        try:
            guard.stop()
        except Exception as exc:
            print("guard stop:", exc)
        time.sleep(1)
        info = cl.stop_record()
        print("STOP_RECORD", getattr(info, "output_path", None))

    newest = sorted(OUT.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if newest:
        dest = OUT / "sensitive-upload-guard-desktop-live.mp4"
        dest.write_bytes(newest[0].read_bytes())
        print("DEMO", dest, dest.stat().st_size)


if __name__ == "__main__":
    main()
