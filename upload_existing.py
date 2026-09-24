"""
Lädt alle vorhandenen .pm4u Dateien aus dem Downloads-Ordner hoch.
Muss nach setup_token.py ausgeführt werden.
"""

import json
import sys
from pathlib import Path

# Shared logic aus uploader.py wiederverwenden
sys.path.insert(0, str(Path(__file__).parent))
from uploader import upload, load_token, WATCH_FOLDER, WATCH_EXTENSIONS


def main():
    token = load_token()
    if not token:
        print("Kein Token gefunden. Bitte zuerst start.ps1 ausführen.")
        sys.exit(1)

    files = sorted(
        f for ext in WATCH_EXTENSIONS
        for f in WATCH_FOLDER.glob(f"*{ext}")
    )

    if not files:
        print(f"Keine {'/'.join(WATCH_EXTENSIONS)} Dateien in {WATCH_FOLDER} gefunden.")
        sys.exit(0)

    print(f"{len(files)} Datei(en) gefunden:\n")
    for f in files:
        mb = f.stat().st_size / 1_048_576
        print(f"  {f.name} ({mb:.1f} MB)")

    print()
    ok = 0
    fail = 0
    for f in files:
        try:
            if upload(f, token):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"FEHLER bei {f.name}: {e}")
            fail += 1

    print(f"\nFertig: {ok} erfolgreich, {fail} fehlgeschlagen.")


if __name__ == "__main__":
    main()
