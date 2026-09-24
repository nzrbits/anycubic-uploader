"""Shared fixtures. Every test gets its own config.json and state file in tmp_path."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import logging  # noqa: E402

import config  # noqa: E402
import uploader  # noqa: E402

# uploader.py attaches a FileHandler to the real watcher.log at import time.
# Drop it so test runs never write fake uploads into the user's log.
for _h in list(logging.getLogger().handlers):
    if isinstance(_h, logging.FileHandler):
        logging.getLogger().removeHandler(_h)
        _h.close()


@pytest.fixture(autouse=True)
def isolated_files(tmp_path, monkeypatch):
    """Keep tests away from the real config.json and last_upload.json."""
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(uploader, "STATE_FILE", tmp_path / "last_upload.json")
    return tmp_path


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {}
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise uploader.requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture
def fake_api(monkeypatch):
    """Record API calls and answer them from a dict keyed by endpoint path."""
    calls: list[tuple[str, str, dict]] = []
    replies: dict[str, dict] = {
        "/v2/cloud_storage/lockStorageSpace": {
            "code": 1, "data": {"id": 42, "preSignUrl": "https://s3.example/put"},
        },
        "/v2/profile/newUploadFile": {"code": 1, "data": {"id": 7}},
        "/v2/cloud_storage/unlockStorageSpace": {"code": 1},
    }
    put_status = {"code": 200}

    def fake_post(url, headers, data, timeout):
        import json
        path = url.removeprefix(uploader.API_BASE)
        calls.append(("POST", path, json.loads(data)))
        return FakeResponse(replies.get(path, {}))

    def fake_put(url, data, timeout):
        body = data.read()
        calls.append(("PUT", url, {"bytes": len(body)}))
        return FakeResponse(status_code=put_status["code"])

    monkeypatch.setattr(uploader.requests, "post", fake_post)
    monkeypatch.setattr(uploader.requests, "put", fake_put)

    class Api:
        pass

    api = Api()
    api.calls = calls
    api.replies = replies
    api.put_status = put_status
    return api
