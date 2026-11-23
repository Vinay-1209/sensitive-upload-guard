"""Native Continue / Cancel confirmation dialog (tkinter)."""

from __future__ import annotations

import glob
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

Decision = Literal["continue", "cancel"]


def _ensure_display() -> None:
    if not os.environ.get("DISPLAY"):
        socks = sorted(Path("/tmp/.X11-unix").glob("X*")) if Path("/tmp/.X11-unix").is_dir() else []
        if socks:
            os.environ["DISPLAY"] = f":{socks[0].name[1:]}"
        else:
            os.environ["DISPLAY"] = ":0"

    if not os.environ.get("XAUTHORITY"):
        uid = os.getuid()
        candidates = (
            sorted(glob.glob(f"/run/user/{uid}/.mutter-Xwaylandauth.*"), reverse=True)
            + sorted(glob.glob(f"/run/user/{uid}/.Xauthority"), reverse=True)
        )
        home_xa = Path.home() / ".Xauthority"
        if home_xa.is_file():
            candidates.append(str(home_xa))
        for path in candidates:
            if Path(path).is_file():
                os.environ["XAUTHORITY"] = path
                break


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
    # Always use a subprocess so the main app's Tk event loop is never nested.
    try:
        return _ask_via_subprocess(
            source=source, detail=detail, filename=filename, error=error
        )
    except Exception as exc:
        logger.exception("subprocess dialog failed: %s", exc)
        return "cancel"


def _ask_via_subprocess(
    *,
    source: str,
    detail: str,
    filename: str | None,
    error: str | None,
) -> Decision:
    env = os.environ.copy()
    script = Path(__file__).with_name("_dialog_cli.py")
    cmd = [
        sys.executable,
        str(script),
        "--source",
        source,
        "--detail",
        detail or "",
    ]
    if filename:
        cmd.extend(["--filename", filename])
    if error:
        cmd.extend(["--error", error])
    proc = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if proc.stderr:
        logger.info("dialog stderr: %s", proc.stderr.strip()[:500])
    out = (proc.stdout or "").strip().lower()
    if out == "continue":
        return "continue"
    return "cancel"


def _show(
    *,
    source: str,
    detail: str,
    filename: str | None,
    error: str | None,
) -> Decision:
    import tkinter as tk

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
    # ponytail: optional demo auto-click via /tmp/sug_demo_auto (cancel|continue); ceiling=file IPC for recordings
    try:
        auto = Path("/tmp/sug_demo_auto").read_text(encoding="utf-8").strip().lower()
    except OSError:
        auto = ""
    if auto in ("continue", "cancel"):
        delay_ms = 2800
        try:
            delay_ms = int(Path("/tmp/sug_demo_auto_ms").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass
        dialog.after(delay_ms, lambda a=auto: finish(a))  # type: ignore[misc]
    root.mainloop()
    try:
        root.destroy()
    except tk.TclError:
        pass
    return result["value"]
