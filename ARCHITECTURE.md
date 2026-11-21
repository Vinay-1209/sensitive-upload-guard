# Architecture

## Goal

Prevent accidental leaks of the marker `WALLED_SENSITIVE` into ChatGPT and Perplexity by inspecting prompts and uploads **before transmit**, showing a **native** Continue/Cancel dialog when found, and visibly restyling AI replies on both sites.

## Approach

```
Browser (Chrome / Firefox)
  └─ Extension (MV3)
       ├─ content/gate.js      intercept send + file attach
       ├─ content/color.js     paint AI responses
       ├─ content/selectors.js site DOM hooks
       └─ background.js        nativeMessaging (sendNativeMessage)
                │
                ▼
       Python native host (stdio length-prefixed JSON)
         ├─ run_host.sh        restores DISPLAY/XAUTHORITY (Chrome strips them)
         ├─ scan/detect.py     text / PDF (pypdf) / image (EXIF + Tesseract)
         └─ dialog.py          tkinter Continue/Cancel (GUI subprocess)
```

| Approach | Pre-transmit | Native dialog | Response color | Verdict |
|----------|--------------|---------------|----------------|---------|
| Extension + native host | Yes | Yes | Yes | Chosen |
| TLS MITM | Partial | Awkward | Poor | Rejected |
| OS accessibility hooks | Unreliable | Yes | No | Rejected |

## Interception

1. **Prompts** — capture-phase `keydown` (Enter), `pointerdown`/`click` on send, and `submit`. If composer text contains the marker, block the event, ask the host, then re-dispatch only after Continue.
2. **Files** — capture-phase `change` / `drop` / `paste`. Bytes go to the host as base64. Cancel clears the input; Continue re-fires `change` once.
3. **Responses** — CSS class `sug-ai-response` via selectors + `MutationObserver` (covers streamed replies).
4. **Presence** — green **SUG active** badge confirms the content script is injected.

## Scanning

| Type | Method |
|------|--------|
| Text | Substring `WALLED_SENSITIVE` |
| PDF | `pypdf` text extraction |
| Image | Filename + EXIF/info strings + Tesseract OCR |

Scan / UI failures **fail closed** (treated as sensitive → Cancel).

## Native messaging

- Host name: `com.walled.sensitive_upload_guard`
- Chrome origin uses a stable extension ID from the manifest `key`
- Firefox uses gecko id `sensitive-upload-guard@local`
- Chrome often launches the host without `DISPLAY`; `run_host.sh` and dialog helpers restore a graphical session so tkinter can show

## Enforcement

- **Continue** — do not modify the original prompt or file; allow the page to proceed
- **Cancel** — block; user can edit and retry
- Clean content — no dialog
