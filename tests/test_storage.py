from pathlib import Path

import storage


def test_explicit_data_directory_overrides_bundle(monkeypatch, tmp_path):
    monkeypatch.setenv("ANYCUBIC_UPLOADER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(storage.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        storage.sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False
    )
    assert storage.data_directory() == tmp_path


def test_windows_data_directory_is_outside_bundle(monkeypatch, tmp_path):
    monkeypatch.delenv("ANYCUBIC_UPLOADER_DATA_DIR", raising=False)
    monkeypatch.setattr(storage.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert storage.data_directory() == tmp_path / "AnycubicUploader"


def test_mac_data_directory(monkeypatch):
    monkeypatch.delenv("ANYCUBIC_UPLOADER_DATA_DIR", raising=False)
    monkeypatch.setattr(storage.sys, "platform", "darwin")
    assert (
        storage.data_directory()
        == Path.home() / "Library/Application Support/AnycubicUploader"
    )


def test_normalize_path_expands_home_and_resolves_file_segments(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert (
        storage.normalize_path(Path("~/prints/../part.pm4u")) == tmp_path / "part.pm4u"
    )
