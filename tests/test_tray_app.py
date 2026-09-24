from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

import config
import tray_app

macos_only = pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")


class RecordingNotifier:
    def __init__(self):
        self.messages = []

    def notify(self, title, body="", kind="ok"):
        self.messages.append((title, body, kind))


class FakeEvent:
    def __init__(self, path, is_directory=False):
        self.src_path = str(path)
        self.is_directory = is_directory


@pytest.mark.parametrize("size", [16, 26, 64])
def test_make_icon_size(size):
    img = tray_app.make_icon(size)
    assert img.size == (size, size)
    assert img.mode == "RGBA"


class InlineThread:
    """Runs the target immediately instead of in a background thread."""
    def __init__(self, target, args=(), daemon=None):
        self._target, self._args = target, args

    def start(self):
        self._target(*self._args)


def test_handler_ignores_other_extensions_and_dirs(tmp_path, monkeypatch):
    started = []
    monkeypatch.setattr(tray_app.UploadHandler, "_run", lambda self, p: started.append(p))
    monkeypatch.setattr(tray_app.threading, "Thread", InlineThread)
    h = tray_app.UploadHandler("tok", RecordingNotifier(), {".pm4u"})

    h.on_created(FakeEvent(tmp_path / "a.stl"))
    h.on_created(FakeEvent(tmp_path / "dir.pm4u", is_directory=True))
    h.on_created(FakeEvent(tmp_path / "b.PM4U"))
    assert started == [tmp_path / "b.PM4U"]


def test_do_upload_notifies_success(monkeypatch, tmp_path):
    monkeypatch.setattr(tray_app, "upload_and_track", lambda p, t: True)
    monkeypatch.setattr(tray_app, "free_storage", lambda t: "3.0 GB free")
    nm = RecordingNotifier()
    tray_app._do_upload(tmp_path / "a.pm4u", "tok", nm)
    assert nm.messages == [
        ("Uploading…", "a.pm4u", "upload"),
        ("Uploaded ✓", "a.pm4u\n3.0 GB free", "ok"),
    ]


def test_do_upload_notifies_exception(monkeypatch, tmp_path):
    def boom(p, t):
        raise ConnectionError("offline")
    monkeypatch.setattr(tray_app, "upload_and_track", boom)
    nm = RecordingNotifier()
    tray_app._do_upload(tmp_path / "a.pm4u", "tok", nm)
    assert nm.messages[-1] == ("Upload failed", "a.pm4u", "error")


def test_free_storage_formats_gb(monkeypatch):
    monkeypatch.setattr(tray_app, "_api_post", lambda t, ep, p: {
        "data": {"total_size": 8 * 1_073_741_824, "used_size": 3 * 1_073_741_824}})
    assert tray_app.free_storage("tok") == "5.0 GB free"


def test_free_storage_none_when_api_fails(monkeypatch):
    def boom(*a):
        raise RuntimeError
    monkeypatch.setattr(tray_app, "_api_post", boom)
    assert tray_app.free_storage("tok") is None


def test_catch_up_uploads_only_newer_files_oldest_first(tmp_path, monkeypatch):
    import os
    old, new1, new2 = (tmp_path / n for n in ("old.pm4u", "new1.pm4u", "new2.pm4u"))
    for f in (old, new1, new2):
        f.write_bytes(b"x")
    os.utime(old, (1000, 1000))
    os.utime(new2, (3000, 3000))
    os.utime(new1, (2500, 2500))
    config.save({"watch_folders": [str(tmp_path)], "watch_extensions": [".pm4u"]})
    monkeypatch.setattr(tray_app, "load_last_upload_time", lambda: 2000.0)

    done = []
    monkeypatch.setattr(tray_app, "_do_upload", lambda p, t, nm: done.append(p.name))
    tray_app._catch_up("tok", RecordingNotifier())
    assert done == ["new1.pm4u", "new2.pm4u"]


