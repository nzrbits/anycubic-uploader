"""Persistent configuration management for Anycubic Uploader."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
_lock = threading.RLock()  # reentrant: save_token() calls load() then save()

_DEFAULTS: dict = {
    "token": "",
    "watch_folders": [str(Path.home() / "Downloads")],
    "watch_extensions": [".pm4u"],
}


def load() -> dict:
    with _lock:
        if not CONFIG_FILE.exists():
            return dict(_DEFAULTS)
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
            return {**_DEFAULTS, **data}
        except Exception:
            return dict(_DEFAULTS)


def save(cfg: dict) -> None:
    with _lock:
        CONFIG_FILE.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if os.name != "nt":  # chmod 600 on Unix so the token is not world-readable
            os.chmod(CONFIG_FILE, 0o600)


def load_token() -> str:
    return load().get("token", "")


def save_token(token: str) -> None:
    cfg = load()
    cfg["token"] = token
    save(cfg)


def get_watch_folders() -> list[Path]:
    raw = load().get("watch_folders", _DEFAULTS["watch_folders"])
    return [Path(f).expanduser() for f in raw]


def add_watch_folder(folder: Path) -> None:
    cfg = load()
    folders: list[str] = cfg.setdefault("watch_folders", list(_DEFAULTS["watch_folders"]))
    s = str(folder)
    if s not in folders:
        folders.append(s)
        save(cfg)


def remove_watch_folder(folder: Path) -> None:
    cfg = load()
    folders: list[str] = cfg.get("watch_folders", list(_DEFAULTS["watch_folders"]))
    s = str(folder)
    if s in folders:
        folders.remove(s)
        cfg["watch_folders"] = folders
        save(cfg)


def get_watch_extensions() -> set[str]:
    return set(load().get("watch_extensions", _DEFAULTS["watch_extensions"]))
