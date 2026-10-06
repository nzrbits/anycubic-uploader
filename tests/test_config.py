from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

import config


def test_load_returns_defaults_without_file():
    cfg = config.load()
    assert cfg["token"] == ""
    assert cfg["watch_extensions"] == [".pm4u"]
    assert cfg["watch_folders"] == [str(Path.home() / "Downloads")]


def test_load_merges_file_over_defaults():
    config.CONFIG_FILE.write_text('{"token": "abc"}', encoding="utf-8")
    cfg = config.load()
    assert cfg["token"] == "abc"
    assert cfg["watch_extensions"] == [".pm4u"]


def test_load_accepts_utf8_bom():
    # Notepad and PowerShell 5 write a BOM; load() must not fall back to defaults.
    config.CONFIG_FILE.write_bytes(b'\xef\xbb\xbf{"token": "bom"}')
    assert config.load_token() == "bom"


def test_load_reports_broken_json_without_overwriting():
    config.CONFIG_FILE.write_text("{not json", encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.load()
    assert config.CONFIG_FILE.read_text(encoding="utf-8") == "{not json"


def test_save_token_roundtrip_keeps_other_keys():
    config.save(
        {"token": "old", "watch_folders": ["/x"], "watch_extensions": [".gcode"]}
    )
    config.save_token("new")
    cfg = config.load()
    assert cfg["token"] == "new"
    assert cfg["watch_folders"] == ["/x"]
    assert cfg["watch_extensions"] == [".gcode"]


@pytest.mark.skipif(os.name == "nt", reason="chmod 600 only applies on Unix")
def test_save_makes_config_owner_only():
    config.save_token("secret")
    mode = stat.S_IMODE(config.CONFIG_FILE.stat().st_mode)
    assert mode == 0o600


def test_watch_folders_expand_tilde():
    config.save({"watch_folders": ["~/prints"]})
    assert config.get_watch_folders() == [Path.home() / "prints"]


def test_add_watch_folder_is_idempotent(tmp_path):
    config.save({"watch_folders": []})
    config.add_watch_folder(tmp_path)
    config.add_watch_folder(tmp_path)
    assert config.load()["watch_folders"] == [str(tmp_path)]


def test_remove_watch_folder(tmp_path):
    other = tmp_path / "other"
    config.save({"watch_folders": [str(tmp_path), str(other)]})
    config.remove_watch_folder(tmp_path)
    assert config.load()["watch_folders"] == [str(other)]


def test_remove_unknown_folder_does_not_write(tmp_path):
    config.remove_watch_folder(tmp_path / "missing")
    assert not config.CONFIG_FILE.exists()


def test_watch_extensions_is_a_set():
    config.save({"watch_extensions": [".pm4u", ".pm4u", ".gcode"]})
    assert config.get_watch_extensions() == {".pm4u", ".gcode"}


def test_default_lists_are_independent():
    first = config.load()
    first["watch_folders"].clear()
    first["watch_extensions"].append(".other")
    assert config.load()["watch_folders"]
    assert config.get_watch_extensions() == {".pm4u"}


@pytest.mark.parametrize(
    "invalid",
    [
        {"token": 123},
        {"watch_folders": "abc"},
        {"watch_extensions": None},
        {"watch_folders": [None]},
        {"watch_extensions": ["*.pm4u"]},
        [],
    ],
)
def test_invalid_config_is_rejected(invalid):
    import json

    config.CONFIG_FILE.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.load()


def test_concurrent_updates_keep_all_fields(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    config.save({"token": "old", "watch_folders": []})
    folders = [tmp_path / str(i) for i in range(10)]
    with ThreadPoolExecutor(max_workers=8) as workers:
        futures = [
            workers.submit(config.add_watch_folder, folder) for folder in folders
        ]
        futures.append(workers.submit(config.save_token, "new"))
        for future in futures:
            future.result()
    assert config.load_token() == "new"
    assert set(config.get_watch_folders()) == set(folders)


def test_failed_atomic_replace_preserves_config(monkeypatch):
    import storage

    config.save_token("old")
    original = config.CONFIG_FILE.read_bytes()
    monkeypatch.setattr(
        storage.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disk error"))
    )
    with pytest.raises(OSError):
        config.save_token("new")
    assert config.CONFIG_FILE.read_bytes() == original
    assert list(config.CONFIG_FILE.parent.glob("config.json.*")) == [
        config.CONFIG_FILE.with_suffix(".json.lock")
    ]


def test_legacy_config_migrates_once(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy.json"
    legacy.write_text('{"token":"old","watch_folders":[]}', encoding="utf-8")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "LEGACY_CONFIG_FILE", legacy)
    assert config.load_token() == "old"
    legacy.write_text('{"token":"changed"}', encoding="utf-8")
    assert config.load_token() == "old"


def test_separate_processes_preserve_config_updates(tmp_path):
    import subprocess

    config.save({"token": "old", "watch_folders": []})
    environment = {**os.environ, "ANYCUBIC_UPLOADER_DATA_DIR": str(tmp_path)}
    programs = [
        "import config; [config.add_watch_folder(config.CONFIG_FILE.parent / str(i)) for i in range(15)]",
        "import config; [config.save_token('new') for i in range(15)]",
    ]
    processes = [
        subprocess.Popen([sys.executable, "-c", program], env=environment)
        for program in programs
    ]
    for process in processes:
        assert process.wait(timeout=30) == 0
    assert config.load_token() == "new"
    assert len(config.get_watch_folders()) == 15
