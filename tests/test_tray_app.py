import threading
from unittest.mock import Mock

from watchdog.events import (
    DirCreatedEvent,
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

import config
import tray_app
import uploader


def test_handler_submits_created_moved_and_modified_files(tmp_path):
    uploads = Mock()
    handler = tray_app.UploadHandler(uploads)
    source, target = tmp_path / "part.tmp", tmp_path / "part.pm4u"
    handler.dispatch(FileCreatedEvent(str(target)))
    handler.dispatch(FileMovedEvent(str(source), str(target)))
    handler.dispatch(FileModifiedEvent(str(target)))
    handler.dispatch(DirCreatedEvent(str(target)))
    assert [call.args for call in uploads.submit.call_args_list] == [(target,)] * 3


def test_unavailable_configured_folder_can_be_removed(tmp_path):
    missing = tmp_path / "missing"
    config.save({"watch_folders": [str(missing)]})
    manager = tray_app.WatcherManager(Mock())
    try:
        config.apply_changes({"watch_folders": []}, config.load())
        manager._sync_watches()
        assert config.get_watch_folders() == []
        assert manager._watches == {}
    finally:
        manager.stop()


def test_saved_settings_replace_folder_watches(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    config.save({"watch_folders": [str(first)]})
    manager = tray_app.WatcherManager(Mock())
    try:
        manager._sync_watches()
        assert set(manager._watches) == {first}
        config.apply_changes({"watch_folders": [str(second)]}, config.load())
        manager._sync_watches()
        assert set(manager._watches) == {second}
    finally:
        manager.stop()


def test_real_observer_detects_file(tmp_path, monkeypatch, fake_api):
    watch = tmp_path / "watch"
    watch.mkdir()
    config.save({"token": "mock", "watch_folders": [str(watch)]})
    monkeypatch.setattr(uploader, "wait_until_stable", lambda path, cancel=None: True)
    monkeypatch.setattr(tray_app, "free_storage", lambda token: None)
    uploaded = threading.Event()
    notifier = Mock()
    notifier.notify.side_effect = lambda title, *args: (
        uploaded.set() if title == "Uploaded" else None
    )
    manager = tray_app.WatcherManager(notifier)
    manager.start()
    try:
        (watch / "part.pm4u").write_bytes(b"model")
        assert uploaded.wait(10)
    finally:
        manager.stop()
    assert len([call for call in fake_api.calls if call[0] == "PUT"]) == 1


def _walk(menu):
    for item in menu.items:
        assert item.visible in (True, False)
        if item.submenu:
            yield from _walk(item.submenu)
        yield item


def test_manual_upload_wakes_scanner_and_reloads_watches(tmp_path, monkeypatch):
    config.save({"watch_folders": []})
    manager = tray_app.WatcherManager(Mock())
    scanned = threading.Event()
    monkeypatch.setattr(manager._uploads, "scan", scanned.set)
    manager.start()
    try:
        assert scanned.wait(5)
        scanned.clear()
        config.add_watch_folder(tmp_path)
        manager.upload_pending()
        assert scanned.wait(5)
        assert tmp_path in manager._watches
    finally:
        manager.stop()


def test_menu_exposes_settings_and_manual_upload(monkeypatch):
    manager, notifier = Mock(), Mock()
    manager.get_folders.return_value = []
    editor = Mock(return_value=True)
    monkeypatch.setattr(tray_app, "open_settings", editor)
    menu = {item.text: item for item in _walk(tray_app._build_menu(manager, notifier))}
    menu["Settings"](None)
    editor.assert_called_once_with(manager.upload_pending)
    menu["Upload pending files"](None)
    manager.upload_pending.assert_called_once()
    notifier.notify.assert_called_once_with("Checking folders", kind="upload")


def test_stop_during_scan_does_not_wait_for_next_interval(monkeypatch):
    manager = tray_app.WatcherManager(Mock())
    wake = Mock()
    wake.clear.side_effect = manager._stop.set
    monkeypatch.setattr(manager, "_rescan", wake)
    monkeypatch.setattr(manager._uploads, "scan", Mock())
    try:
        manager._scan_loop()
        wake.wait.assert_not_called()
    finally:
        manager.stop()


def test_menu_has_one_entry_for_each_task_and_opens_faq(monkeypatch):
    browser = Mock(return_value=True)
    monkeypatch.setattr(tray_app.webbrowser, "open", browser)
    items = [
        item
        for item in tray_app._build_menu(Mock(), Mock()).items
        if item is not tray_app.pystray.Menu.SEPARATOR and item.text != tray_app.APP
    ]
    assert [item.text for item in items] == [
        "Settings",
        "Upload pending files",
        "FAQ",
        "Open log",
        "Quit",
    ]
    assert all(item.submenu is None for item in items)
    next(item for item in items if item.text == "FAQ")(None)
    browser.assert_called_once_with(tray_app.FAQ_URL)
