# Contributing

Open an issue for a bug or send a focused pull request.
Include your OS, Python version, what you expected and the relevant log entries.
Remove tokens and signed upload URLs before sharing logs.

## Development

```sh
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -rs
```

macOS:

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -rs
```

Python needs Tk for the tray and settings tests.
The tests use temporary settings and databases, and simulate the cloud API.
Observer tests use real filesystem events on the test platform.
CI runs on Windows and macOS with Python 3.10 and 3.12.

## Code layout

| Module | Responsibility |
| --- | --- |
| `storage.py` | Data paths, file locks, atomic JSON writes and logging |
| `config.py` | Settings validation and updates |
| `uploader.py` | Cloud requests and transaction cleanup |
| `upload_state.py` | File versions and upload ownership |
| `upload_queue.py` | Discovery, deduplication and upload processing |
| `notifications.py` | Icons and notifications |
| `tray_app.py` | Tray menu and folder watches |
| `settings_dialog.py` | Settings window |
| `upload_existing.py` | Bulk command |

Keep upload decisions in `upload_queue.py` so event handlers and bulk uploads follow the same rules.
Add regression tests for changed behavior, especially failures during a cloud transaction or a settings update.

## Standalone builds

Install PyInstaller 6 in the virtual environment:

```sh
python -m pip install "pyinstaller>=6,<7"
```

Use the virtual environment's `pyinstaller` command:

```sh
pyinstaller packaging/windows.spec
pyinstaller packaging/macos.spec
```

Build each package on its target OS. Output goes to `dist/`.
CI builds both packages on Python 3.12 after the tests pass.
Version tags beginning with `v` run the release workflow.
