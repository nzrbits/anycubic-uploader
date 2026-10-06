"""Edit watched folders, extensions and token in a separate window."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk

import config

_lock = threading.Lock()
_process: subprocess.Popen | None = None


def save_settings(
    original: config.Settings, folders: list[str], extensions: str, token: str
) -> None:
    edited = {
        "watch_folders": folders,
        "watch_extensions": [
            part.strip().lower() for part in extensions.split(",") if part.strip()
        ],
        "token": token.strip(),
    }
    changes = {key: value for key, value in edited.items() if value != original[key]}
    config.apply_changes(changes, original)


def open_settings(on_close: Callable[[], None]) -> bool:
    global _process
    with _lock:
        if _process is not None and _process.poll() is None:
            return False
        command = (
            [sys.executable, "--settings"]
            if getattr(sys, "frozen", False)
            else [sys.executable, str(Path(__file__))]
        )
        # The editor must keep its bundle files if the tray app exits first.
        environment = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
        _process = subprocess.Popen(command, env=environment)
        process = _process

    def finished():
        process.wait()
        on_close()

    threading.Thread(target=finished, name="settings-window", daemon=True).start()
    return True


def main() -> int:
    root = tk.Tk()
    root.title("Anycubic Uploader settings")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    try:
        initial = config.load()
    except (config.ConfigError, OSError) as error:
        mb.showerror("Cannot read settings", str(error), parent=root)
        root.destroy()
        return 1
    frame = ttk.Frame(root, padding=16)
    frame.grid(sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)
    ttk.Label(frame, text="Folders to watch").grid(row=0, column=0, sticky="w")
    folders = tk.Listbox(
        frame, height=6, width=65, selectmode=tk.EXTENDED, exportselection=False
    )
    folders.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
    scroll = ttk.Scrollbar(frame, orient="vertical", command=folders.yview)
    scroll.grid(row=1, column=1, sticky="ns")
    folders.configure(yscrollcommand=scroll.set)
    for folder in initial["watch_folders"]:
        folders.insert(tk.END, folder)

    def add_folder():
        chosen = fd.askdirectory(title="Select a folder to watch", parent=root)
        if chosen and chosen not in folders.get(0, tk.END):
            folders.insert(tk.END, chosen)

    def remove_folders():
        for index in reversed(folders.curselection()):
            folders.delete(index)

    actions = ttk.Frame(frame)
    actions.grid(row=2, column=0, sticky="w", pady=(6, 12))
    ttk.Button(actions, text="Add folder", command=add_folder).pack(side="left")
    ttk.Button(actions, text="Remove selected", command=remove_folders).pack(
        side="left", padx=6
    )
    ttk.Label(frame, text="File extensions (comma separated)").grid(
        row=3, column=0, sticky="w"
    )
    extensions = tk.StringVar(root, value=", ".join(initial["watch_extensions"]))
    ttk.Entry(frame, textvariable=extensions).grid(
        row=4, column=0, sticky="ew", pady=(6, 12)
    )
    ttk.Label(frame, text="Anycubic token").grid(row=5, column=0, sticky="w")
    token = tk.StringVar(root, value=initial["token"])
    ttk.Entry(frame, textvariable=token, show="*").grid(
        row=6, column=0, sticky="ew", pady=(6, 12)
    )
    ttk.Label(frame, text="Changes apply after Save. Current uploads continue.").grid(
        row=7, column=0, sticky="w"
    )
    buttons = ttk.Frame(frame)
    buttons.grid(row=8, column=0, sticky="e", pady=(12, 0))

    def save():
        try:
            save_settings(
                initial, list(folders.get(0, tk.END)), extensions.get(), token.get()
            )
        except (config.ConfigError, OSError) as error:
            mb.showerror("Cannot save settings", str(error), parent=root)
            return
        root.destroy()

    ttk.Button(buttons, text="Cancel", command=root.destroy).pack(side="left", padx=6)
    ttk.Button(buttons, text="Save", command=save).pack(side="left")
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
