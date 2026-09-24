"""
Anycubic Cloud Auto-Uploader
Watches the Downloads folder for new .pm4u files and uploads them automatically.

Upload flow (reverse-engineered from anycubic-cloud-api library):
  1. POST /v2/cloud_storage/lockStorageSpace  -> get preSignUrl + lock_id
  2. PUT  preSignUrl (AWS S3)                  -> upload file bytes
  3. POST /v2/profile/newUploadFile            -> claim upload, get cloud_file_id
  4. POST /v2/cloud_storage/unlockStorageSpace -> finalise
"""

import hashlib
import json
import logging
import sys
import time
import uuid
from pathlib import Path

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Settings ────────────────────────────────────────────────────────────────
WATCH_FOLDER    = Path.home() / "Downloads"
WATCH_EXTENSIONS = {".pm4u"}
API_BASE         = "https://cloud-universe.anycubic.com/p/p/workbench/api"
CONFIG_FILE      = Path(__file__).parent / "config.json"
FILE_STABLE_WAIT   = 3
FILE_STABLE_CHECKS = 5

# Anycubic API signing constants
_AID = "f9b3528877c94d5c9c5af32245db46ef"
_SEC = "0cf75926606049a3937f56b0373b99fb"
_VER = "1.0.0"
# ─────────────────────────────────────────────────────────────────────────────

_log_file = Path(__file__).parent / "watcher.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
        *([] if sys.stdout is None else [logging.StreamHandler(
            open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)
        )]),
    ],
)
log = logging.getLogger(__name__)


def load_token() -> str:
    if not CONFIG_FILE.exists():
        return ""
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig")).get("token", "")


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


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def wait_until_stable(path: Path) -> bool:
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


def upload(path: Path, token: str) -> bool:
    size_mb = path.stat().st_size / 1_048_576

    # Step 1 – lock storage space, get presigned AWS URL
    log.info(f"[1/4] Reserviere Cloud-Speicher fuer {path.name} ({size_mb:.1f} MB)...")
    lock_resp = _api_post(token, "/v2/cloud_storage/lockStorageSpace", {
        "size":         path.stat().st_size,
        "name":         path.name,
        "is_temp_file": 0,
    })
    lock_data = lock_resp.get("data")
    if not lock_data or "preSignUrl" not in lock_data:
        log.error(f"lockStorageSpace fehlgeschlagen: code={lock_resp.get('code')} data={lock_data}")
        return False
    lock_id    = lock_data["id"]
    presign_url = lock_data["preSignUrl"]

    # Step 2 – upload file bytes to S3
    log.info(f"[2/4] Lade hoch nach S3...")
    with open(path, "rb") as f:
        put = requests.put(presign_url, data=f, timeout=600)
    if put.status_code != 200:
        log.error(f"S3-Upload fehlgeschlagen: HTTP {put.status_code}")
        _api_post(token, "/v2/cloud_storage/unlockStorageSpace", {
            "id": lock_id, "is_delete_cos": 1
        })
        return False

    # Step 3 – claim upload → get cloud file ID
    log.info(f"[3/4] Registriere Datei in der Cloud...")
    claim_resp = _api_post(token, "/v2/profile/newUploadFile", {
        "user_lock_space_id": lock_id,
    })
    if not claim_resp.get("data") or "id" not in claim_resp.get("data", {}):
        log.error(f"claim fehlgeschlagen: code={claim_resp.get('code')} msg={claim_resp.get('msg')}")
        _api_post(token, "/v2/cloud_storage/unlockStorageSpace", {
            "id": lock_id, "is_delete_cos": 1
        })
        return False

    # Step 4 – unlock storage space to finalise
    log.info(f"[4/4] Abschliessen...")
    _api_post(token, "/v2/cloud_storage/unlockStorageSpace", {
        "id": lock_id, "is_delete_cos": 0
    })

    log.info(f"Erfolgreich hochgeladen: {path.name}")
    return True


class PrintFileHandler(FileSystemEventHandler):
    def __init__(self, token: str):
        self.token = token

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in WATCH_EXTENSIONS:
            return
        log.info(f"Neue Datei erkannt: {path.name}")
        if not wait_until_stable(path):
            log.warning(f"Datei nicht vollstaendig geschrieben: {path.name}")
            return
        try:
            upload(path, self.token)
        except Exception as e:
            log.error(f"Fehler bei {path.name}: {e}")


STATE_FILE = Path(__file__).parent / "last_upload.json"


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


def catch_up(token: str) -> None:
    last_ts = load_last_upload_time()
    missed = sorted(
        (f for ext in WATCH_EXTENSIONS
         for f in WATCH_FOLDER.glob(f"*{ext}")
         if f.stat().st_mtime > last_ts),
        key=lambda f: f.stat().st_mtime,
    )
    if not missed:
        return
    log.info(f"Nachholen: {len(missed)} verpasste Datei(en)...")
    for f in missed:
        try:
            upload_and_track(f, token)
        except Exception as e:
            log.error(f"Fehler bei {f.name}: {e}")


def main():
    token = load_token()
    if not token:
        print("Kein Token. Bitte start.ps1 ausfuehren.")
        sys.exit(1)

    log.info(f"Beobachte: {WATCH_FOLDER}")
    log.info(f"Dateitypen: {', '.join(WATCH_EXTENSIONS)}")

    # Upload any files that appeared since the last run
    catch_up(token)

    log.info("Warte auf neue Dateien... (Strg+C zum Beenden)")

    class TrackingHandler(PrintFileHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix.lower() not in WATCH_EXTENSIONS:
                return
            log.info(f"Neue Datei erkannt: {path.name}")
            if not wait_until_stable(path):
                log.warning(f"Datei nicht vollstaendig geschrieben: {path.name}")
                return
            try:
                upload_and_track(path, self.token)
            except Exception as e:
                log.error(f"Fehler bei {path.name}: {e}")

    handler = TrackingHandler(token=token)
    observer = Observer()
    observer.schedule(handler, str(WATCH_FOLDER), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
