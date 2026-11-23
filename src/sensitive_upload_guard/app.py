"""Tkinter desktop shell for Sensitive Upload Guard."""

from __future__ import annotations

import logging
import queue
import shutil
import tkinter as tk
from tkinter import scrolledtext, ttk

from sensitive_upload_guard.guard import Guard

logger = logging.getLogger(__name__)

CHATGPT = "https://chatgpt.com/"
PERPLEXITY = "https://www.perplexity.ai/"


def _preflight() -> list[str]:
    notes: list[str] = []
    try:
        import tkinter as _tk

        r = _tk.Tk()
        r.withdraw()
        r.destroy()
    except Exception as exc:
        notes.append(f"tkinter unavailable: {exc}")

    if shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium-browser"):
        notes.append("Chrome/Chromium found on PATH.")
    else:
        notes.append("No Chrome binary on PATH — Playwright may use bundled Chromium.")

    if shutil.which("tesseract"):
        notes.append("tesseract found (image OCR enabled).")
    else:
        notes.append("tesseract not on PATH — image scans fail closed until installed.")
    return notes


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sensitive Upload Guard")
        self.geometry("640x480")
        self.minsize(520, 360)

        self._events: queue.Queue[str] = queue.Queue()
        self._guard: Guard | None = None

        hdr = ttk.Label(
            self,
            text="Desktop DLP for ChatGPT & Perplexity",
            font=("Sans", 12, "bold"),
        )
        hdr.pack(anchor="w", padx=12, pady=(12, 4))

        sub = ttk.Label(
            self,
            text="Opens a controlled browser (no extension). Marker: WALLED_SENSITIVE",
            wraplength=600,
        )
        sub.pack(anchor="w", padx=12, pady=(0, 8))

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=12, pady=4)

        self.start_btn = ttk.Button(btns, text="Start guard", command=self._start)
        self.start_btn.pack(side="left", padx=(0, 6))
        self.stop_btn = ttk.Button(btns, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 6))
        self.chatgpt_btn = ttk.Button(
            btns, text="Open ChatGPT", command=lambda: self._open(CHATGPT), state="disabled"
        )
        self.chatgpt_btn.pack(side="left", padx=(0, 6))
        self.pplx_btn = ttk.Button(
            btns,
            text="Open Perplexity",
            command=lambda: self._open(PERPLEXITY),
            state="disabled",
        )
        self.pplx_btn.pack(side="left")

        self.status = ttk.Label(self, text="Stopped", foreground="#374151")
        self.status.pack(anchor="w", padx=12, pady=(8, 4))

        ttk.Label(self, text="Event log").pack(anchor="w", padx=12)
        self.log = scrolledtext.ScrolledText(self, height=16, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        for line in _preflight():
            self._append(line)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._drain)

    def _append(self, msg: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", msg.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain(self) -> None:
        while True:
            try:
                msg = self._events.get_nowait()
            except queue.Empty:
                break
            self._append(msg)
        self.after(200, self._drain)

    def _on_event(self, msg: str) -> None:
        self._events.put(msg)

    def _start(self) -> None:
        if self._guard:
            return
        self.status.configure(text="Starting…")
        self.start_btn.configure(state="disabled")
        self.update_idletasks()

        guard = Guard(on_event=self._on_event)
        try:
            guard.start()
        except Exception as exc:
            self._append(f"Start failed: {exc}")
            self.status.configure(text="Start failed")
            self.start_btn.configure(state="normal")
            return

        self._guard = guard
        self.status.configure(text="Running")
        self.stop_btn.configure(state="normal")
        self.chatgpt_btn.configure(state="normal")
        self.pplx_btn.configure(state="normal")
        self._append("Guard started.")

    def _stop(self) -> None:
        guard = self._guard
        self._guard = None
        if guard:
            try:
                guard.stop()
            except Exception as exc:
                self._append(f"Stop error: {exc}")
        self.status.configure(text="Stopped")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.chatgpt_btn.configure(state="disabled")
        self.pplx_btn.configure(state="disabled")
        self._append("Guard stopped.")

    def _open(self, url: str) -> None:
        if not self._guard:
            return
        try:
            self._guard.open_site(url)
        except Exception as exc:
            self._append(f"Open failed: {exc}")

    def _on_close(self) -> None:
        self._stop()
        self.destroy()


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = App()
    app.mainloop()
