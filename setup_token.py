"""
Anycubic Token Setup
Extracts the XX-Token from your browser's local storage or lets you paste it manually.

Supported methods:
  - Windows: Microsoft Edge (automatic browser launch + LevelDB extraction)
  - Windows: Google Chrome (automatic LevelDB extraction)
  - macOS:   Google Chrome (automatic LevelDB extraction)
  - All:     Manual paste via GUI dialog (fallback / universal)
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import tkinter.simpledialog as sd
import tkinter.messagebox as mb
from pathlib import Path

import config as cfg

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

ANYCUBIC_URL = "https://cloud-universe.anycubic.com/file"
_JWT_RE      = re.compile(rb"([ey][A-Za-z0-9\-_.]{80,})")


# ── Browser paths ─────────────────────────────────────────────────────────────

def _find_edge() -> str | None:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    for base in [
        Path(r"C:\Program Files (x86)\Microsoft\EdgeCore"),
        Path(r"C:\Program Files\Microsoft\EdgeCore"),
    ]:
        if base.exists():
            hits = sorted(base.glob("*/msedge.exe"), reverse=True)
            if hits:
                return str(hits[0])
    try:
        out = subprocess.check_output(["where.exe", "msedge.exe"], text=True).strip()
        if out:
            return out.splitlines()[0]
    except Exception:
        pass
    return None


def _find_chrome_win() -> str | None:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    try:
        out = subprocess.check_output(["where.exe", "chrome.exe"], text=True).strip()
        if out:
            return out.splitlines()[0]
    except Exception:
        pass
    return None


def _find_chrome_mac() -> str | None:
    paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for p in paths:
        if Path(p).exists():
            return str(p)
    return None


# ── LevelDB extraction ────────────────────────────────────────────────────────

def _find_token_in_leveldb(folder: Path) -> str | None:
    candidates: list[str] = []
    for f in sorted(folder.iterdir()):
        if f.suffix not in (".log", ".ldb"):
            continue
        try:
            data = f.read_bytes()
        except OSError:
            continue

        if b"XX-Token" not in data and b"anycubic" not in data:
            continue

        idx = data.find(b"XX-Token")
        if idx >= 0:
            window = data[idx: idx + 512]
            m = _JWT_RE.search(window)
            if m:
                return m.group(1).decode("ascii")

        for m in _JWT_RE.finditer(data):
            candidates.append(m.group(1).decode("ascii"))

    return candidates[0] if candidates else None


def _chrome_leveldb_win() -> Path:
    return (Path(os.environ.get("LOCALAPPDATA", "")) /
            "Google" / "Chrome" / "User Data" / "Default" / "Local Storage" / "leveldb")


def _chrome_leveldb_mac() -> Path:
    return (Path.home() /
            "Library" / "Application Support" / "Google" / "Chrome" /
            "Default" / "Local Storage" / "leveldb")


# ── Browser-based extraction ──────────────────────────────────────────────────

def _extract_via_browser(exe: str, temp_profile: Path, kill_name: str) -> str | None:
    """Launch browser with a temp profile, wait for user to log in, extract token."""
    subprocess.run(
        ["taskkill", "/F", "/IM", kill_name] if IS_WIN else ["pkill", "-f", kill_name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    print(f"\nLaunching browser: {Path(exe).name}")
    proc = subprocess.Popen([
        exe,
        f"--user-data-dir={temp_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        ANYCUBIC_URL,
    ])

    print("\n>>> Log in to Anycubic Cloud in the browser window.")
    print(">>> Press Enter here when done. <<<")
    input()

    print("\nClosing browser and reading token...")
    proc.terminate()
    time.sleep(2)
    subprocess.run(
        ["taskkill", "/F", "/IM", kill_name] if IS_WIN else ["pkill", "-f", kill_name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    leveldb = temp_profile / "Default" / "Local Storage" / "leveldb"
    if not leveldb.exists():
        print(f"Error: localStorage folder not found: {leveldb}")
        return None
    return _find_token_in_leveldb(leveldb)


# ── Live Chrome profile extraction (no temp profile needed) ──────────────────

def _extract_from_live_chrome(leveldb: Path) -> str | None:
    """Read token directly from the user's existing Chrome profile (Chrome must be closed)."""
    if not leveldb.exists():
        return None
    return _find_token_in_leveldb(leveldb)


