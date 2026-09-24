"""
Anycubic Token Extraktor
Oeffnet Edge in einem temporaeren Profil, wartet auf Login, liest XX-Token aus.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
TEMP_PROFILE = Path(os.environ["TEMP"]) / "anycubic_edge_debug"
LS_LEVELDB = TEMP_PROFILE / "Default" / "Local Storage" / "leveldb"


def find_edge():
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    # EdgeCore (non-standard install)
    for base in [
        Path(r"C:\Program Files (x86)\Microsoft\EdgeCore"),
        Path(r"C:\Program Files\Microsoft\EdgeCore"),
    ]:
        if base.exists():
            hits = sorted(base.glob("*/msedge.exe"), reverse=True)
            if hits:
                return str(hits[0])
    # Last resort
    try:
        out = subprocess.check_output(["where.exe", "msedge.exe"], text=True).strip()
        if out:
            return out.splitlines()[0]
    except Exception:
        pass
    raise FileNotFoundError("Microsoft Edge nicht gefunden.")


def find_token_in_leveldb(folder: Path):
    # LevelDB stores localStorage entries; look for XX-Token followed by a JWT
    broad = re.compile(rb"([ey][A-Za-z0-9\-_.]{80,})")
    candidates = []
    for f in sorted(folder.iterdir()):
        if f.suffix not in (".log", ".ldb"):
            continue
        try:
            data = f.read_bytes()
        except OSError:
            continue

        if b"XX-Token" not in data and b"anycubic" not in data:
            continue

        # Look for XX-Token key then nearby JWT
        idx = data.find(b"XX-Token")
        if idx >= 0:
            window = data[idx: idx + 512]
            m = broad.search(window)
            if m:
                return m.group(1).decode("ascii")

        # Broad fallback
        for m in broad.finditer(data):
            candidates.append(m.group(1).decode("ascii"))

    return candidates[0] if candidates else None


def main():
    print("=" * 55)
    print("  Anycubic Cloud - Token Extraktor")
    print("=" * 55)

    edge = find_edge()
    print(f"\nGefunden: {edge}")

    # Kill any leftover Edge that might block the profile
    subprocess.run(
        ["taskkill", "/F", "/IM", "msedge.exe"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    print("\nStarte Edge mit temporaerem Profil...")
    proc = subprocess.Popen([
        edge,
        f"--user-data-dir={TEMP_PROFILE}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://cloud-universe.anycubic.com/file",
    ])

    print("\n>>> Bitte in Edge einloggen.")
    print(">>> Danach hier Enter druecken. <<<")
    input()

    print("\nSchliesse Edge und lese Token...")
    proc.terminate()
    time.sleep(2)
    subprocess.run(
        ["taskkill", "/F", "/IM", "msedge.exe"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    if not LS_LEVELDB.exists():
        print(f"Fehler: localStorage-Ordner nicht gefunden: {LS_LEVELDB}")
        sys.exit(1)

    token = find_token_in_leveldb(LS_LEVELDB)

    if not token:
        print("\nToken nicht gefunden. Bitte stell sicher, dass du vollstaendig eingeloggt warst.")
        sys.exit(1)

    CONFIG_FILE.write_text(json.dumps({"token": token}, indent=2), encoding="utf-8")
    preview = token[:40] + "..."
    print(f"\nToken gespeichert: {preview}")
    print(f"Datei: {CONFIG_FILE}")
    print("\nDu kannst jetzt start.ps1 ausfuehren!")


if __name__ == "__main__":
    main()
