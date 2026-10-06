"""Anycubic API calls and the reserve, transfer, register, finalize transaction."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path

import requests

API_BASE = "https://cloud-universe.anycubic.com/p/p/workbench/api"
FILE_STABLE_WAIT = 3
FILE_STABLE_CHECKS = 5
_AID = "f9b3528877c94d5c9c5af32245db46ef"
_SEC = "0cf75926606049a3937f56b0373b99fb"
_VER = "1.0.0"
log = logging.getLogger(__name__)


class ApiError(RuntimeError):
    pass


def _make_headers(token: str) -> dict[str, str]:
    ts = str(int(time.time() * 1000))
    nonce = str(uuid.uuid1())
    sig = hashlib.md5(f"{_AID}{ts}{_VER}{_SEC}{nonce}{_AID}".encode()).hexdigest()
    return {
        "XX-Token": token,
        "XX-Device-Type": "web",
        "XX-IS-CN": "2",
        "XX-Timestamp": ts,
        "XX-Nonce": nonce,
        "XX-Version": _VER,
        "XX-Signature": sig,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://cloud-universe.anycubic.com/file",
        "Origin": "https://cloud-universe.anycubic.com",
    }


def _api_post(token: str, path: str, payload: dict, timeout: int = 30) -> dict:
    response = requests.post(
        f"{API_BASE}{path}",
        headers=_make_headers(token),
        data=json.dumps(payload),
        timeout=timeout,
    )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or result.get("code") != 1:
        raise ApiError(f"{path} rejected the request")
    return result


def _data(response: dict, *fields: str) -> dict:
    data = response.get("data")
    if not isinstance(data, dict) or any(data.get(field) is None for field in fields):
        raise ApiError("API response is missing required fields")
    return data


def _signature(stat: os.stat_result) -> tuple[int, int]:
    return stat.st_size, stat.st_mtime_ns


def wait_until_stable(path: Path, cancel: threading.Event | None = None) -> bool:
    def pause(seconds: float) -> bool:
        if cancel is not None:
            return cancel.wait(seconds)
        time.sleep(seconds)
        return False

    if pause(FILE_STABLE_WAIT):
        return False
    previous = None
    for _ in range(FILE_STABLE_CHECKS):
        try:
            current = _signature(path.stat())
        except OSError:
            return False
        if current == previous and current[0] > 0:
            return True
        previous = current
        if pause(1):
            return False
    return False


def upload(path: Path, token: str) -> bool:
    lock_id = None
    completed = False
    try:
        with path.open("rb") as stream:
            original = _signature(os.fstat(stream.fileno()))
            log.info(
                "Reserving storage for %s (%.1f MB)", path.name, original[0] / 1_048_576
            )
            reservation = _data(
                _api_post(
                    token,
                    "/v2/cloud_storage/lockStorageSpace",
                    {
                        "size": original[0],
                        "name": path.name,
                        "is_temp_file": 0,
                    },
                ),
                "id",
            )
            lock_id = reservation["id"]
            url = reservation.get("preSignUrl")
            if not isinstance(url, str) or not url.startswith("https://"):
                raise ApiError("API returned an invalid upload URL")
            log.info("Transferring %s", path.name)
            response = requests.put(url, data=stream, timeout=600)
            response.raise_for_status()
            if (
                _signature(os.fstat(stream.fileno())) != original
                or _signature(path.stat()) != original
            ):
                raise ApiError("File changed during upload")
        _data(
            _api_post(
                token, "/v2/profile/newUploadFile", {"user_lock_space_id": lock_id}
            ),
            "id",
        )
        _api_post(
            token,
            "/v2/cloud_storage/unlockStorageSpace",
            {"id": lock_id, "is_delete_cos": 0},
        )
        completed = True
        log.info("Uploaded %s", path.name)
        return True
    except (requests.RequestException, OSError, ValueError, ApiError):
        log.exception("Upload failed for %s", path.name)
        return False
    finally:
        if lock_id is not None and not completed:
            try:
                _api_post(
                    token,
                    "/v2/cloud_storage/unlockStorageSpace",
                    {"id": lock_id, "is_delete_cos": 1},
                )
            except (requests.RequestException, OSError, ValueError, ApiError):
                log.exception("Could not release cloud reservation for %s", path.name)


def free_storage(token: str) -> str | None:
    for endpoint in ("/v2/cloud_storage/storageInfo", "/v2/profile/storageInfo"):
        try:
            data = _data(_api_post(token, endpoint, {}))
            total = data.get("total_size", data.get("totalSize", 0))
            used = data.get("used_size", data.get("usedSize", 0))
            if (
                isinstance(total, (int, float))
                and isinstance(used, (int, float))
                and total > 0
            ):
                return f"{(total - used) / 1_073_741_824:.1f} GB free"
        except (requests.RequestException, ValueError, ApiError):
            log.debug("Storage information unavailable", exc_info=True)
    return None
