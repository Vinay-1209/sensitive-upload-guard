from pathlib import Path

from sensitive_upload_guard.scan.detect import MARKER, scan_bytes, scan_text

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_marker_constant():
    assert MARKER == "WALLED_SENSITIVE"


def test_scan_text_clean():
    r = scan_text("hello world")
    assert r.found is False


def test_scan_text_sensitive():
    r = scan_text(f"prefix {MARKER} suffix")
    assert r.found is True
    assert r.source == "prompt"
    assert MARKER in r.detail


def test_scan_txt_file():
    data = (FIXTURES / "sensitive.txt").read_bytes()
    r = scan_bytes(data, "sensitive.txt", "text/plain")
    assert r.found is True
    assert r.source == "file"

    clean = (FIXTURES / "clean.txt").read_bytes()
    r2 = scan_bytes(clean, "clean.txt", "text/plain")
    assert r2.found is False


def test_scan_pdf_file():
    data = (FIXTURES / "sensitive.pdf").read_bytes()
    r = scan_bytes(data, "sensitive.pdf", "application/pdf")
    assert r.found is True

    clean = (FIXTURES / "clean.pdf").read_bytes()
    r2 = scan_bytes(clean, "clean.pdf", "application/pdf")
    assert r2.found is False


def test_scan_png_file():
    data = (FIXTURES / "sensitive.png").read_bytes()
    r = scan_bytes(data, "sensitive.png", "image/png")
    # OCR or EXIF may find marker; fail-closed also acceptable if tesseract missing
    assert r.found is True or r.error

    clean = (FIXTURES / "clean.png").read_bytes()
    r2 = scan_bytes(clean, "clean.png", "image/png")
    # clean image should not contain marker unless OCR false-positive / fail-closed
    assert r2.found is False or r2.error