@macos_only
def test_mac_notification_passes_text_as_argv(monkeypatch):
    calls = []
    monkeypatch.setattr(tray_app.subprocess, "Popen",
                        lambda args, **kw: calls.append(args))
    tray_app.NotificationManager().notify('Say "hi"\nnow', "x\" & do shell script \"rm")
    args = calls[0]
    assert args[0] == "osascript"
    # title/body are separate argv entries, never spliced into the script
    assert args[-2:] == ['Say "hi" now', "x\" & do shell script \"rm"]
    assert all("rm" not in a for a in args[:-2])


@macos_only
def test_mac_osascript_notification_script_compiles():
    import subprocess
    r = subprocess.run(
        ["osacompile", "-o", "/dev/null",
         "-e", "on run {t, b}", "-e", "display notification b with title t", "-e", "end run"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr


@macos_only
def test_watcher_uploads_file_dropped_into_folder(tmp_path, monkeypatch):
    """Real FSEvents observer: a new .pm4u in a watched folder reaches the uploader."""
    watch = tmp_path / "watch"
    watch.mkdir()
    config.save({"watch_folders": [str(watch)], "watch_extensions": [".pm4u"]})
    monkeypatch.setattr(tray_app, "wait_until_stable", lambda p: True)

    uploaded = threading.Event()
    got = []

    def fake_do_upload(p, token, nm):
        got.append((p.name, token))
        uploaded.set()

    monkeypatch.setattr(tray_app, "_do_upload", fake_do_upload)
    wm = tray_app.WatcherManager("tok", RecordingNotifier())
    wm.start()
    try:
        time.sleep(0.5)
        (watch / "ignored.txt").write_text("no")
        (watch / "model.pm4u").write_bytes(b"sliced")
        assert uploaded.wait(10), "FSEvents did not report the new file"
    finally:
        wm.stop()
    # FSEvents may report the same file twice; the .txt must never show up
    assert set(got) == {("model.pm4u", "tok")}


@macos_only
def test_watcher_add_and_remove_folder(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    config.save({"watch_folders": [str(a)], "watch_extensions": [".pm4u"]})
    wm = tray_app.WatcherManager("tok", RecordingNotifier())
    wm.start()
    try:
        wm.add_folder(b)
        wm.add_folder(tmp_path / "missing")
        assert config.load()["watch_folders"] == [str(a), str(b)]
        wm.remove_folder(a)
        assert config.load()["watch_folders"] == [str(b)]
        assert list(wm._watches) == [str(b)]
    finally:
        wm.stop()


def _walk_menu(menu):
    """Force pystray to build every item, like the tray backend does on open."""
    for item in menu.items:
        assert item.visible in (True, False)
        if item.submenu:
            yield from _walk_menu(item.submenu)
        yield item


def test_build_menu_is_accepted_by_pystray(tmp_path):
    # pystray rejects actions with more than two positional parameters; this
    # crashed the app on macOS where the menu is built at startup.
    config.save({"watch_folders": [str(tmp_path)]})
    wm = tray_app.WatcherManager("tok", RecordingNotifier())
    menu = tray_app._build_menu(wm, RecordingNotifier())
    texts = [i.text for i in _walk_menu(menu)]
    assert "Open in Finder" in texts or "Open in Explorer" in texts
    assert "Remove" in texts and "Quit" in texts


def test_folder_menu_actions_target_their_folder(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    config.save({"watch_folders": [str(a), str(b)]})
    opened, removed = [], []
    monkeypatch.setattr(tray_app, "_open_path", opened.append)
    wm = tray_app.WatcherManager("tok", RecordingNotifier())
    monkeypatch.setattr(wm, "remove_folder", removed.append)

    menu = tray_app._build_menu(wm, RecordingNotifier())
    items = list(_walk_menu(menu))
    for item in items:
        if item.text in ("Open in Finder", "Open in Explorer", "Remove"):
            item(None)
    assert opened == [a, b]
    assert removed == [a, b]
