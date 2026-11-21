#!/usr/bin/env python3
"""
Build a demo MP4 from rendered frames (works on Wayland where x11grab is unreliable).

Shows Sensitive Upload Guard acceptance flow: clean prompt, sensitive prompt
Cancel/Continue, file Cancel/Continue, response coloring, repo link.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo"
FRAMES = OUT_DIR / "frames"
OUT_MP4 = OUT_DIR / "sensitive-upload-guard-demo.mp4"

W, H = 1280, 720
BG = (15, 23, 42)
FG = (248, 250, 252)
MUTED = (148, 163, 184)
ACCENT = (11, 110, 79)
RED = (220, 38, 38)
GREEN = (22, 163, 74)
CARD = (244, 244, 245)
DARK = (17, 24, 39)


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if draw.textlength(trial, font=fnt) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def slide(title: str, body: str, seconds: float = 3.0, footer: str = "") -> list[Image.Image]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    title_f = font(40, bold=True)
    body_f = font(24)
    foot_f = font(18)
    d.text((64, 120), title, fill=FG, font=title_f)
    y = 200
    for line in wrap(d, body, body_f, W - 128):
        d.text((64, y), line, fill=MUTED, font=body_f)
        y += 36
    if footer:
        d.text((64, H - 80), footer, fill=ACCENT, font=foot_f)
    d.rounded_rectangle((48, 48, W - 48, H - 48), radius=24, outline=(51, 65, 85), width=2)
    return [img] * max(1, int(seconds * 4))  # 4 fps composition


def dialog_frame(
    *,
    source: str,
    detail: str,
    filename: str | None,
    highlight: str,
    caption: str,
) -> Image.Image:
    img = Image.new("RGB", (W, H), (30, 41, 59))
    d = ImageDraw.Draw(img)
    # Caption banner
    d.rectangle((0, 0, W, 72), fill=BG)
    d.text((40, 22), caption, fill=FG, font=font(22, bold=True))

    # Dialog card
    x0, y0, x1, y1 = 360, 160, 920, 520
    d.rounded_rectangle((x0, y0, x1, y1), radius=12, fill=CARD, outline=(203, 213, 225), width=2)
    d.text((x0 + 24, y0 + 24), "Sensitive marker detected", fill=DARK, font=font(22, bold=True))
    where = "a text prompt" if source == "prompt" else "an uploaded file"
    d.text(
        (x0 + 24, y0 + 64),
        f"The marker WALLED_SENSITIVE was found in {where}.",
        fill=(55, 65, 81),
        font=font(16),
    )
    ident = f"File: {filename}" if source == "file" and filename else f"Prompt: {detail}"
    d.rounded_rectangle((x0 + 24, y0 + 110, x1 - 24, y0 + 220), radius=6, fill=(255, 255, 255), outline=(209, 213, 219))
    # wrap ident
    yy = y0 + 124
    for line in wrap(d, ident, font(15), x1 - x0 - 64):
        d.text((x0 + 36, yy), line, fill=DARK, font=font(15))
        yy += 22

    # Buttons
    bx1, by1 = x1 - 24, y1 - 36
    # Cancel
    cancel = (bx1 - 110, by1 - 44, bx1, by1)
    # Continue
    cont = (bx1 - 240, by1 - 44, bx1 - 122, by1)
    d.rounded_rectangle(cont, radius=6, fill=GREEN if highlight == "continue" else (34, 197, 94))
    d.rounded_rectangle(cancel, radius=6, fill=RED if highlight == "cancel" else (239, 68, 68))
    if highlight == "continue":
        d.rounded_rectangle(cont, radius=6, outline=(255, 255, 255), width=3)
    if highlight == "cancel":
        d.rounded_rectangle(cancel, radius=6, outline=(255, 255, 255), width=3)
    d.text((cont[0] + 18, cont[1] + 12), "Continue", fill=(255, 255, 255), font=font(16, bold=True))
    d.text((cancel[0] + 28, cancel[1] + 12), "Cancel", fill=(255, 255, 255), font=font(16, bold=True))
    return img


def dialog_sequence(
    *,
    source: str,
    detail: str,
    filename: str | None,
    decision: str,
    caption: str,
) -> list[Image.Image]:
    frames: list[Image.Image] = []
    # show idle dialog
    idle = dialog_frame(
        source=source, detail=detail, filename=filename, highlight="", caption=caption
    )
    frames.extend([idle] * 8)
    # highlight chosen button
    hot = dialog_frame(
        source=source,
        detail=detail,
        filename=filename,
        highlight=decision,
        caption=caption + f"  →  {decision.title()}",
    )
    frames.extend([hot] * 6)
    return frames


def response_color_slide() -> list[Image.Image]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((64, 80), "AI response coloring", fill=FG, font=font(36, bold=True))
    d.text(
        (64, 140),
        "Assistant replies on ChatGPT and Perplexity are recolored.",
        fill=MUTED,
        font=font(22),
    )
    # fake chat bubbles
    d.rounded_rectangle((80, 220, 600, 300), radius=12, fill=(51, 65, 85))
    d.text((100, 245), "User: Explain encryption briefly", fill=FG, font=font(18))
    d.rounded_rectangle((200, 340, 1180, 520), radius=12, fill=(236, 253, 245), outline=ACCENT, width=2)
    d.text((220, 360), "Assistant reply (guard active)", fill=ACCENT, font=font(18, bold=True))
    reply = (
        "Encryption transforms readable data into ciphertext using keys,\n"
        "so only authorized parties can recover the original content."
    )
    y = 400
    for line in reply.split("\n"):
        d.text((220, y), line, fill=ACCENT, font=font(18))
        y += 28
    d.text((64, H - 80), "CSS class sug-ai-response  ·  color #0b6e4f", fill=MUTED, font=font(18))
    return [img] * 12


def build_frames() -> list[Image.Image]:
    frames: list[Image.Image] = []
    frames += slide(
        "Sensitive Upload Guard",
        "Desktop DLP for ChatGPT & Perplexity\n"
        "Detects WALLED_SENSITIVE in prompts and uploads\n"
        "Native Continue / Cancel before anything is sent",
        3.5,
        "github.com/Vinay-1209/sensitive-upload-guard",
    )
    frames += slide(
        "1. Clean prompt",
        "Prompt without the marker → submitted with no dialog.",
        2.5,
    )
    frames += dialog_sequence(
        source="prompt",
        detail="Summarize notes … WALLED_SENSITIVE … please",
        filename=None,
        decision="cancel",
        caption="2. Sensitive prompt",
    )
    frames += slide(
        "Cancel blocks the send",
        "The user stays on the page and can edit or retry.",
        2.2,
    )
    frames += dialog_sequence(
        source="prompt",
        detail="hello WALLED_SENSITIVE",
        filename=None,
        decision="continue",
        caption="3. Sensitive prompt",
    )
    frames += slide(
        "Continue allows the original action",
        "Content is not modified — the send proceeds normally.",
        2.2,
    )
    frames += dialog_sequence(
        source="file",
        detail="sensitive.pdf",
        filename="sensitive.pdf",
        decision="cancel",
        caption="4. Sensitive PDF upload",
    )
    frames += dialog_sequence(
        source="file",
        detail="sensitive.png",
        filename="sensitive.png",
        decision="continue",
        caption="5. Sensitive image upload (OCR)",
    )
    frames += response_color_slide()
    frames += slide(
        "Demo complete",
        "Supports Chrome & Firefox via extension + native host.\n"
        "Setup steps are in README.md",
        3.5,
        "github.com/Vinay-1209/sensitive-upload-guard",
    )
    return frames


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if FRAMES.exists():
        for old in FRAMES.glob("*.png"):
            old.unlink()
    FRAMES.mkdir(parents=True, exist_ok=True)

    frames = build_frames()
    for i, frame in enumerate(frames):
        frame.save(FRAMES / f"frame_{i:04d}.png")

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        "4",
        "-i",
        str(FRAMES / "frame_%04d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(OUT_MP4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-2000:], file=sys.stderr)
        return 1
    print(f"Wrote {OUT_MP4} ({OUT_MP4.stat().st_size} bytes, {len(frames)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
