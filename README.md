# Anycubic Cloud Auto-Uploader

Windows tray app that watches your Downloads folder for `.pm4u` slicer files and uploads them to Anycubic Cloud automatically.

## Features

- Runs as a system tray icon
- Detects new `.pm4u` files as soon as they appear in Downloads
- Uploads them via the Anycubic Cloud API (4-step S3 presigned flow)
- Shows custom toast notifications (uploading / success / error + free storage)
- Catches up on files missed while the app was not running
- Token stored locally in `config.json` — never transmitted elsewhere

## Requirements

- Windows 10/11
- Python 3.10+
- Microsoft Edge (for the one-time token setup)

## Setup

### 1. Get your Anycubic token

Run the token extractor once:

```powershell
python setup_token.py
```

A temporary Edge window opens. Log in to [cloud-universe.anycubic.com](https://cloud-universe.anycubic.com), then press Enter in the terminal. The token is saved to `config.json`.

### 2. Start the uploader

```powershell
.\start.ps1
```

`start.ps1` creates a `.venv`, installs dependencies from `requirements.txt`, and launches the tray app. Subsequent starts skip the venv creation step.

### 3. Autostart (optional)

Create a shortcut to `start.ps1` in the Windows Startup folder (`shell:startup`) to launch the app on login.

## Manual one-time upload

To upload all existing `.pm4u` files in Downloads:

```powershell
.venv\Scripts\python.exe upload_existing.py
```

## Files

| File | Purpose |
|---|---|
| `tray_app.py` | Tray app entry point, toast notifications |
| `uploader.py` | Core upload logic and file watcher |
| `setup_token.py` | One-time token extraction from Edge |
| `upload_existing.py` | Bulk upload of existing files |
| `start.ps1` | Launcher (sets up venv, starts tray app) |
| `config.json` | Auth token — **not in git**, copy from `config.example.json` |
| `last_upload.json` | Timestamp of last successful upload (runtime state) |
| `watcher.log` | Upload log |

## How the upload works

The Anycubic Cloud API uses a 4-step flow (reverse-engineered from the web client):

1. `POST /v2/cloud_storage/lockStorageSpace` — reserve space, get AWS presigned URL
2. `PUT <presignUrl>` — upload file bytes directly to S3
3. `POST /v2/profile/newUploadFile` — register the upload, get `cloud_file_id`
4. `POST /v2/cloud_storage/unlockStorageSpace` — finalize

## Token expiry

Tokens expire. Re-run `python setup_token.py` to refresh — it overwrites `config.json`.
