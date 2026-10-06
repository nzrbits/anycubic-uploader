"""Tray artwork, notifications and folder dialogs for each platform."""

from __future__ import annotations

import logging
import platform
import queue
import subprocess
import threading
import tkinter as tk
import tkinter.filedialog as fd
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"
TRANSP = "#010101"
DARK = "#13131f"
STATUS_COLORS = {"upload": "#60a5fa", "ok": "#22c55e", "error": "#ef4444"}
logger = logging.getLogger(__name__)


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=(20, 20, 31)
    )

    def pt(x, y):
        return round(x * size / 64), round(y * size / 64)

    A, B, C = pt(32, 12), pt(51, 23), pt(32, 34)
    D, E, F = pt(13, 23), pt(51, 49), pt(32, 60)
    G = pt(13, 49)

    d.polygon([A, B, C, D], fill=(255, 148, 60))
    d.polygon([B, E, F, C], fill=(214, 98, 32))
    d.polygon([D, C, F, G], fill=(162, 68, 18))

    def lerp(p1, p2, t):
        return round(p1[0] + (p2[0] - p1[0]) * t), round(p1[1] + (p2[1] - p1[1]) * t)

    for t in (0.28, 0.55, 0.78):
        d.line([lerp(B, E, t), lerp(C, F, t)], fill=(190, 78, 22), width=1)
        d.line([lerp(D, G, t), lerp(C, F, t)], fill=(136, 52, 10), width=1)

    return img


if IS_WIN:

    def _fill_rounded_rect(cvs: tk.Canvas, x1, y1, x2, y2, r: int, fill: str):
        d = 2 * r
        for ax, ay, start in [
            (x1, y1, 90),
            (x2 - d, y1, 0),
            (x2 - d, y2 - d, 270),
            (x1, y2 - d, 180),
        ]:
            cvs.create_arc(
                ax, ay, ax + d, ay + d, start=start, extent=90, fill=fill, outline=""
            )
        cvs.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
        cvs.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")

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

            cvs = tk.Canvas(
                win, width=self.W, height=self.H, bg=TRANSP, highlightthickness=0
            )
            cvs.pack()

            _fill_rounded_rect(cvs, 0, 0, self.W, self.H, 14, DARK)
            col = STATUS_COLORS.get(kind, STATUS_COLORS["ok"])
            _fill_rounded_rect(cvs, 4, 12, 8, self.H - 12, 2, col)

            icon_img = make_icon(26)
            icon_ph = ImageTk.PhotoImage(icon_img)
            cvs.create_image(20, self.H // 2, image=icon_ph, anchor="w")
            cvs._icon_ref = icon_ph  # prevent GC

            cvs.create_text(
                54,
                22,
                text=title,
                anchor="w",
                font=("Segoe UI Semibold", 10),
                fill="#f1f5f9",
            )
            for i, line in enumerate(body_lines):
                cvs.create_text(
                    54,
                    39 + i * 17,
                    text=line,
                    anchor="w",
                    font=("Segoe UI", 9),
                    fill="#64748b",
                )

            self._win = win
            self._fade(0.0, 0.92, ms=200, done=lambda: win.after(3800, self._out))

        def _out(self):
            self._fade(0.92, 0.0, ms=350, done=self._win.destroy)

        def _fade(
            self, frm: float, to: float, steps: int = 14, ms: int = 200, done=None
        ):
            delay = max(1, ms // steps)
            delta = (to - frm) / steps

            def tick(a, n):
                if n <= 0:
                    try:
                        self._win.attributes("-alpha", to)
                    except tk.TclError:
                        pass
                    if done:
                        done()
                    return
                try:
                    self._win.attributes("-alpha", a)
                    self._win.after(delay, tick, a + delta, n - 1)
                except tk.TclError:
                    pass

            tick(frm, steps)

    class NotificationManager:
        """Tk owns the main thread; callbacks from the tray go through the queue."""

        def __init__(self):
            self._q: queue.Queue = queue.Queue()
            self._root: tk.Tk | None = None

        def notify(self, title: str, body: str = "", kind: str = "ok"):
            self._q.put((title, body, kind))

        def schedule_on_main(self, fn) -> None:
            self._q.put(fn)

        def _poll(self):
            try:
                while True:
                    item = self._q.get_nowait()
                    try:
                        if callable(item):
                            item()
                        else:
                            Toast(self._root, *item)
                    except Exception:
                        logger.exception("Could not run notification callback")
            except queue.Empty:
                pass
            self._root.after(80, self._poll)

        def run(self):
            self._root = tk.Tk()
            self._root.withdraw()
            self._root.after(0, self._poll)
            try:
                self._root.mainloop()
            finally:
                self._root.destroy()
                self._root = None

        def select_folder(self, selected):
            def pick():
                folder = fd.askdirectory(
                    title="Select a folder to watch", parent=self._root
                )
                if folder:
                    selected(Path(folder))

            self.schedule_on_main(pick)

        def stop(self):
            self.schedule_on_main(lambda: self._root.quit())

else:

    class NotificationManager:  # type: ignore[no-redef]
        def notify(self, title: str, body: str = "", kind: str = "ok"):
            try:
                safe_title = title.replace("\n", " ")
                safe_body = body.replace("\n", " ")
                if IS_MAC:
                    # filenames may contain quotes; keep them out of the script
                    subprocess.Popen(
                        [
                            "osascript",
                            "-e",
                            "on run {t, b}",
                            "-e",
                            "display notification b with title t",
                            "-e",
                            "end run",
                            safe_title,
                            safe_body,
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.Popen(
                        ["notify-send", safe_title, safe_body],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            except OSError:
                logger.exception("Could not show notification")

        def select_folder(self, selected):
            def pick():
                args = (
                    [
                        "osascript",
                        "-e",
                        'POSIX path of (choose folder with prompt "Select a folder to watch:")',
                    ]
                    if IS_MAC
                    else ["zenity", "--file-selection", "--directory"]
                )
                try:
                    result = subprocess.run(
                        args, capture_output=True, text=True, check=False
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        selected(Path(result.stdout.strip()))
                except OSError:
                    self.notify("Could not open folder picker", kind="error")

            threading.Thread(target=pick, daemon=True).start()

        def run(self):
            pass

        def stop(self):
            pass
