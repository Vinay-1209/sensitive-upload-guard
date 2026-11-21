# Sensitive Upload Guard

Lightweight desktop DLP for **ChatGPT** and **Perplexity** in the browser.

When a text prompt or uploaded file contains the marker `WALLED_SENSITIVE`, a **native** Continue / Cancel dialog appears **before** the content is sent. AI-generated responses on both sites are recolored so you can see the guard is active.

```
Browser (Chrome / Firefox)
  └─ Extension gates send / file attach
       └─ Python native host → scan → tkinter Continue/Cancel
```

## Features

- Inspect prompts on [chatgpt.com](https://chatgpt.com) and [perplexity.ai](https://www.perplexity.ai) before submit
- Inspect **text**, **PDF**, and **image** uploads before attach/send
- Native desktop dialog (not an HTML/`alert` popup)
- **Continue** — original action proceeds unchanged  
  **Cancel** — block; user can edit and retry
- Clean traffic — no dialog
- AI reply text color override on both sites
- Chrome / Chromium **and** Firefox
- Local test harness for quick verification without logging into the AI sites

## Requirements

| Dependency | Notes |
|------------|--------|
| Linux desktop session | Tested on Ubuntu 24.04 |
| Python 3.11+ | Project uses a venv |
| Google Chrome / Chromium and/or Firefox | Unpacked / temporary extension |
| `python3-tk` | Native dialogs |
| `tesseract-ocr` | Image marker detection via OCR |

```bash
sudo apt install python3-tk tesseract-ocr
```

## Setup

### 1. Clone and install Python deps

```bash
git clone https://github.com/Vinay-1209/sensitive-upload-guard.git
cd sensitive-upload-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Register the native messaging host

```bash
./scripts/install_native_host.sh
```

This writes host manifests for Chrome, Chromium, Brave, and Firefox.  
Host name: `com.walled.sensitive_upload_guard`

### 3. Load the extension — Chrome / Chromium

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select the `extension/` folder
4. Confirm the ID is `apljnpgfjedkilddjnmmigilnickhpla` (pinned by the manifest `key`)
5. If the ID differs: `./scripts/install_native_host.sh <your-extension-id>`
6. Click the extension icon → **Test native host** → should show `OK` / `"pong": true`
7. After pulling code changes, always click **Reload** on the extension card

### 4. Load the extension — Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. **Load Temporary Add-on** → choose `extension/manifest.json`
3. Gecko id: `sensitive-upload-guard@local` (registered by the install script)

## Usage

1. Open ChatGPT or Perplexity (or the local harness below).
2. Look for the green **SUG active** badge (bottom-right) — confirms the content script is injected.
3. Behaviour:

| Action | Expected |
|--------|----------|
| Prompt without `WALLED_SENSITIVE` | Sends normally, no dialog |
| Prompt containing `WALLED_SENSITIVE` | Native Continue/Cancel dialog |
| Upload clean file from `fixtures/` | No dialog |
| Upload sensitive `.txt` / `.pdf` / `.png` from `fixtures/` | Dialog with file name |
| Continue | Original send/upload proceeds |
| Cancel | Blocked; you can edit and try again |
| AI replies | Text colored green (`#0b6e4f`) |

### Local test harness (recommended first check)

```bash
cd testharness
python3 -m http.server 8766
# open http://127.0.0.1:8766/
```

Reload the extension first (so `localhost` permissions apply), then try clean vs sensitive prompts and file uploads.

Sample files: `fixtures/clean.*` and `fixtures/sensitive.*`.

## Project layout

```
extension/           MV3 extension (gate, color, popup, background)
native_host/         Native messaging host, scanners, tk dialog
scripts/             install_native_host.sh
testharness/         Local HTML page for end-to-end checks
fixtures/            Clean / sensitive txt, pdf, png
tests/               Unit tests for scanners + host logic
ARCHITECTURE.md      Design and interception details
```

## Tests

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No **SUG active** badge | Reload the extension; confirm the site matches ChatGPT / Perplexity / localhost harness |
| **Test native host** fails | Re-run `./scripts/install_native_host.sh`; confirm extension ID matches the host JSON |
| No dialog on sensitive text | Reload extension; ensure a graphical session; host restores `DISPLAY` automatically when Chrome strips it |
| Image scan always sensitive | Install `tesseract-ocr`; OCR failures fail closed by design |
| Firefox temporary add-on gone | Load it again after browser restart |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md).

## Demo checklist

1. Clean prompt — no dialog  
2. Sensitive prompt — Cancel, then Continue  
3. Sensitive text / PDF / image upload — dialog  
4. Response color visible on **both** ChatGPT and Perplexity  

## Security notes

- Fail closed on host / UI / OCR errors  
- Continue never rewrites payload content  
- Only configured site origins are matched  

## License

MIT — see [LICENSE](LICENSE).
