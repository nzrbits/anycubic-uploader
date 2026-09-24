# Changelog

All notable changes to this project will be documented here.

---

## [1.0.0] — 2025-09-24

### Added
- **macOS support** — tray app now runs on macOS via PyObjC/AppKit backend
- **Multiple watch folders** — configure any number of folders via tray menu or `config.json`
- **"Folders to Watch" tray menu** — add or remove watched folders at runtime without restarting
- **Folder picker dialog** — click "Add folder…" in the tray to browse and add a new folder
- **Cross-platform notifications** — custom toast overlay on Windows; native `osascript` notifications on macOS
- **Cross-platform token setup** — `setup_token.py` supports Edge and Chrome on Windows, Chrome on macOS, with a GUI manual-entry fallback on all platforms
- **`config.py`** — centralized configuration layer; `config.json` now supports `watch_folders` and `watch_extensions`
- **macOS launcher** — `start.sh` for macOS and Linux (mirrors `start.ps1`)
- **PyInstaller build specs** — `build/windows.spec` and `build/macos.spec` for standalone executables
- **GitHub Actions workflow** — builds Windows `.exe` and macOS `.app` on every version tag
- **MIT License**
- **`CONTRIBUTING.md`** — contribution guide and platform testing matrix
- **`docs/token-guide.md`** — step-by-step token extraction for Chrome, Edge, Firefox, Safari
- **`docs/autostart.md`** — autostart setup for Windows (Startup folder) and macOS (Launch Agent / Login Items)

### Changed
- `uploader.py` — removed hardcoded `WATCH_FOLDER`; reads config dynamically via `config.py`
- `upload_existing.py` — scans all configured watch folders, not just Downloads
- `tray_app.py` — full rewrite with `WatcherManager` class, cross-platform notification dispatch, dynamic folder menu
- `config.example.json` — updated to include `watch_folders` and `watch_extensions` fields
- `start.ps1` — updated token check to use new config format
- `requirements.txt` — added `pyobjc-framework-Cocoa` for macOS
- All user-facing strings translated to English for international community use
- Log messages standardized to English

### Fixed
- File handler class duplication between `uploader.py` and `tray_app.py` removed
- Observer lifecycle properly managed — `observer.join()` called on shutdown

---

## [0.1.0] — 2025 (Initial release)

- Windows-only tray app
- Watches `~/Downloads` for `.pm4u` files
- Uploads via 4-step Anycubic Cloud S3 flow
- Edge-based token extraction
- Custom toast notifications
