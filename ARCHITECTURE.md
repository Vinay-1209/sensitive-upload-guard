# Architecture

## Goal

Stop accidental leaks of the marker `WALLED_SENSITIVE` into ChatGPT and Perplexity by inspecting prompts and uploads **before transmit**, and ask for a native Continue/Cancel decision when found. Also restyle AI reply text so the guard’s page presence is visible.

## Approach

```
Browser (Chrome / Firefox)
  └─ Extension (MV3)
       ├─ content/gate.js     intercept send + file attach
       ├─ content/color.js    paint AI responses
       └─ background.js       nativeMessaging bridge
                │
                ▼
       Python native host (stdio JSON)
         ├─ scan/detect.py    text / PDF / image
         └─ dialog.py         tkinter Continue/Cancel
```

Why not mitmproxy or OS hooks?

| Approach | Pre-transmit | Native dialog | Response color | Verdict |
|----------|--------------|---------------|----------------|---------|
| Extension + native host | Yes (DOM gate) | Yes | Yes | Chosen |
| TLS MITM | Partial | Awkward | Poor | Rejected |
| Accessibility hooks | Unreliable | Yes | No | Rejected |

## Interception points

1. **Prompts** — capture-phase listeners on Enter and send-button click. If the composer text contains `WALLED_SENSITIVE`, prevent the event, ask the native host, then either stop or re-dispatch after Continue.
2. **Files** — capture-phase `change` / `drop` / `paste` on file inputs. Bytes are base64’d to the host for scanning. Cancel clears the input; Continue re-fires `change` with an allow-once flag.
3. **Responses** — CSS class `sug-ai-response` applied via selectors + `MutationObserver` so streamed replies stay colored.

## Scanning

| Type | Method |
|------|--------|
| Text | Substring search for `WALLED_SENSITIVE` |
| PDF | `pypdf` text extraction |
| Image | Filename + EXIF/info strings + Tesseract OCR |

Scan failures fail closed (treated as sensitive → dialog / cancel).

## Native messaging

Host name: `com.walled.sensitive_upload_guard`  
Chrome origin uses a stable extension ID from the manifest `key`. Firefox uses gecko id `sensitive-upload-guard@local`.

## Enforcement

- **Continue** — original content is not modified; the page proceeds as usual.
- **Cancel** — submission/upload is blocked; the user can edit and retry.
- Clean traffic — no dialog.
