"""
Anycubic Cloud upload logic and API helpers.

Upload flow (reverse-engineered from anycubic-cloud-api library):
  1. POST /v2/cloud_storage/lockStorageSpace  -> get preSignUrl + lock_id
  2. PUT  preSignUrl (AWS S3)                  -> upload file bytes
  3. POST /v2/profile/newUploadFile            -> claim upload, get cloud_file_id
  4. POST /v2/cloud_storage/unlockStorageSpace -> finalise
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
import uuid
from pathlib import Path

import requests

import config as cfg

# ── API constants ─────────────────────────────────────────────────────────────
API_BASE           = "https://cloud-universe.anycubic.com/p/p/workbench/api"
FILE_STABLE_WAIT   = 3
FILE_STABLE_CHECKS = 5
_AID = "f9b3528877c94d5c9c5af32245db46ef"
_SEC = "0cf75926606049a3937f56b0373b99fb"
_VER = "1.0.0"

# ── Logging ───────────────────────────────────────────────────────────────────
_log_file = Path(__file__).parent / "watcher.log"

_handlers: list[logging.Handler] = [logging.FileHandler(_log_file, encoding="utf-8")]
if sys.stdout is not None:
    try:
        _handlers.append(
            logging.StreamHandler(
                open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
            )
        )
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=_handlers,
)
log = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "last_upload.json"

# Re-export for backward compatibility with upload_existing.py
WATCH_EXTENSIONS = cfg.get_watch_extensions()


def load_token() -> str:
    return cfg.load_token()


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _make_headers(token: str) -> dict:
    ts    = str(int(time.time() * 1000))
    nonce = str(uuid.uuid1())
    sig   = hashlib.md5(f"{_AID}{ts}{_VER}{_SEC}{nonce}{_AID}".encode()).hexdigest()
    return {
        "XX-Token":       token,
        "XX-Device-Type": "web",
        "XX-IS-CN":       "2",
        "XX-Timestamp":   ts,
        "XX-Nonce":       nonce,
        "XX-Version":     _VER,
        "XX-Signature":   sig,
        "Content-Type":   "application/json",
        "User-Agent":     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer":        "https://cloud-universe.anycubic.com/file",
        "Origin":         "https://cloud-universe.anycubic.com",
    }


def _api_post(token: str, path: str, payload: dict, timeout: int = 30) -> dict:
    r = requests.post(
        f"{API_BASE}{path}",
        headers=_make_headers(token),
        data=json.dumps(payload),
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


# ── File helpers ──────────────────────────────────────────────────────────────

def wait_until_stable(path: Path) -> bool:
    """Poll until the file size stops changing, returns False if file vanishes."""
    time.sleep(FILE_STABLE_WAIT)
    prev = -1
    for _ in range(FILE_STABLE_CHECKS):
        try:
            sz = path.stat().st_size
        except OSError:
            return False
        if sz == prev and sz > 0:
            return True
        prev = sz
        time.sleep(1)
    return prev > 0


# ── Upload ────────────────────────────────────────────────────────────────────

def upload(path: Path, token: str) -> bool:
    size_mb = path.stat().st_size / 1_048_576
    log.info("[1/4] Reserving cloud storage for %s (%.1f MB)...", path.name, size_mb)

    lock_resp = _api_post(token, "/v2/cloud_storage/lockStorageSpace", {
        "size":         path.stat().st_size,
        "name":         path.name,
        "is_temp_file": 0,
    })
    lock_data = lock_resp.get("data")
    if not lock_data or "preSignUrl" not in lock_data:
        log.error("lockStorageSpace failed: code=%s data=%s", lock_resp.get("code"), lock_data)
        return False

    lock_id     = lock_data["id"]
    presign_url = lock_data["preSignUrl"]

    log.info("[2/4] S3-Upload...")
    with open(path, "rb") as f:
        put = requests.put(presign_url, data=f, timeout=600)
    if put.status_code != 200:
        log.error("S3-Upload failed: HTTP %s", put.status_code)
        _api_post(token, "/v2/cloud_storage/unlockStorageSpace", {"id": lock_id, "is_delete_cos": 1})
        return False

    log.info("[3/4] Registering file in cloud...")
    claim_resp = _api_post(token, "/v2/profile/newUploadFile", {"user_lock_space_id": lock_id})
    if not claim_resp.get("data") or "id" not in claim_resp.get("data", {}):
        log.error("claim failed: code=%s msg=%s", claim_resp.get("code"), claim_resp.get("msg"))
        _api_post(token, "/v2/cloud_storage/unlockStorageSpace", {"id": lock_id, "is_delete_cos": 1})
        return False

    log.info("[4/4] Finalizing...")
    _api_post(token, "/v2/cloud_storage/unlockStorageSpace", {"id": lock_id, "is_delete_cos": 0})
    log.info("Upload complete: %s", path.name)
    return True


# ── State tracking ────────────────────────────────────────────────────────────

def load_last_upload_time() -> float:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("ts", 0.0)
        except Exception:
            pass
    return 0.0


def save_last_upload_time(ts: float) -> None:
    STATE_FILE.write_text(json.dumps({"ts": ts}), encoding="utf-8")


def upload_and_track(path: Path, token: str) -> bool:
    ok = upload(path, token)
    if ok:
        save_last_upload_time(path.stat().st_mtime)
    return ok
