"""Tray menu and folder watches."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import threading
import tkinter as tk
import tkinter.messagebox as mb
import webbrowser
from pathlib import Path

import pystray
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

import config as cfg
from notifications import IS_MAC, IS_WIN, NotificationManager, make_icon
from settings_dialog import open_settings
from storage import DATA_DIR, configure_logging
from upload_queue import Result, UploadQueue
from uploader import free_storage, log

APP = "Anycubic Uploader"
FAQ_URL = "https://github.com/nzrbits/anycubic-uploader/blob/master/docs/faq.md"
SCAN_INTERVAL = 30
logger = logging.getLogger(__name__)


class UploadHandler(FileSystemEventHandler):
    def __init__(self, uploads: UploadQueue):
        self._uploads = uploads

    def on_created(self, event):
        if not event.is_directory:
            self._uploads.submit(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._uploads.submit(Path(event.dest_path))

    def on_modified(self, event):
        if not event.is_directory:
            self._uploads.submit(Path(event.src_path))


class WatcherManager:
    def __init__(self, nm: NotificationManager):
        self._nm = nm
        self._observer = Observer()
        self._watches: dict[Path, ObservedWatch] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._rescan = threading.Event()
        self._uploads = UploadQueue(
            self._finished, lambda path: nm.notify("Uploading", path.name, "upload")
        )
        self._scanner = threading.Thread(
            target=self._scan_loop, name="folder-scan", daemon=True
        )

    def _finished(self, path: Path, result: Result) -> None:
        if result == Result.UPLOADED:
            free = free_storage(cfg.load_token())
            self._nm.notify("Uploaded", path.name + (f"\n{free}" if free else ""))
        elif result == Result.FAILED:
            self._nm.notify("Upload failed", path.name, "error")

    def start(self) -> None:
        self._sync_watches()
        self._observer.start()
        self._scanner.start()

    def _schedule(self, folder: Path) -> None:
        watch = self._observer.schedule(
            UploadHandler(self._uploads), str(folder), recursive=False
        )
        self._watches[folder] = watch
        log.info("Watching %s", folder)

    def _sync_watches(self) -> None:
        with self._lock:
            if self._stop.is_set():
                return
            configured = set(cfg.get_watch_folders())
            unavailable = {folder for folder in self._watches if not folder.is_dir()}
            for folder in (set(self._watches) - configured) | unavailable:
                self._observer.unschedule(self._watches.pop(folder))
            for folder in configured - set(self._watches):
                if folder.is_dir():
                    try:
                        self._schedule(folder)
                    except OSError:
                        log.warning("Cannot watch %s", folder, exc_info=True)

    def _scan_loop(self) -> None:
        while not self._stop.is_set():
            self._rescan.clear()
            try:
                self._sync_watches()
                self._uploads.scan()
            except Exception:
                logger.exception("Folder scan failed")
            if not self._stop.is_set():
                self._rescan.wait(SCAN_INTERVAL)

    def upload_pending(self) -> None:
        self._rescan.set()

    def stop(self) -> None:
        self._stop.set()
        self._rescan.set()
        self._observer.stop()
        if self._observer.is_alive():
            self._observer.join()
        if self._scanner.is_alive():
            self._scanner.join()
        self._uploads.stop()


def _open_path(path: Path) -> None:
    if IS_WIN:
        os.startfile(str(path))
    else:
        subprocess.Popen(["open" if IS_MAC else "xdg-open", str(path)])


def _build_menu(wm: WatcherManager, nm: NotificationManager):
    def settings(icon, item):
        try:
            if not open_settings(wm.upload_pending):
                nm.notify("Settings already open")
        except OSError:
            logger.exception("Could not open settings")
            nm.notify("Could not open settings", kind="error")

    def upload_pending(icon, item):
        wm.upload_pending()
        nm.notify("Checking folders", kind="upload")

    def on_quit(icon, item):
        def stop():
            try:
                wm.stop()
            finally:
                nm.stop()
                icon.stop()

        threading.Thread(target=stop, name="app-stop", daemon=True).start()

    return pystray.Menu(
        pystray.MenuItem(APP, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Settings", settings),
        pystray.MenuItem("Upload pending files", upload_pending),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("FAQ", lambda icon, item: webbrowser.open(FAQ_URL)),
        pystray.MenuItem(
            "Open log", lambda icon, item: _open_path(DATA_DIR / "watcher.log")
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=APP)
    parser.add_argument("--upload-existing", action="store_true")
    parser.add_argument("--settings", action="store_true")
    args = parser.parse_args()
    if args.settings:
        from settings_dialog import main as edit_settings

        return edit_settings()
    configure_logging()
    if args.upload_existing:
        from upload_existing import main as bulk_upload

        return bulk_upload()
    nm = NotificationManager()
    try:
        token = cfg.load_token()
    except (OSError, cfg.ConfigError) as error:
        root = tk.Tk()
        root.withdraw()
        try:
            mb.showerror(APP, str(error), parent=root)
        finally:
            root.destroy()
        return 1
    if not token:
        nm.notify(
            "No token configured",
            "Open FAQ for browser steps.\nPaste the token in Settings.",
            "error",
        )
    wm = WatcherManager(nm)
    icon = pystray.Icon(APP, make_icon(64), APP)
    icon.menu = _build_menu(wm, nm)
    try:
        wm.start()
        if IS_WIN:
            threading.Thread(target=icon.run, name="tray-ui", daemon=True).start()
            nm.run()
        else:
            icon.run(setup=lambda ic: ic.__setattr__("visible", True))
    finally:
        wm.stop()
        icon.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
