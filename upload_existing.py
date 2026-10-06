"""Upload pending files from the configured folders."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import config
from storage import configure_logging
from upload_queue import Result, UploadQueue, discover_files


def main() -> int:
    try:
        if not config.load_token():
            print("No token found. Run setup_token.py first.")
            return 1
        files = discover_files()
    except (config.ConfigError, OSError) as error:
        print(f"Cannot load settings: {error}")
        return 1
    if not files:
        print("No matching files found in the configured folders.")
        return 0
    counts: Counter[Result] = Counter()

    def finished(path: Path, result: Result) -> None:
        counts[result] += 1
        print(f"{path.name}: {result.value}")

    worker = UploadQueue(finished)
    try:
        for path in files:
            if not worker.submit(path, block=True):
                counts[Result.SKIPPED] += 1
        worker.wait()
    finally:
        worker.stop()
    print(
        f"Done: {counts[Result.UPLOADED]} succeeded, {counts[Result.FAILED]} failed, "
        f"{counts[Result.DEFERRED]} deferred, {counts[Result.SKIPPED]} skipped."
    )
    return 1 if counts[Result.FAILED] or counts[Result.DEFERRED] else 0


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(main())
