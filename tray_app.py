"""Anycubic Cloud PM4U Auto-Uploader — Tray App (Windows & macOS)."""
from __future__ import annotations

import os
import platform
import queue
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from pathlib import Path
from typing import Any

import pystray
from PIL import Image, ImageDraw, ImageTk
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import config as cfg
from uploader import (
    _api_post, load_token, log, upload_and_track, wait_until_stable,
    load_last_upload_time,
)

APP    = "Anycubic Uploader"
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"
TRANSP = "#010101"
DARK   = "#13131f"
STATUS_COLORS = {"upload": "#60a5fa", "ok": "#22c55e", "error": "#ef4444"}


# ── Icon ───────────────────────────────────────────────────────────────────────

def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1],
                        radius=int(size * 0.22), fill=(20, 20, 31))

    def pt(x, y): return round(x * size / 64), round(y * size / 64)
    A, B, C = pt(32, 12), pt(51, 23), pt(32, 34)
    D, E, F = pt(13, 23), pt(51, 49), pt(32, 60)
    G       = pt(13, 49)

    d.polygon([A, B, C, D], fill=(255, 148,  60))
    d.polygon([B, E, F, C], fill=(214,  98,  32))
    d.polygon([D, C, F, G], fill=(162,  68,  18))

    def lerp(p1, p2, t):
        return round(p1[0] + (p2[0] - p1[0]) * t), round(p1[1] + (p2[1] - p1[1]) * t)

    for t in (0.28, 0.55, 0.78):
        d.line([lerp(B, E, t), lerp(C, F, t)], fill=(190, 78, 22), width=1)
        d.line([lerp(D, G, t), lerp(C, F, t)], fill=(136, 52, 10), width=1)

    return img


# ── Notifications ──────────────────────────────────────────────────────────────

