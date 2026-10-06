"""Completed file versions and leases shared by the tray app and bulk uploads."""

from __future__ import annotations

import os
import sqlite3
import threading
import time
import uuid
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from storage import DATA_DIR

STATE_FILE = DATA_DIR / "uploads.sqlite3"
LEASE_SECONDS = 1200


@dataclass(frozen=True)
class FileVersion:
    path: str
    size: int
    mtime_ns: int

    @classmethod
    def read(cls, path: Path) -> FileVersion:
        normalized = path.expanduser().resolve()
        stat = normalized.stat()
        return cls(os.path.normcase(str(normalized)), stat.st_size, stat.st_mtime_ns)


class UploadLedger:
    def __init__(self, path: Path | None = None):
        self.path = path if path is not None else STATE_FILE
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.owner = uuid.uuid4().hex
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS uploads (
                path TEXT PRIMARY KEY, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
                status TEXT NOT NULL, owner TEXT NOT NULL, updated REAL NOT NULL
            )""")

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            yield db

    def completed(self, version: FileVersion) -> bool:
        with self._connect() as db:
            return (
                db.execute(
                    "SELECT 1 FROM uploads WHERE path=? AND size=? AND mtime_ns=? AND status='done'",
                    (version.path, version.size, version.mtime_ns),
                ).fetchone()
                is not None
            )

    def claim(self, version: FileVersion) -> bool:
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT size,mtime_ns,status,updated FROM uploads WHERE path=?",
                (version.path,),
            ).fetchone()
            if row and (
                (row[:3] == (version.size, version.mtime_ns, "done"))
                or (row[2] == "running" and row[3] > now - LEASE_SECONDS)
            ):
                return False
            db.execute(
                "INSERT OR REPLACE INTO uploads VALUES (?,?,?,?,?,?)",
                (
                    version.path,
                    version.size,
                    version.mtime_ns,
                    "running",
                    self.owner,
                    now,
                ),
            )
            return True

    def finish(self, version: FileVersion, success: bool) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE uploads SET status=?,updated=? WHERE path=? AND owner=? AND size=? AND mtime_ns=?",
                (
                    "done" if success else "failed",
                    time.time(),
                    version.path,
                    self.owner,
                    version.size,
                    version.mtime_ns,
                ),
            )

    @contextmanager
    def heartbeat(self, version: FileVersion):
        stop = threading.Event()

        def refresh():
            while not stop.wait(30):
                with self._connect() as db:
                    db.execute(
                        "UPDATE uploads SET updated=? WHERE path=? AND owner=? AND status='running'",
                        (time.time(), version.path, self.owner),
                    )

        thread = threading.Thread(target=refresh, name="upload-lease", daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join()
