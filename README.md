# Sensitive Upload Guard

Lightweight desktop DLP for **ChatGPT** and **Perplexity** in the browser.

When a text prompt or file upload contains the marker `WALLED_SENSITIVE`, a **native** Continue / Cancel dialog appears before anything is sent. AI responses on both sites are recolored so you can see the guard is active.

## Features

- Pre-submit inspection of prompts on chatgpt.com and perplexity.ai
- Pre-upload inspection of **text**, **PDF**, and **image** files
- Native tkinter Continue / Cancel dialog (not an HTML popup)
- Continue leaves content unchanged; Cancel blocks and lets you edit/retry
- AI response text color override on both sites
- Works with **Google Chrome / Chromium** and **Firefox**

## Requirements

- Linux (tested on Ubuntu) with a graphical session
- Python 3.11+
- Google Chrome or Chromium (and/or Firefox)
- System packages:
  ```bash
  sudo apt install python3-tk tesseract-ocr
  ```

## Setup

```bash
git clone <this-repo> sensitive-upload-guard
cd sensitive-upload-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Register native messaging host (Chrome + Firefox)
./scripts/install_native_host.sh
```

### Load the extension — Chrome / Chromium

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select the `extension/` folder
4. Confirm the extension ID is `apljnpgfjedkilddjnmmigilnickhpla` (pinned via manifest `key`)
5. If the ID differs, re-run: `./scripts/install_native_host.sh <your-extension-id>`

### Load the extension — Firefox

1. Install Firefox if needed
2. Open `about:debugging#/runtime/this-firefox`
3. **Load Temporary Add-on** → pick `extension/manifest.json`
4. Gecko id: `sensitive-upload-guard@local` (already registered by the install script)

## Usage

1. Keep your normal desktop session (DISPLAY available for the dialog).
2. Open [ChatGPT](https://chatgpt.com) or [Perplexity](https://www.perplexity.ai).
3. Try:
   - A normal prompt → sends with no dialog
   - A prompt containing `WALLED_SENSITIVE` → native dialog
   - Upload `fixtures/sensitive.txt` / `.pdf` / `.png` → dialog before attach
   - Upload clean fixtures → no dialog
4. AI replies should appear in **green** (`#0b6e4f`).

## Project layout

```
extension/          Browser extension (MV3)
native_host/        Python native messaging host + scanners + dialog
scripts/            Native host installer
fixtures/           Clean / sensitive sample files
tests/              Scanner unit tests
ARCHITECTURE.md     Design notes
```

## Tests

```bash
source .venv/bin/activate
pytest -q
```

## Demo checklist

Record a short video covering both sites:

1. Clean prompt — no dialog  
2. Sensitive prompt — Cancel, then Continue  
3. Sensitive text / PDF / image upload — dialog  
4. Visible AI response color change  

## Security notes

- Fail closed: host/UI/OCR errors → treat as sensitive / Cancel  
- Only ChatGPT and Perplexity origins are matched  
- Continue never rewrites payload content  

## License

MIT
