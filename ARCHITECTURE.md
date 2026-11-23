# Architecture

## Goal

Prevent accidental leaks of the marker `WALLED_SENSITIVE` into ChatGPT and Perplexity by inspecting prompts and uploads **before transmit**, showing a **native** Continue/Cancel dialog when found, and visibly restyling AI replies on both sites.

This is a **standalone desktop application**. It does not install or require a browser extension, plugin, or add-on.

## Approach

```
Desktop app (tkinter)
  └─ Start Guard
       └─ Playwright launches Chrome/Chromium
            • persistent profile (~/.local/share/sensitive-upload-guard/profile)
            • --disable-extensions
            • add_init_script(web/gate.js)
            • expose_binding("__sug_check")
                 │
                 ▼
            Python handlers → scan (text/PDF/image) → tk Continue/Cancel subprocess
```

| Approach | Pre-transmit | Native dialog | Response color | Meets “no extension” | Verdict |
|----------|--------------|---------------|----------------|----------------------|---------|
| Desktop app + controlled browser + JS inject | Yes | Yes | Yes | Yes | **Chosen** |
| Browser extension + native host | Yes | Yes | Yes | No | Rejected (disqualified) |
| TLS MITM / system proxy | Partial | Awkward | Weak | Yes | Rejected |
| OS accessibility hooks | Unreliable | Yes | No | Yes | Rejected |
| Embedded Electron/Qt WebView | Yes | Yes | Yes | Yes | Rejected (heavy; login friction) |

## Interception

1. **Prompts** — injected script listens (capture phase) for Enter, send-button pointer/click, and submit. If composer text contains the marker, the event is blocked, Python is asked via `__sug_check`, and the send is re-dispatched only after Continue.
2. **Files** — capture-phase `change` / `drop` / `paste`. Bytes are base64’d to Python. Cancel clears the input; Continue re-fires `change` once.
3. **Responses** — assistant nodes get class `sug-ai-response` + green color (`#0b6e4f`) via `adoptedStyleSheets` / `setProperty(..., 'important')`, with a `MutationObserver` for streamed replies.
4. **Presence** — green **SUG active** badge confirms the inject is live.

## Scanning

| Type | Method |
|------|--------|
| Text | Substring `WALLED_SENSITIVE` |
| PDF | `pypdf` text extraction |
| Image | Filename + EXIF/info strings + Tesseract OCR |

Scan / UI / binding failures **fail closed** (treated as sensitive → Cancel).

## Enforcement

- **Continue** — original prompt or file proceeds unchanged  
- **Cancel** — block; user can edit and retry  
- Clean content — no dialog  

Dialogs run in a **subprocess** so they never nest inside the main app’s Tk loop.

## Concurrency

One `asyncio.Lock` serializes binding handlers so only one native dialog is shown at a time. Playwright runs on a background thread; the Tk UI polls a queue for log lines.

## Why not a browser extension

Walled AI requires a standalone desktop application. An extension (even as a helper) does not meet that bar. The desktop app owns the browser process, injects the gate itself, and never loads unpacked add-ons (`chrome://extensions` stays empty in the controlled profile).