if IS_WIN:
    def _fill_rounded_rect(cvs: tk.Canvas, x1, y1, x2, y2, r: int, fill: str):
        d = 2 * r
        for ax, ay, start in [(x1, y1, 90), (x2-d, y1, 0), (x2-d, y2-d, 270), (x1, y2-d, 180)]:
            cvs.create_arc(ax, ay, ax+d, ay+d, start=start, extent=90, fill=fill, outline="")
        cvs.create_rectangle(x1+r, y1,   x2-r, y2,   fill=fill, outline="")
        cvs.create_rectangle(x1,   y1+r, x2,   y2-r, fill=fill, outline="")

    class Toast:
        W = 300

        def __init__(self, root: tk.Tk, title: str, body: str, kind: str):
            body_lines = [ln for ln in body.split("\n") if ln] if body else []
            self.H = 74 + max(0, len(body_lines) - 1) * 17

            win = tk.Toplevel(root)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.attributes("-transparentcolor", TRANSP)
            win.attributes("-alpha", 0.0)

            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            win.geometry(f"{self.W}x{self.H}+{sw - self.W - 16}+{sh - self.H - 58}")

            cvs = tk.Canvas(win, width=self.W, height=self.H,
                            bg=TRANSP, highlightthickness=0)
            cvs.pack()

            _fill_rounded_rect(cvs, 0, 0, self.W, self.H, 14, DARK)
            col = STATUS_COLORS.get(kind, STATUS_COLORS["ok"])
            _fill_rounded_rect(cvs, 4, 12, 8, self.H - 12, 2, col)

            icon_img = make_icon(26)
            icon_ph  = ImageTk.PhotoImage(icon_img)
            cvs.create_image(20, self.H // 2, image=icon_ph, anchor="w")
            cvs._icon_ref = icon_ph  # prevent GC

            cvs.create_text(54, 22, text=title, anchor="w",
                            font=("Segoe UI Semibold", 10), fill="#f1f5f9")
            for i, line in enumerate(body_lines):
                cvs.create_text(54, 39 + i * 17, text=line, anchor="w",
                                font=("Segoe UI", 9), fill="#64748b")

            self._win = win
            self._fade(0.0, 0.92, ms=200, done=lambda: win.after(3800, self._out))

        def _out(self):
            self._fade(0.92, 0.0, ms=350, done=self._win.destroy)

        def _fade(self, frm: float, to: float, steps: int = 14, ms: int = 200, done=None):
            delay = max(1, ms // steps)
            delta = (to - frm) / steps

            def tick(a, n):
                if n <= 0:
                    try:   self._win.attributes("-alpha", to)
                    except tk.TclError: pass
                    if done: done()
                    return
                try:
                    self._win.attributes("-alpha", a)
                    self._win.after(delay, tick, a + delta, n - 1)
                except tk.TclError:
                    pass

            tick(frm, steps)

    class NotificationManager:
        """Windows: custom tkinter toast overlay — must run() from main thread."""

        def __init__(self):
            self._q:    queue.Queue = queue.Queue()
            self._root: tk.Tk | None = None

        def notify(self, title: str, body: str = "", kind: str = "ok"):
            self._q.put((title, body, kind))

        def schedule_on_main(self, fn) -> None:
            if self._root:
                self._root.after(0, fn)

        def _poll(self):
            try:
                while True:
                    Toast(self._root, *self._q.get_nowait())
            except queue.Empty:
                pass
            self._root.after(80, self._poll)

        def run(self):
            self._root = tk.Tk()
            self._root.withdraw()
            self._poll()
            self._root.mainloop()

        def stop(self):
            if self._root:
                self._root.after(0, self._root.quit)

else:
    class NotificationManager:  # type: ignore[no-redef]
        """macOS/Linux: native OS notifications via osascript / notify-send."""

        def notify(self, title: str, body: str = "", kind: str = "ok"):
            try:
                clean_title = title.replace('"', "'")
                clean_body  = body.replace('"', "'").replace("\n", " ")
                if IS_MAC:
                    subprocess.Popen(
                        ["osascript", "-e",
                         f'display notification "{clean_body}" with title "{clean_title}"'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.Popen(
                        ["notify-send", clean_title, clean_body],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
            except Exception:
                pass

        def schedule_on_main(self, fn) -> None:
            threading.Thread(target=fn, daemon=True).start()

        def run(self):
            pass

        def stop(self):
            pass


# ── Cloud helpers ─────────────────────────────────────────────────────────────

def free_storage(token: str) -> str | None:
    for ep in ("/v2/cloud_storage/storageInfo", "/v2/profile/storageInfo"):
        try:
            data  = _api_post(token, ep, {}).get("data") or {}
            total = data.get("total_size") or data.get("totalSize") or 0
            used  = data.get("used_size")  or data.get("usedSize")  or 0
            if total:
                return f"{(total - used) / 1_073_741_824:.1f} GB free"
        except Exception:
            pass
    return None


# ── Upload handler ────────────────────────────────────────────────────────────

def _do_upload(path: Path, token: str, nm: NotificationManager):
    nm.notify("Uploading…", path.name, "upload")
    try:
        ok = upload_and_track(path, token)
    except Exception as e:
        log.error("Upload error for %s: %s", path.name, e)
        nm.notify("Upload failed", path.name, "error")
        return
    if ok:
        free = free_storage(token)
        nm.notify("Uploaded ✓", path.name + (f"\n{free}" if free else ""), "ok")
    else:
        nm.notify("Upload failed", path.name, "error")


class UploadHandler(FileSystemEventHandler):
    def __init__(self, token: str, nm: NotificationManager, extensions: set[str]):
        self.token      = token
        self.nm         = nm
        self.extensions = extensions

    def on_created(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() not in self.extensions:
            return
        threading.Thread(target=self._run, args=(p,), daemon=True).start()

    def _run(self, p: Path):
        log.info("New file detected: %s", p.name)
        if not wait_until_stable(p):
            log.warning("File incomplete, skipping: %s", p.name)
            return
        _do_upload(p, self.token, self.nm)


# ── Watcher manager ───────────────────────────────────────────────────────────

class WatcherManager:
    """Manages one Observer with dynamically added/removed folder watches."""

    def __init__(self, token: str, nm: NotificationManager):
        self._token    = token
        self._nm       = nm
        self._observer = Observer()
        self._watches: dict[str, Any] = {}
        self._lock     = threading.Lock()

    def start(self):
        for folder in cfg.get_watch_folders():
            if folder.exists():
                self._schedule(folder)
            else:
                log.warning("Watch folder not found, skipping: %s", folder)
        self._observer.start()

    def _schedule(self, folder: Path) -> None:
        exts    = cfg.get_watch_extensions()
        handler = UploadHandler(self._token, self._nm, exts)
        watch   = self._observer.schedule(handler, str(folder), recursive=False)
        self._watches[str(folder)] = watch
        log.info("Watching: %s", folder)

    def add_folder(self, folder: Path) -> None:
        with self._lock:
            s = str(folder)
            if s in self._watches:
                return
            if not folder.exists():
                log.warning("Folder does not exist: %s", folder)
                return
            self._schedule(folder)
            cfg.add_watch_folder(folder)

    def remove_folder(self, folder: Path) -> None:
        with self._lock:
            s = str(folder)
            if s not in self._watches:
                return
            self._observer.unschedule(self._watches.pop(s))
            cfg.remove_watch_folder(folder)
            log.info("Stopped watching: %s", folder)

    def get_folders(self) -> list[Path]:
        return cfg.get_watch_folders()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()


# ── Catch-up on missed files ──────────────────────────────────────────────────

def _catch_up(token: str, nm: NotificationManager):
    last     = load_last_upload_time()
    exts     = cfg.get_watch_extensions()
    folders  = cfg.get_watch_folders()
    missed   = sorted(
        (f for folder in folders if folder.exists()
         for ext in exts
         for f in folder.glob(f"*{ext}")
         if f.stat().st_mtime > last),
        key=lambda f: f.stat().st_mtime,
    )
    if not missed:
        log.info("No missed files.")
        return
    log.info("Catching up: %d file(s).", len(missed))
    for p in missed:
        _do_upload(p, token, nm)


# ── Folder picker ─────────────────────────────────────────────────────────────

def _pick_folder_mac() -> Path | None:
    result = subprocess.run(
        ["osascript", "-e",
         'POSIX path of (choose folder with prompt "Select a folder to watch:")'],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return None


def _open_path(path: Path) -> None:
    if IS_WIN:
        os.startfile(str(path))
    elif IS_MAC:
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ── Tray menu builder ─────────────────────────────────────────────────────────

def _build_menu(wm: WatcherManager, nm: NotificationManager, icon_ref: list):
    """Returns a fresh pystray.Menu — called each time the menu opens."""

    def folder_items():
        items = []
        for folder in wm.get_folders():
            f = folder
            label = str(f).replace(str(Path.home()), "~")
            sub = pystray.Menu(
                pystray.MenuItem(
                    "Open in Explorer" if IS_WIN else "Open in Finder",
                    lambda ic, it, fp=f: _open_path(fp),
                ),
                pystray.MenuItem(
                    "Remove",
                    lambda ic, it, fp=f: wm.remove_folder(fp),
                ),
            )
            items.append(pystray.MenuItem(label, sub))

        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Add folder…", lambda ic, it: _add_folder(wm, nm)))
        return tuple(items)

    def on_quit(ic, _):
        wm.stop()
        nm.stop()
        ic.stop()

    return pystray.Menu(
        pystray.MenuItem(APP, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Folders to watch", pystray.Menu(folder_items)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Open log",
            lambda ic, it: _open_path(Path(__file__).parent / "watcher.log"),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )


def _add_folder(wm: WatcherManager, nm: NotificationManager) -> None:
    if IS_MAC:
        def _pick():
            folder = _pick_folder_mac()
            if folder:
                wm.add_folder(folder)
                nm.notify("Folder added", str(folder).replace(str(Path.home()), "~"))
        threading.Thread(target=_pick, daemon=True).start()
    else:
        def _show_dialog():
            root_tmp = tk.Tk()
            root_tmp.withdraw()
            root_tmp.attributes("-topmost", True)
            folder = fd.askdirectory(
                title="Select a folder to watch",
                initialdir=str(Path.home()),
                parent=root_tmp,
            )
            root_tmp.destroy()
            if folder:
                wm.add_folder(Path(folder))
                nm.notify("Folder added", folder.replace(str(Path.home()), "~"))
        nm.schedule_on_main(_show_dialog)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    token = load_token()
    if not token:
        if IS_WIN or not IS_MAC:
            root = tk.Tk()
            root.withdraw()
            mb.showerror(APP,
                         "No token found.\n\nRun setup_token.py first.\n"
                         "See README for instructions.")
            root.destroy()
        else:
            subprocess.run(
                ["osascript", "-e",
                 f'display alert "{APP}" message "No token found. Run setup_token.py first."'],
                capture_output=True,
            )
        return

    nm = NotificationManager()
    wm = WatcherManager(token, nm)
    icon_ref: list = []

    icon = pystray.Icon(APP, make_icon(64), APP)
    icon.menu = _build_menu(wm, nm, icon_ref)
    icon_ref.append(icon)

    def _start_workers():
        wm.start()
        threading.Thread(target=_catch_up, args=(token, nm), daemon=True).start()
        log.info("Tray app started. Watching %d folder(s).", len(wm.get_folders()))

    if IS_WIN:
        # pystray runs in background; tkinter mainloop owns the main thread
        threading.Thread(target=icon.run, daemon=True).start()
        threading.Thread(target=_start_workers, daemon=True).start()
        nm.run()   # blocks: tkinter mainloop
    else:
        # macOS: AppKit requires pystray on the main thread
        threading.Thread(target=_start_workers, daemon=True).start()
        icon.run(setup=lambda ic: ic.__setattr__("visible", True))  # blocks


if __name__ == "__main__":
    main()
