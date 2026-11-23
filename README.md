# Sensitive Upload Guard

Standalone **desktop** DLP for ChatGPT and Perplexity.

The app launches a controlled Chrome/Chromium window (no browser extension). When a text prompt or uploaded file contains `WALLED_SENSITIVE`, a **native** Continue / Cancel dialog appears **before** the content is sent. AI replies on both sites are recolored so you can see the guard is active.

```
Desktop app (sug)
  └─ Playwright Chrome/Chromium (--disable-extensions)
       └─ Injected gate.js ↔ Python scan + tk dialog
```

## Features

- Inspect prompts on [chatgpt.com](https://chatgpt.com) and [perplexity.ai](https://www.perplexity.ai) before submit
- Inspect **text**, **PDF**, and **image** uploads before attach/send
- Native desktop dialog (not an HTML/`alert` popup)
- **Continue** — original action proceeds unchanged  
  **Cancel** — block; user can edit and retry
- Clean traffic — no dialog
- AI reply text color override on both sites
- Local HTML harness for quick checks without logging into the AI sites

## Requirements

| Dependency | Notes |
|------------|--------|
| Linux desktop session | Tested on Ubuntu 24.04 |
| Python 3.11+ | Project uses a venv |
| Google Chrome (preferred) or Chromium | Launched by the app |
| `python3-tk` | Native dialogs + app UI |
| `tesseract-ocr` | Image marker detection via OCR |

```bash
sudo apt install python3-tk tesseract-ocr
```

## Setup

```bash
git clone https://github.com/Vinay-1209/sensitive-upload-guard.git
cd sensitive-upload-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium   # fallback if Chrome channel unavailable
```

## Run

```bash
source .venv/bin/activate
sug
# or: python -m sensitive_upload_guard
```

1. Click **Start guard** — a Chrome/Chromium window opens (extensions disabled).
2. Click **Open ChatGPT** or **Open Perplexity** (log in once; the profile is reused under `~/.local/share/sensitive-upload-guard/profile`).
3. Look for the green **SUG active** badge (bottom-right).
4. Try:

| Action | Expected |
|--------|----------|
| Prompt without `WALLED_SENSITIVE` | Sends normally, no dialog |
| Prompt containing `WALLED_SENSITIVE` | Native Continue/Cancel dialog |
| Upload clean file from `fixtures/` | No dialog |
| Upload sensitive `.txt` / `.pdf` / `.png` from `fixtures/` | Dialog with file name |
| Continue | Original send/upload proceeds |
| Cancel | Blocked; you can edit and try again |
| AI replies | Text colored green (`#0b6e4f`) |

### Local test harness

```bash
cd testharness
python3 -m http.server 8766
```

With the guard running, open `http://127.0.0.1:8766/` in the **controlled** browser window (paste the URL in the address bar).

## Why this is not a browser extension

The assignment requires a **standalone desktop application**. This project:

- Ships a Tk desktop UI (`sug`)
- Owns the browser process via Playwright
- Injects monitoring JS itself (`add_init_script`)
- Never installs a Chrome/Firefox extension, plugin, or add-on

`chrome://extensions` in the controlled profile should show no SUG add-on.

## Project layout

```
src/sensitive_upload_guard/
  app.py          Tk desktop shell
  guard.py        Playwright worker + binding
  handlers.py     check_prompt / check_file
  dialog.py       native Continue/Cancel
  scan/detect.py  text / PDF / image scanners
  web/gate.js     injected page gate + color
testharness/      local HTML page
fixtures/         clean / sensitive samples
tests/            unit + harness e2e
ARCHITECTURE.md   design notes
```

## Tests

```bash
source .venv/bin/activate
pytest -q
```

## Known limitations

- DOM selectors can break when ChatGPT/Perplexity redesign the UI
- Only the app-controlled browser is guarded (not your everyday Chrome profile unless you start it from the app)
- Image-only PDFs are not OCR’d (text-layer PDFs are)
- Missing `tesseract` → image scans fail closed (extra Cancel prompts)
- Some SPA paths (edit-and-resend chips, etc.) may need selector updates

## Security notes

- Fail closed on host / UI / OCR / binding errors
- Continue never rewrites payload content
- Inject only activates on ChatGPT, Perplexity, and localhost harness hosts
- Browser profile (cookies) lives outside the repo

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md).

## Demo video

Record a live walkthrough of the **desktop app** (both sites) with OBS:

```bash
# Terminal A: start OBS (websocket enabled on :4455)
obs

# Terminal B:
source .venv/bin/activate
pip install obsws-python   # only needed for the recorder helper
PYTHONPATH=src python scripts/record_live_demo.py
```

Output (local, **not** committed — upload to YouTube yourself):

`~/Videos/sensitive-upload-guard/sensitive-upload-guard-desktop-live.mp4`

The script shows: title card → controlled Chrome (no extensions) → ChatGPT clean / Cancel / Continue / file Cancel → Perplexity Cancel / Continue. Native Continue/Cancel dialogs are real tk windows.

Manual checklist for your own recording:

1. `sug` → **Start guard** → Open ChatGPT and Perplexity  
2. Confirm `chrome://extensions` has no SUG add-on  
3. Clean prompt (no dialog)  
4. `WALLED_SENSITIVE` → Cancel, then Continue  
5. Sensitive file from `fixtures/` → dialog  
6. Response text color on both sites  

## License

MIT — see [LICENSE](LICENSE).
