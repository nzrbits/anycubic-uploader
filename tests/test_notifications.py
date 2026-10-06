import sys
from unittest.mock import Mock

import pytest

import notifications

macos_only = pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")


@pytest.mark.parametrize("size", [16, 26, 64])
def test_make_icon(size):
    image = notifications.make_icon(size)
    assert image.size == (size, size)
    assert image.mode == "RGBA"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Tk queue")
def test_windows_dialog_can_be_queued_before_root_exists():
    manager = notifications.NotificationManager()
    callback = Mock()
    manager.schedule_on_main(callback)
    assert manager._q.get_nowait() is callback
    callback.assert_not_called()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Tk queue")
def test_windows_callbacks_wait_for_mainloop(monkeypatch):
    manager = notifications.NotificationManager()
    root = Mock()
    poll = Mock()
    monkeypatch.setattr(notifications.tk, "Tk", lambda: root)
    monkeypatch.setattr(manager, "_poll", poll)
    root.mainloop.side_effect = lambda: poll.assert_not_called()
    manager.run()
    root.after.assert_called_once_with(0, poll)
    root.destroy.assert_called_once()


@macos_only
def test_mac_notification_passes_text_as_argv(monkeypatch):
    calls = []
    monkeypatch.setattr(
        notifications.subprocess, "Popen", lambda args, **kw: calls.append(args)
    )
    notifications.NotificationManager().notify(
        'Say "hi"\nnow', 'x" & do shell script "bad'
    )
    assert calls[0][-2:] == ['Say "hi" now', 'x" & do shell script "bad']
    assert all("bad" not in arg for arg in calls[0][:-2])


@macos_only
def test_mac_notification_script_compiles():
    import subprocess

    result = subprocess.run(
        [
            "osacompile",
            "-o",
            "/dev/null",
            "-e",
            "on run {t, b}",
            "-e",
            "display notification b with title t",
            "-e",
            "end run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
