"""Enter an Anycubic token without reading or closing browser profiles."""

from __future__ import annotations

import tkinter as tk
import tkinter.messagebox as mb
import tkinter.simpledialog as sd

import config

ANYCUBIC_URL = "https://cloud-universe.anycubic.com/file"


def prompt_token() -> bool:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        mb.showinfo(
            "Anycubic Token Setup",
            "Open cloud-universe.anycubic.com/file and log in.\n\n"
            "Open your browser's developer tools.\n"
            "In Application (Storage in Firefox), select Local Storage\n"
            "for cloud-universe.anycubic.com. Copy the XX-Token value.\n\n"
            "Click OK to paste your token.",
            parent=root,
        )
        token = sd.askstring(
            "Anycubic Token Setup", "Paste your XX-Token:", parent=root, show="*"
        )
        if not token or not token.strip():
            return False
        config.save_token(token.strip())
        return True
    except (config.ConfigError, OSError) as error:
        mb.showerror("Anycubic Token Setup", str(error), parent=root)
        return False
    finally:
        root.destroy()


def main() -> int:
    return 0 if prompt_token() else 1


if __name__ == "__main__":
    raise SystemExit(main())
