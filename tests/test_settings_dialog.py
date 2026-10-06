import sys
from unittest.mock import Mock

import pytest

import config
import settings_dialog


def test_save_updates_folders_extensions_and_token(tmp_path):
    original = config.load()
    folders = [str(tmp_path / "prints")]
    settings_dialog.save_settings(original, folders, " .PM4U, .gcode, ", " new ")
    assert config.load() == {
        "watch_folders": folders,
        "watch_extensions": [".pm4u", ".gcode"],
        "token": "new",
    }


def test_invalid_edit_preserves_settings():
    config.save_token("old")
    original = config.load()
    before = config.CONFIG_FILE.read_bytes()
    with pytest.raises(config.ConfigError):
        settings_dialog.save_settings(original, [], "*.pm4u", "new")
    assert config.CONFIG_FILE.read_bytes() == before


def test_unedited_fields_keep_concurrent_changes():
    original = config.load()
    config.save_token("renewed")
    settings_dialog.save_settings(original, [], ".pm4u", original["token"])
    assert config.load_token() == "renewed"
    assert config.get_watch_folders() == []


def test_conflicting_edit_is_rejected_atomically():
    original = config.load()
    config.save_token("renewed")
    with pytest.raises(config.ConfigError, match="changed while"):
        settings_dialog.save_settings(original, [], ".gcode", "replacement")
    assert config.load_token() == "renewed"
    assert config.get_watch_folders()
    assert config.get_watch_extensions() == {".pm4u"}


@pytest.mark.parametrize("frozen", [False, True])
def test_open_settings_launches_editor_and_rescans_on_close(monkeypatch, frozen):
    process = Mock()
    popen = Mock(return_value=process)
    thread = Mock()
    thread_factory = Mock(return_value=thread)
    monkeypatch.setattr(settings_dialog, "_process", None)
    monkeypatch.setattr(settings_dialog.sys, "frozen", frozen, raising=False)
    monkeypatch.setattr(settings_dialog.subprocess, "Popen", popen)
    monkeypatch.setattr(settings_dialog.threading, "Thread", thread_factory)
    rescan = Mock()
    assert settings_dialog.open_settings(rescan)
    command = popen.call_args.args[0]
    assert command[0] == sys.executable
    assert command[1] == ("--settings" if frozen else settings_dialog.__file__)
    assert popen.call_args.kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    rescan.assert_not_called()
    thread_factory.call_args.kwargs["target"]()
    process.wait.assert_called_once()
    rescan.assert_called_once()
    thread.start.assert_called_once()


def test_open_settings_does_not_duplicate_window(monkeypatch):
    monkeypatch.setattr(settings_dialog, "_process", Mock(poll=Mock(return_value=None)))
    popen = Mock()
    monkeypatch.setattr(settings_dialog.subprocess, "Popen", popen)
    assert not settings_dialog.open_settings(Mock())
    popen.assert_not_called()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows desktop Tk")
def test_dialog_save_and_cancel(monkeypatch, tmp_path):
    real_tk = settings_dialog.tk.Tk
    folders = [str(tmp_path / "prints")]
    initial = config.load()
    errors = []
    applied_icons = []
    action = "Save"

    def make_root():
        root = real_tk()
        root.withdraw()
        native_iconphoto = root.iconphoto

        def apply_icons(default, *images):
            native_iconphoto(default, *images)
            applied_icons.append(
                (
                    default,
                    [
                        root.tk.call(str(image), "get", 32, 20)
                        for image in images
                        if image.width() == 64
                    ],
                )
            )

        root.iconphoto = apply_icons

        def edit():
            try:
                frame = root.winfo_children()[0]
                widgets = frame.winfo_children()
                folder_list = next(
                    w for w in widgets if isinstance(w, settings_dialog.tk.Listbox)
                )
                folder_list.delete(0, settings_dialog.tk.END)
                folder_list.insert(settings_dialog.tk.END, folders[0])
                entries = [
                    w for w in widgets if isinstance(w, settings_dialog.ttk.Entry)
                ]
                for entry, value in zip(entries, [".pm4u, .gcode", "new"], strict=True):
                    entry.delete(0, settings_dialog.tk.END)
                    entry.insert(0, value)
                buttons = [
                    button for widget in widgets for button in widget.winfo_children()
                ]
                next(b for b in buttons if b.cget("text") == action).invoke()
            except (settings_dialog.tk.TclError, StopIteration, ValueError) as error:
                errors.append(error)
                root.destroy()

        root.after(10, edit)
        root.after(5000, root.destroy)
        return root

    monkeypatch.setattr(settings_dialog.tk, "Tk", make_root)
    action = "Cancel"
    assert settings_dialog.main() == 0
    assert config.load() == initial
    action = "Save"
    assert settings_dialog.main() == 0
    assert not errors
    assert applied_icons == [(True, [(255, 148, 60)]), (True, [(255, 148, 60)])]
    assert config.load()["watch_folders"] == folders
    assert config.load_token() == "new"
    assert config.get_watch_extensions() == {".pm4u", ".gcode"}
