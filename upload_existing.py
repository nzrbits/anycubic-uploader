"""
Upload all existing .pm4u files from all configured watch folders.
Run this once after setup_token.py if you have files that were sliced before
the uploader was installed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config as cfg
from uploader import upload, load_token, WATCH_EXTENSIONS


def main():
    token = load_token()
    if not token:
        print("No token found. Run setup_token.py first.")
        sys.exit(1)

    folders = cfg.get_watch_folders()
    exts    = cfg.get_watch_extensions()

    files = sorted(
        f
        for folder in folders if folder.exists()
        for ext in exts
        for f in folder.glob(f"*{ext}")
    )

    if not files:
        print(f"No {'/'.join(exts)} files found in:")
        for folder in folders:
            print(f"  {folder}")
        sys.exit(0)

    print(f"Found {len(files)} file(s):\n")
    for f in files:
        size_mb = f.stat().st_size / 1_048_576
        print(f"  {f.name} ({size_mb:.1f} MB)")

    print()
    ok = fail = 0
    for f in files:
        try:
            if upload(f, token):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"ERROR: {f.name}: {e}")
            fail += 1

    print(f"\nDone: {ok} succeeded, {fail} failed.")


if __name__ == "__main__":
    main()
