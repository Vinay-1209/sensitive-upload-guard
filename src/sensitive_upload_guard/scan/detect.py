"""Detect the WALLED_SENSITIVE marker in text, PDF, and image payloads."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

MARKER = "WALLED_SENSITIVE"


@dataclass(frozen=True)
class ScanResult:
    found: bool
    source: str  # "prompt" | "file" | "none"
    detail: str = ""
    error: str | None = None


def scan_text(text: str, *, source: str = "prompt") -> ScanResult:
    if MARKER in (text or ""):
        snippet = _snippet(text, MARKER)
        return ScanResult(found=True, source=source, detail=snippet)
    return ScanResult(found=False, source="none")


def scan_bytes(data: bytes, filename: str, mime: str = "") -> ScanResult:
    name = filename or "upload"
    lower = name.lower()
    mime = (mime or "").lower()

    # Filename itself may contain the marker.
    if MARKER in name:
        return ScanResult(found=True, source="file", detail=name)

    try:
        if _is_pdf(lower, mime, data):
            return _scan_pdf(data, name)
        if _is_image(lower, mime, data):
            return _scan_image(data, name)
        # Default: treat as text (utf-8 / latin-1 fallback).
        return _scan_text_bytes(data, name)
    except Exception as exc:  # fail closed — caller should prompt / block
        logger.exception("scan failed for %s", name)
        return ScanResult(
            found=True,
            source="file",
            detail=name,
            error=f"Scan failed ({exc}); treat as sensitive",
        )


def _is_pdf(name: str, mime: str, data: bytes) -> bool:
    return name.endswith(".pdf") or "pdf" in mime or data[:4] == b"%PDF"


def _is_image(name: str, mime: str, data: bytes) -> bool:
    if mime.startswith("image/"):
        return True
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"):
        if name.endswith(ext):
            return True
    # Magic sniff
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    return False


def _scan_text_bytes(data: bytes, name: str) -> ScanResult:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            text = None
    else:
        text = data.decode("utf-8", errors="replace")
    result = scan_text(text, source="file")
    if result.found:
        return ScanResult(found=True, source="file", detail=name)
    return ScanResult(found=False, source="none")


def _scan_pdf(data: bytes, name: str) -> ScanResult:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n".join(chunks)
    if MARKER in text:
        return ScanResult(found=True, source="file", detail=name)
    return ScanResult(found=False, source="none")


def _scan_image(data: bytes, name: str) -> ScanResult:
    from PIL import Image
    from PIL.ExifTags import TAGS

    img = Image.open(io.BytesIO(data))

    # EXIF / info string fields
    meta_bits: list[str] = [name]
    try:
        exif = img.getexif()
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, str(tag_id))
                meta_bits.append(f"{tag}={value}")
    except Exception:
        pass
    for key, value in (img.info or {}).items():
        meta_bits.append(f"{key}={value}")
    meta_text = "\n".join(str(x) for x in meta_bits)
    if MARKER in meta_text:
        return ScanResult(found=True, source="file", detail=name)

    # OCR
    try:
        import pytesseract

        ocr_text = pytesseract.image_to_string(img) or ""
    except Exception as exc:
        return ScanResult(
            found=True,
            source="file",
            detail=name,
            error=f"OCR unavailable ({exc}); treat as sensitive",
        )
    if MARKER in ocr_text:
        return ScanResult(found=True, source="file", detail=name)
    return ScanResult(found=False, source="none")


def _snippet(text: str, marker: str, radius: int = 40) -> str:
    idx = text.find(marker)
    if idx < 0:
        return text[:80]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(marker) + radius)
    piece = text[start:end].replace("\n", " ")
    if start > 0:
        piece = "…" + piece
    if end < len(text):
        piece = piece + "…"
    return piece