# ── Manual GUI fallback ───────────────────────────────────────────────────────

def _extract_manual() -> str | None:
    print("\nOpening manual token entry dialog...")
    print("Instructions:")
    print("  1. Open", ANYCUBIC_URL, "in any browser")
    print("  2. Log in to your Anycubic account")
    print("  3. Open DevTools (F12 or Cmd+Option+I)")
    print("  4. Go to Application > Storage > Local Storage > cloud-universe.anycubic.com")
    print("  5. Find the key 'XX-Token' and copy its value")
    print("  6. Paste it into the dialog that opens\n")

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    mb.showinfo(
        "Anycubic Token Setup",
        "1. Open cloud-universe.anycubic.com in your browser\n"
        "2. Log in to your Anycubic account\n"
        "3. Open DevTools (F12)\n"
        "4. Application → Local Storage → cloud-universe.anycubic.com\n"
        "5. Copy the value of 'XX-Token'\n\n"
        "Then click OK and paste your token.",
        parent=root,
    )

    token = sd.askstring(
        "Paste Token",
        "Paste your XX-Token here:",
        parent=root,
    )
    root.destroy()
    return token.strip() if token and token.strip() else None


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 56)
    print("  Anycubic Cloud — Token Setup")
    print("=" * 56)

    token: str | None = None

    if IS_WIN:
        edge = _find_edge()
        chrome_win = _find_chrome_win()

        if edge:
            print(f"\nFound Microsoft Edge: {edge}")
            choice = input("Use Edge for automatic extraction? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                tmp = Path(tempfile.gettempdir()) / "anycubic_edge_debug"
                token = _extract_via_browser(edge, tmp, "msedge.exe")

        if not token and chrome_win:
            print(f"\nFound Chrome: {chrome_win}")
            choice = input("Try reading from existing Chrome profile? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                chrome_db = _chrome_leveldb_win()
                print("  Close Chrome first for best results.")
                input("  Press Enter when Chrome is closed... ")
                token = _extract_from_live_chrome(chrome_db)
                if not token:
                    print("  Not found in Chrome profile — try launching with temp profile.")
                    choice2 = input("  Launch Chrome for manual login? [Y/n]: ").strip().lower()
                    if choice2 in ("", "y", "yes"):
                        tmp = Path(tempfile.gettempdir()) / "anycubic_chrome_debug"
                        token = _extract_via_browser(chrome_win, tmp, "chrome.exe")

    elif IS_MAC:
        chrome_mac = _find_chrome_mac()

        if chrome_mac:
            print(f"\nFound Google Chrome: {chrome_mac}")
            choice = input("Try reading from existing Chrome profile? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                chrome_db = _chrome_leveldb_mac()
                print("  Close Chrome first for best results.")
                input("  Press Enter when Chrome is closed... ")
                token = _extract_from_live_chrome(chrome_db)
                if not token:
                    print("  Not found in Chrome profile — try launching with temp profile.")
                    choice2 = input("  Launch Chrome for manual login? [Y/n]: ").strip().lower()
                    if choice2 in ("", "y", "yes"):
                        tmp = Path(tempfile.gettempdir()) / "anycubic_chrome_debug"
                        token = _extract_via_browser(chrome_mac, tmp, "Google Chrome")
        else:
            print("\nGoogle Chrome not found.")

    if not token:
        print("\nAutomatic extraction unavailable — using manual entry.")
        token = _extract_manual()

    if not token:
        print("\nNo token entered. Aborting.")
        sys.exit(1)

    cfg.save_token(token)
    preview = token[:40] + "..."
    print(f"\nToken saved: {preview}")
    print(f"Config file: {cfg.CONFIG_FILE}")
    print("\nYou can now run the uploader!")


if __name__ == "__main__":
    main()
