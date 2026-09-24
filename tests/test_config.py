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


def test_load_falls_back_on_broken_json():
    config.CONFIG_FILE.write_text("{not json", encoding="utf-8")
    assert config.load()["token"] == ""


def test_save_token_roundtrip_keeps_other_keys():
    config.save({"token": "old", "watch_folders": ["/x"], "watch_extensions": [".gcode"]})
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
