from unittest.mock import Mock

import pytest

import config
import tray_app


@pytest.fixture
def app(monkeypatch):
    notifier, watcher, icon, root = Mock(), Mock(), Mock(), Mock()
    monkeypatch.setattr(tray_app, "NotificationManager", lambda: notifier)
    monkeypatch.setattr(tray_app, "WatcherManager", lambda nm: watcher)
    monkeypatch.setattr(tray_app.pystray, "Icon", lambda *args: icon)
    monkeypatch.setattr(tray_app, "IS_WIN", True)
    monkeypatch.setattr(tray_app.threading, "Thread", Mock())
    monkeypatch.setattr(tray_app.tk, "Tk", lambda: root)
    monkeypatch.setattr(tray_app.mb, "showerror", Mock())
    monkeypatch.setattr("sys.argv", ["tray_app.py"])
    return notifier, watcher, icon, root


def test_missing_token_warns_once_and_keeps_tray_running(app):
    notifier, watcher, _icon, root = app
    assert tray_app.main() == 0
    notifier.notify.assert_called_once_with(
        "No token configured",
        "Open FAQ for browser steps.\nPaste the token in Settings.",
        "error",
    )
    watcher.start.assert_called_once()
    notifier.run.assert_called_once()
    watcher.stop.assert_called_once()
    root.withdraw.assert_not_called()


def test_existing_token_starts_without_warning_or_setup(app):
    config.save_token("existing")
    notifier, watcher, _icon, root = app
    assert tray_app.main() == 0
    notifier.notify.assert_not_called()
    watcher.start.assert_called_once()
    root.withdraw.assert_not_called()
    assert config.load_token() == "existing"


def test_corrupt_config_is_reported_without_overwriting(app):
    config.CONFIG_FILE.write_text("broken", encoding="utf-8")
    _notifier, watcher, _icon, root = app
    assert tray_app.main() == 1
    tray_app.mb.showerror.assert_called_once()
    root.destroy.assert_called_once()
    watcher.start.assert_not_called()
    assert config.CONFIG_FILE.read_text() == "broken"


def test_bulk_without_token_does_not_open_setup(app, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["tray_app.py", "--upload-existing"])
    assert tray_app.main() == 1
    assert "Settings" in capsys.readouterr().out
    notifier, _watcher, _icon, root = app
    root.withdraw.assert_not_called()
    notifier.run.assert_not_called()
