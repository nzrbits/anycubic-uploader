# Changelog

All notable changes to this project will be documented here.

---

## [Unreleased]

## [1.1.4] - 2026-10-06

### Added
- A minimal Windows setup with a Start menu shortcut and uninstaller.
- Native macOS setup packages for Apple Silicon and Intel, installed in Applications.
- Installation and update checks that verify existing settings are preserved.

## [1.1.3] - 2026-10-06

### Fixed
- Quit cancels the current upload and releases its cloud reservation instead of waiting for the whole transfer.
- Upload completion and failure notifications are suppressed during shutdown.

## [1.1.2] - 2026-10-06

### Changed
- Startup no longer opens token setup. A missing token produces one red notification while the tray stays available.
- Token entry and folder management live in Settings. Duplicate tray controls and the setup script were removed.
- The tray links to a browser FAQ with token instructions and troubleshooting.
- Uploads wait without repeated failure notifications until a token is saved.
- Path normalization is shared, log messages use the correct module, and tests are grouped by responsibility.

## [1.1.1] - 2026-10-06

### Fixed
- The settings window and Windows executable use the Anycubic tray icon.

## [1.1.0] - 2026-10-06

### Changed
- The tray menu offers a settings window and a manual pending-upload trigger.
- Events, startup scans and bulk uploads use one queue and a shared SQLite upload record.
- Settings and logs use a persistent user data folder. Existing source settings migrate once.
- Token setup uses explicit paste entry and runs on first launch of packaged builds.
- README, setup instructions and code comments use shorter, concrete wording.

### Fixed
- Failed older files remain eligible when newer uploads succeed.
- Duplicate events and concurrent uploader processes share upload ownership.
- Growing files are deferred; renamed and modified files reach the queue.
- Network failures release cloud reservations where possible. Finalization failures no longer count as success.
- Settings updates validate field types, preserve concurrent edits and replace files atomically.
- Missing folders can be removed. Failed settings writes undo newly added watches.
- Token setup no longer closes browser processes or guesses tokens from browser database files.
- Launchers retry failed dependency installs and detect changed requirements.
- Windows dialogs queue callbacks until Tk is ready. Tests and package builds run before releases.

### Added
- **Test suite** — pytest tests for config, uploader, token extraction, bulk upload and tray app, with macOS-only tests for the FSEvents watcher, notifications and Chrome profile paths
- **CI workflow** — runs the tests on macOS and Windows for pull requests and pushes to `master`

### Fixed
- Tray app crashed on start with `ValueError` from pystray when at least one watch folder was configured (folder menu callbacks had three parameters, pystray allows two)
- `start.sh` now stops with an install hint when Python has no Tk, instead of crashing in `tray_app.py`

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
