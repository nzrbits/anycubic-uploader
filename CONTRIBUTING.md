# Contributing to Anycubic Uploader

Thanks for wanting to help! This is a community project — all contributions welcome.

## Ways to contribute

- **Bug reports** — open an issue with your OS version, Python version, and the full error from `watcher.log`
- **Feature requests** — open an issue describing what you need and why
- **Code contributions** — see below
- **Documentation** — improvements to README, token guide, or autostart guide always appreciated
- **Testing** — confirm it works (or doesn't) on your OS and hardware — report in Issues

---

## Development setup

```bash
git clone https://github.com/nzrbits/anycubic-uploader
cd anycubic-uploader

python3 -m venv .venv
# Windows:
.venv\Scripts\pip install -r requirements.txt
# macOS/Linux:
.venv/bin/pip install -r requirements.txt
```

Copy `config.example.json` to `config.json` and fill in your token:
```bash
cp config.example.json config.json
# then run setup_token.py or paste your token manually
```

Run the app:
```bash
# Windows:
.venv\Scripts\python tray_app.py
# macOS/Linux:
.venv/bin/python tray_app.py
```

---

## Project structure

| File | Purpose |
|------|---------|
| `config.py` | Config load/save (token, watch folders, extensions) |
| `uploader.py` | Anycubic API + upload logic |
| `tray_app.py` | System tray UI, notifications, folder watcher manager |
| `setup_token.py` | One-time token extraction (browser or manual) |
| `upload_existing.py` | Bulk upload utility |
| `start.ps1` | Windows launcher |
| `start.sh` | macOS/Linux launcher |
| `build/` | PyInstaller specs for building standalone apps |
| `docs/` | User guides |

---

## Running tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

The tests mock the Anycubic API, so no token or network is needed.
Tests marked macOS-only (FSEvents watcher, `osascript` notifications, Chrome profile paths) are skipped on other systems.
Python needs Tk support, otherwise the tray and token tests fail on import.
Homebrew Python does not include Tk unless you install `python-tk`.

---

## Submitting a pull request

1. Fork the repo and create a branch: `git checkout -b feature/my-thing`
2. Make your changes
3. Run the tests and test on your platform
4. Open a PR with a clear description of what changed and why

Please keep PRs focused — one feature or fix per PR makes review much easier.

---

## Platform testing matrix

Help wanted confirming these work:

| Platform | Status |
|---|---|
| Windows 10 / Python 3.10 | ✅ confirmed |
| Windows 11 / Python 3.12 | ✅ confirmed |
| macOS 13 Ventura / Python 3.12 | needs testing |
| macOS 14 Sonoma / Python 3.12 | needs testing |
| macOS 15 Sequoia / Python 3.12 | needs testing |
| macOS 26 Tahoe / Python 3.10–3.13 | ✅ tests pass, app starts (menu bar icon not checked visually) |

If you test on any of these, please open an issue or PR to update this table.

---

## Questions?

Open an issue — there are no dumb questions.
