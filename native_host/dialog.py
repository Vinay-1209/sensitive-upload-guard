"""Native Continue / Cancel confirmation dialog (tkinter)."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from typing import Literal

logger = logging.getLogger(__name__)

Decision = Literal["continue", "cancel"]


def _ensure_display() -> None:
    if os.environ.get("DISPLAY"):
        return
    if os.path.isdir("/tmp/.X11-unix"):
        socks = sorted(os.listdir("/tmp/.X11-unix"))
        if socks:
            os.environ["DISPLAY"] = f":{socks[0][1:]}"
            return
    os.environ.setdefault("DISPLAY", ":0")


def ask_user(
    *,
    source: str,
    detail: str,
    filename: str | None = None,
    error: str | None = None,
) -> Decision:
    """
    Show a native dialog. Returns 'continue' or 'cancel'.
    Fail-closed: any UI error → cancel.
    """
    _ensure_display()
    try:
        return _show(source=source, detail=detail, filename=filename, error=error)
    except Exception as exc:
        logger.exception("dialog failed: %s", exc)
        return "cancel"


def _show(
    *,
    source: str,
    detail: str,
    filename: str | None,
    error: str | None,
) -> Decision:
    result: dict[str, Decision] = {"value": "cancel"}

    root = tk.Tk()
    root.withdraw()
    root.title("Sensitive Upload Guard")
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    bg = "#f4f4f5"
    dialog = tk.Toplevel(root)
    dialog.title("Sensitive content detected")
    dialog.configure(bg=bg)
    dialog.attributes("-topmost", True)
    dialog.resizable(True, True)
    dialog.minsize(480, 280)
    dialog.geometry("560x320")
    try:
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
    except tk.TclError:
        pass

    frame = tk.Frame(dialog, bg=bg, padx=16, pady=16)
    frame.pack(fill=tk.BOTH, expand=True)

    where = "a text prompt" if source == "prompt" else "an uploaded file"
    tk.Label(
        frame,
        text="Sensitive marker detected",
        font=("Sans", 13, "bold"),
        bg=bg,
        fg="#111827",
        anchor="w",
    ).pack(fill=tk.X)

    tk.Label(
        frame,
        text=f"The marker WALLED_SENSITIVE was found in {where}.",
        font=("Sans", 10),
        bg=bg,
        fg="#374151",
        anchor="w",
        justify=tk.LEFT,
        wraplength=500,
    ).pack(fill=tk.X, pady=(8, 4))

    if source == "file" and filename:
        ident = f"File: {filename}"
    elif source == "prompt":
        ident = f"Prompt: {detail}"
    else:
        ident = f"Detail: {detail or filename or '(unknown)'}"

    tk.Label(
        frame,
        text=ident,
        font=("monospace", 10),
        bg="#ffffff",
        fg="#111827",
        anchor="w",
        justify=tk.LEFT,
        wraplength=500,
        padx=8,
        pady=8,
        relief=tk.SOLID,
        borderwidth=1,
    ).pack(fill=tk.BOTH, expand=True, pady=(8, 8))

    if error:
        tk.Label(
            frame,
            text=f"Note: {error}",
            font=("Sans", 9),
            bg=bg,
            fg="#b45309",
            anchor="w",
            wraplength=500,
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(0, 8))

    btn_row = tk.Frame(frame, bg=bg)
    btn_row.pack(side=tk.BOTTOM, fill=tk.X)

    def finish(decision: Decision) -> None:
        result["value"] = decision
        try:
            dialog.grab_release()
        except tk.TclError:
            pass
        dialog.destroy()
        root.quit()

    tk.Button(
        btn_row,
        text="  Cancel  ",
        command=lambda: finish("cancel"),
        font=("Sans", 11, "bold"),
        bg="#dc2626",
        fg="#ffffff",
        activebackground="#b91c1c",
        activeforeground="#ffffff",
        relief=tk.RAISED,
        borderwidth=2,
        padx=18,
        pady=8,
        cursor="hand2",
    ).pack(side=tk.RIGHT, padx=(8, 0))

    tk.Button(
        btn_row,
        text="  Continue  ",
        command=lambda: finish("continue"),
        font=("Sans", 11, "bold"),
        bg="#16a34a",
        fg="#ffffff",
        activebackground="#15803d",
        activeforeground="#ffffff",
        relief=tk.RAISED,
        borderwidth=2,
        padx=18,
        pady=8,
        cursor="hand2",
    ).pack(side=tk.RIGHT)

    tk.Label(
        btn_row,
        text="Continue allows the action · Cancel blocks it",
        font=("Sans", 9),
        bg=bg,
        fg="#6b7280",
        anchor="w",
    ).pack(side=tk.LEFT)

    dialog.protocol("WM_DELETE_WINDOW", lambda: finish("cancel"))
    dialog.bind("<Escape>", lambda _e: finish("cancel"))
    dialog.update_idletasks()
    root.mainloop()
    try:
        root.destroy()
    except tk.TclError:
        pass
    return result["value"]
