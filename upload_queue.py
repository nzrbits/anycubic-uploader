"""One upload path for filesystem events, startup scans and the bulk command."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from enum import Enum
from pathlib import Path

import config
import uploader
from upload_state import FileVersion, UploadLedger

logger = logging.getLogger(__name__)


class Result(Enum):
    UPLOADED = "uploaded"
    FAILED = "failed"
    DEFERRED = "deferred"
    SKIPPED = "skipped"


def discover_files() -> list[Path]:
    extensions = config.get_watch_extensions()
    found: set[Path] = set()
    for folder in config.get_watch_folders():
        try:
            found.update(
                p.resolve()
                for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in extensions
            )
        except OSError:
            uploader.log.warning("Cannot scan %s", folder, exc_info=True)
    return sorted(found)


class UploadQueue:
    def __init__(
        self,
        on_result: Callable[[Path, Result], None],
        on_start: Callable[[Path], None] = lambda path: None,
        ledger: UploadLedger | None = None,
    ):
        self._on_result = on_result
        self._on_start = on_start
        self._ledger = ledger if ledger is not None else UploadLedger()
        self._queue: queue.Queue[Path] = queue.Queue(maxsize=128)
        self._pending: set[Path] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._worker = threading.Thread(
            target=self._run, name="upload-worker", daemon=True
        )
        self._worker.start()

    def submit(self, path: Path, block: bool = False) -> bool:
        path = config.normalize_folder(path)
        if path.suffix.lower() not in config.get_watch_extensions():
            return False
        try:
            if self._ledger.completed(FileVersion.read(path)):
                return False
        except OSError:
            return False
        while True:
            with self._lock:
                if self._stop.is_set() or path in self._pending:
                    return False
                try:
                    self._queue.put_nowait(path)
                except queue.Full:
                    if not block:
                        return False
                else:
                    self._pending.add(path)
                    return True
            if self._stop.wait(0.05):
                return False

    def scan(self) -> None:
        for path in discover_files():
            self.submit(path)

    def wait(self) -> None:
        self._queue.join()

    def stop(self) -> None:
        with self._lock:
            self._stop.set()
        self._worker.join()

    def _process(self, path: Path) -> Result:
        try:
            version = FileVersion.read(path)
        except OSError:
            return Result.DEFERRED
        if self._ledger.completed(version):
            return Result.SKIPPED
        if not uploader.wait_until_stable(path, self._stop):
            return Result.DEFERRED
        version = FileVersion.read(path)
        token = config.load_token()
        if not token:
            return Result.FAILED
        if not self._ledger.claim(version):
            return Result.SKIPPED
        success = False
        try:
            with self._ledger.heartbeat(version):
                self._on_start(path)
                success = uploader.upload(path, token)
                if success and FileVersion.read(path) != version:
                    success = False
            return Result.UPLOADED if success else Result.FAILED
        finally:
            self._ledger.finish(version, success)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                path = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                try:
                    result = self._process(path)
                except Exception:
                    logger.exception("Could not process %s", path)
                    result = Result.FAILED
                self._on_result(path, result)
            except Exception:
                logger.exception("Could not report upload result for %s", path)
            finally:
                with self._lock:
                    self._pending.discard(path)
                self._queue.task_done()
        while True:
            try:
                path = self._queue.get_nowait()
            except queue.Empty:
                break
            with self._lock:
                self._pending.discard(path)
            self._queue.task_done()
