# Anycubic Cloud Auto-Uploader

A system tray app for **Windows and macOS** that watches folders for `.pm4u` slicer files
and uploads them to Anycubic Cloud automatically — so your printer is always ready.

---

## Features

- Runs silently as a system tray / menu bar icon
- Watches any number of folders — configurable at any time from the tray menu
- Detects new `.pm4u` files instantly and uploads them via the Anycubic Cloud API
- Catches up on files missed while the app was not running
- Custom toast notifications on Windows; native notifications on macOS
- Token stored **locally only** in `config.json` — never sent anywhere except Anycubic Cloud
- Cross-platform: Windows 10/11 and macOS 12+

---

## Requirements

| | Windows | macOS |
|---|---|---|
| Python | 3.10 or later | 3.10 or later |
| Browser (token setup) | Edge or Chrome | Chrome |
| OS | Windows 10 / 11 | macOS 12 Monterey or later |

No Edge required on macOS — Chrome works, or paste your token manually.

---

## Quick start

### 1. Download

```bash
git clone https://github.com/nzrbits/anycubic-uploader
cd anycubic-uploader
```

Or download the [latest release](../../releases/latest) as a standalone `.exe` (Windows)
or `.app` (macOS) — no Python needed.

### 2. First-time setup

**Windows (PowerShell):**
```powershell
.\start.ps1
```

**macOS / Linux (Terminal):**
```bash
chmod +x start.sh
./start.sh
```

The launcher will:
1. Create a Python virtual environment (once)
2. Install dependencies (once)
3. Run `setup_token.py` if no token is saved yet
4. Start the tray app

### 3. Get your token

`setup_token.py` tries to extract the token automatically from Edge or Chrome.
If that fails, it shows a dialog with step-by-step instructions.

> For detailed instructions on every browser, see **[docs/token-guide.md](docs/token-guide.md)**

### 4. Configure watch folders

The default watch folder is `~/Downloads`. To change or add folders:

- **Right-click the tray icon** → **Folders to watch** → **Add folder…**
- Or edit `config.json` directly:

```json
{
  "token": "eyJ...",
  "watch_folders": [
    "~/Downloads",
    "~/Desktop/prints"
  ],
  "watch_extensions": [".pm4u"]
}
```

### 5. Autostart (optional)

See **[docs/autostart.md](docs/autostart.md)** for instructions on Windows (Startup folder)
and macOS (Launch Agent or Login Items).

---

## Tray menu

Right-click the tray icon to access:

```
Anycubic Uploader
─────────────────
Folders to watch ▶
  ~/Downloads
    ├── Open in Explorer
    └── Remove
  ~/Desktop/prints
    ├── Open in Explorer
    └── Remove
  ─────────────────
  Add folder…
─────────────────
Open log
─────────────────
Quit
```

---

## Manual bulk upload

To upload all `.pm4u` files already in your watched folders:

**Windows:**
```powershell
.venv\Scripts\python.exe upload_existing.py
```

**macOS / Linux:**
```bash
.venv/bin/python upload_existing.py
```

---

## Files

| File | Purpose |
|---|---|
| `config.py` | Config management (token, folders, extensions) |
| `tray_app.py` | Tray app, notifications, folder watcher manager |
| `uploader.py` | Anycubic Cloud API + upload logic |
| `setup_token.py` | One-time token extraction |
| `upload_existing.py` | Bulk upload utility |
| `start.ps1` | Windows launcher |
| `start.sh` | macOS / Linux launcher |
| `config.json` | Your settings — **not in git** |
| `config.example.json` | Template for config.json |
| `watcher.log` | Upload log (last ~1000 entries) |
| `last_upload.json` | Timestamp used for catch-up logic |

---

## How uploads work

The Anycubic Cloud API uses a 4-step presigned S3 flow:

1. `POST /v2/cloud_storage/lockStorageSpace` — reserve space, receive AWS presigned URL
2. `PUT <presignUrl>` — upload file bytes directly to S3
3. `POST /v2/profile/newUploadFile` — register the upload, receive `cloud_file_id`
4. `POST /v2/cloud_storage/unlockStorageSpace` — finalize and make file available

This was reverse-engineered from the Anycubic Cloud web client.

---

## Token expiry

Tokens expire after some time. If uploads fail with authentication errors:

```bash
python setup_token.py   # or: .venv/bin/python setup_token.py
```

This overwrites the old token in `config.json`.

---

## Troubleshooting

**Tray icon doesn't appear on macOS**
Make sure `pyobjc-framework-Cocoa` is installed: `pip install pyobjc-framework-Cocoa`

**"No token found" on startup**
Run `setup_token.py` — see [docs/token-guide.md](docs/token-guide.md)

**Upload fails with HTTP 4xx**
Your token has expired. Re-run `setup_token.py`.

**File is detected but not uploaded**
The app waits for the file to finish writing before uploading.
If the slicer takes a long time to save, increase `FILE_STABLE_WAIT` in `uploader.py`.

**Logs**
All events are logged to `watcher.log` in the app folder.
Open it from the tray menu: **Open log**.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions welcome — bug reports,
feature requests, macOS testing, and code PRs.

---

## License

MIT — see [LICENSE](LICENSE)
