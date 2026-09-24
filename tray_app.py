"""Anycubic Cloud PM4U Auto-Uploader — Tray App with custom toast notifications."""

import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path

import pystray
from PIL import Image, ImageDraw, ImageTk
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

sys.path.insert(0, str(Path(__file__).parent))
from uploader import (
    WATCH_EXTENSIONS, WATCH_FOLDER,
    load_last_upload_time, load_token,
    upload_and_track, wait_until_stable,
    _api_post, log,
)

APP    = "Anycubic Uploader"
TRANSP = "#010101"   # color-key for transparent corners
DARK   = "#13131f"
STATUS_COLORS = {"upload": "#60a5fa", "ok": "#22c55e", "error": "#ef4444"}


# ── icon ──────────────────────────────────────────────────────────────────────

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


# ── custom toast notification ─────────────────────────────────────────────────

def _fill_rounded_rect(cvs: tk.Canvas, x1, y1, x2, y2, r: int, fill: str):
    d = 2 * r
    for ax, ay, start in [(x1, y1, 90), (x2-d, y1, 0), (x2-d, y2-d, 270), (x1, y2-d, 180)]:
        cvs.create_arc(ax, ay, ax+d, ay+d, start=start, extent=90, fill=fill, outline="")
    cvs.create_rectangle(x1+r, y1,   x2-r, y2,   fill=fill, outline="")
    cvs.create_rectangle(x1,   y1+r, x2,   y2-r, fill=fill, outline="")


class Toast:
    W = 300

    def __init__(self, root: tk.Tk, title: str, body: str, kind: str):
        body_lines = [l for l in body.split("\n") if l] if body else []
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

        # card background
        _fill_rounded_rect(cvs, 0, 0, self.W, self.H, 14, DARK)

        # subtle left accent bar
        col = STATUS_COLORS.get(kind, STATUS_COLORS["ok"])
        _fill_rounded_rect(cvs, 4, 12, 8, self.H - 12, 2, col)

        # mini cube icon
        icon_img = make_icon(26)
        icon_ph  = ImageTk.PhotoImage(icon_img)
        cvs.create_image(20, self.H // 2, image=icon_ph, anchor="w")
        cvs._icon_ref = icon_ph  # prevent GC

        # title
        cvs.create_text(54, 22, text=title, anchor="w",
                        font=("Segoe UI Semibold", 10), fill="#f1f5f9")

        # body lines
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
    """Thread-safe toast dispatcher. Run nm.run() from the main thread."""

    def __init__(self):
        self._q    = queue.Queue()
        self._root: tk.Tk | None = None

    def notify(self, title: str, body: str = "", kind: str = "ok"):
        """Call from any thread."""
        self._q.put((title, body, kind))

    def _poll(self):
        try:
            while True:
                Toast(self._root, *self._q.get_nowait())
        except queue.Empty:
            pass
        self._root.after(80, self._poll)

    def run(self):
        """Blocks — call from main thread."""
        self._root = tk.Tk()
        self._root.withdraw()
        self._poll()
        self._root.mainloop()

    def stop(self):
        if self._root:
            self._root.after(0, self._root.quit)


# ── Anycubic cloud helpers ────────────────────────────────────────────────────

def free_storage(token: str) -> str | None:
    for ep in ("/v2/cloud_storage/storageInfo", "/v2/profile/storageInfo"):
        try:
            data  = _api_post(token, ep, {}).get("data") or {}
            total = data.get("total_size") or data.get("totalSize") or 0
            used  = data.get("used_size")  or data.get("usedSize")  or 0
            if total:
                return f"{(total - used) / 1_073_741_824:.1f} GB frei"
        except Exception:
            pass
    return None


# ── upload logic ──────────────────────────────────────────────────────────────

def _do_upload(path: Path, token: str, nm: NotificationManager):
    nm.notify("Lade hoch …", path.name, "upload")
    try:
        ok = upload_and_track(path, token)
    except Exception as e:
        log.error("Upload-Fehler bei %s: %s", path.name, e)
        nm.notify("Upload fehlgeschlagen", path.name, "error")
        return
    if ok:
        free = free_storage(token)
        nm.notify("Hochgeladen ✓", path.name + (f"\n{free}" if free else ""), "ok")
    else:
        nm.notify("Upload fehlgeschlagen", path.name, "error")


class UploadHandler(FileSystemEventHandler):
    def __init__(self, token: str, nm: NotificationManager):
        self.token = token
        self.nm    = nm

    def on_created(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() not in WATCH_EXTENSIONS:
            return
        threading.Thread(target=self._run, args=(p,), daemon=True).start()

    def _run(self, p: Path):
        log.info("Neue Datei: %s", p.name)
        if not wait_until_stable(p):
            log.warning("Datei unvollständig: %s", p.name)
            return
        _do_upload(p, self.token, self.nm)


def _catch_up(token: str, nm: NotificationManager):
    last   = load_last_upload_time()
    missed = sorted(
        (f for ext in WATCH_EXTENSIONS for f in WATCH_FOLDER.glob(f"*{ext}")
         if f.stat().st_mtime > last),
        key=lambda f: f.stat().st_mtime,
    )
    if not missed:
        log.info("Keine verpassten Dateien.")
        return
    log.info("Nachholen: %d Datei(en).", len(missed))
    for p in missed:
        _do_upload(p, token, nm)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    token = load_token()
    if not token:
        root = tk.Tk()
        root.withdraw()
        import tkinter.messagebox as mb
        mb.showerror(APP, "Kein Token gefunden.\nBitte start.ps1 ausführen.")
        root.destroy()
        return

    nm = NotificationManager()

    observer = Observer()
    observer.schedule(UploadHandler(token, nm), str(WATCH_FOLDER), recursive=False)
    observer.start()

    icon = pystray.Icon(APP, make_icon(64), APP)

    def on_quit(ic, _):
        observer.stop()
        nm.stop()
        ic.stop()

    icon.menu = pystray.Menu(
        pystray.MenuItem(APP,           None,  enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Log öffnen",  lambda i, _: os.startfile(
            str(Path(__file__).parent / "watcher.log"))),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Beenden",     on_quit),
    )

    threading.Thread(target=icon.run,    daemon=True).start()
    threading.Thread(target=_catch_up,   args=(token, nm), daemon=True).start()

    log.info("Tray-App gestartet – beobachte %s", WATCH_FOLDER)
    nm.run()   # blocks: tkinter mainloop in main thread


if __name__ == "__main__":
    main()
