"""Validated settings with atomic updates."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

from storage import DATA_DIR, atomic_json, file_lock, normalize_path

CONFIG_FILE = DATA_DIR / "config.json"
LEGACY_CONFIG_FILE = Path(__file__).parent / "config.json"
_lock = threading.Lock()


class ConfigError(ValueError):
    pass


class Settings(TypedDict):
    token: str
    watch_folders: list[str]
    watch_extensions: list[str]


def _defaults() -> Settings:
    return {
        "token": "",
        "watch_folders": [str(Path.home() / "Downloads")],
        "watch_extensions": [".pm4u"],
    }


def _validated(data: object) -> Settings:
    if not isinstance(data, dict):
        raise ConfigError("Settings must be a JSON object")
    result = {**_defaults(), **data}
    token = result["token"]
    if not isinstance(token, str):
        raise ConfigError("token must be a string")
    for key in ("watch_folders", "watch_extensions"):
        values = result[key]
        if not isinstance(values, list) or any(
            not isinstance(v, str) or not v.strip() or "\0" in v for v in values
        ):
            raise ConfigError(f"{key} must be a list of non-empty strings")
        result[key] = list(dict.fromkeys(values))
    if any(
        len(ext) < 2 or not ext.startswith(".") or any(c in ext for c in "/\\*?[]")
        for ext in result["watch_extensions"]
    ):
        raise ConfigError("watch_extensions must contain suffixes such as .pm4u")
    result["watch_extensions"] = list(
        dict.fromkeys(ext.lower() for ext in result["watch_extensions"])
    )
    result["token"] = (
        "" if token.strip() == "YOUR_ANYCUBIC_TOKEN_HERE" else token.strip()
    )
    return result


def _load() -> Settings:
    source = CONFIG_FILE
    if not source.exists():
        if source != DATA_DIR / "config.json" or not LEGACY_CONFIG_FILE.exists():
            return _defaults()
        source = LEGACY_CONFIG_FILE
    try:
        settings = _validated(json.loads(source.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError) as error:
        raise ConfigError(f"Cannot read {source}: {error}") from error
    if source != CONFIG_FILE:
        atomic_json(CONFIG_FILE, settings)
    return settings


def load() -> Settings:
    with _lock, file_lock(CONFIG_FILE):
        return _load()


def save(settings: dict) -> None:
    with _lock, file_lock(CONFIG_FILE):
        atomic_json(CONFIG_FILE, _validated(settings))


def _update(change: Callable[[Settings], None]) -> None:
    with _lock, file_lock(CONFIG_FILE):
        settings = _load()
        change(settings)
        atomic_json(CONFIG_FILE, _validated(settings))


def load_token() -> str:
    return load()["token"]


def save_token(token: str) -> None:
    _update(lambda settings: settings.update(token=token))


def apply_changes(changes: dict, original: Settings) -> None:
    def apply(settings: Settings) -> None:
        for key in changes:
            if settings.get(key) != original.get(key):
                raise ConfigError(
                    "Settings changed while this window was open. Reopen it before saving."
                )
        settings.update(changes)

    _update(apply)


def get_watch_folders() -> list[Path]:
    return list(dict.fromkeys(normalize_path(Path(f)) for f in load()["watch_folders"]))


def add_watch_folder(folder: Path) -> None:
    path = str(normalize_path(folder))

    def add(settings: Settings) -> None:
        folders = [str(normalize_path(Path(f))) for f in settings["watch_folders"]]
        settings["watch_folders"] = list(dict.fromkeys([*folders, path]))

    _update(add)


def remove_watch_folder(folder: Path) -> None:
    path = normalize_path(folder)
    with _lock, file_lock(CONFIG_FILE):
        settings = _load()
        folders = [
            f for f in settings["watch_folders"] if normalize_path(Path(f)) != path
        ]
        if folders != settings["watch_folders"]:
            settings["watch_folders"] = folders
            atomic_json(CONFIG_FILE, settings)


def get_watch_extensions() -> set[str]:
    return set(load()["watch_extensions"])
