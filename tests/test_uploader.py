from __future__ import annotations

import hashlib
import json

import pytest

import uploader


def test_headers_carry_token_and_valid_signature():
    h = uploader._make_headers("tok123")
    assert h["XX-Token"] == "tok123"
    raw = f"{uploader._AID}{h['XX-Timestamp']}{uploader._VER}{uploader._SEC}{h['XX-Nonce']}{uploader._AID}"
    assert h["XX-Signature"] == hashlib.md5(raw.encode()).hexdigest()
    assert h["XX-Timestamp"].isdigit() and len(h["XX-Timestamp"]) == 13


def test_headers_use_fresh_nonce():
    assert uploader._make_headers("t")["XX-Nonce"] != uploader._make_headers("t")["XX-Nonce"]


def test_upload_happy_path_runs_all_four_steps(tmp_path, fake_api):
    f = tmp_path / "part.pm4u"
    f.write_bytes(b"x" * 1234)

    assert uploader.upload(f, "tok") is True

    steps = [(m, p) for m, p, _ in fake_api.calls]
    assert steps == [
        ("POST", "/v2/cloud_storage/lockStorageSpace"),
        ("PUT", "https://s3.example/put"),
        ("POST", "/v2/profile/newUploadFile"),
        ("POST", "/v2/cloud_storage/unlockStorageSpace"),
    ]
    lock_body = fake_api.calls[0][2]
    assert lock_body == {"size": 1234, "name": "part.pm4u", "is_temp_file": 0}
    assert fake_api.calls[1][2] == {"bytes": 1234}
    assert fake_api.calls[2][2] == {"user_lock_space_id": 42}
    assert fake_api.calls[3][2] == {"id": 42, "is_delete_cos": 0}


def test_upload_stops_when_lock_fails(tmp_path, fake_api):
    f = tmp_path / "a.pm4u"
    f.write_bytes(b"x")
    fake_api.replies["/v2/cloud_storage/lockStorageSpace"] = {"code": 0, "data": None}

    assert uploader.upload(f, "tok") is False
    assert len(fake_api.calls) == 1


def test_upload_releases_lock_when_s3_fails(tmp_path, fake_api):
    f = tmp_path / "a.pm4u"
    f.write_bytes(b"x")
    fake_api.put_status["code"] = 403

    assert uploader.upload(f, "tok") is False
    last = fake_api.calls[-1]
    assert last[1] == "/v2/cloud_storage/unlockStorageSpace"
    assert last[2] == {"id": 42, "is_delete_cos": 1}


def test_upload_releases_lock_when_claim_fails(tmp_path, fake_api):
    f = tmp_path / "a.pm4u"
    f.write_bytes(b"x")
    fake_api.replies["/v2/profile/newUploadFile"] = {"code": 0, "msg": "nope", "data": None}

    assert uploader.upload(f, "tok") is False
    assert fake_api.calls[-1][2] == {"id": 42, "is_delete_cos": 1}


def test_api_post_raises_on_http_error(monkeypatch):
    from conftest import FakeResponse
    monkeypatch.setattr(uploader.requests, "post",
                        lambda *a, **k: FakeResponse(status_code=401))
    with pytest.raises(uploader.requests.HTTPError):
        uploader._api_post("tok", "/x", {})


def test_upload_and_track_saves_mtime_only_on_success(tmp_path, fake_api):
    f = tmp_path / "a.pm4u"
    f.write_bytes(b"x")

    fake_api.put_status["code"] = 500
    assert uploader.upload_and_track(f, "tok") is False
    assert uploader.load_last_upload_time() == 0.0

    fake_api.put_status["code"] = 200
    assert uploader.upload_and_track(f, "tok") is True
    assert uploader.load_last_upload_time() == f.stat().st_mtime


def test_last_upload_time_survives_broken_state_file():
    uploader.STATE_FILE.write_text("garbage", encoding="utf-8")
    assert uploader.load_last_upload_time() == 0.0


def test_last_upload_time_roundtrip():
    uploader.save_last_upload_time(1700000000.5)
    assert json.loads(uploader.STATE_FILE.read_text())["ts"] == 1700000000.5
    assert uploader.load_last_upload_time() == 1700000000.5


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(uploader.time, "sleep", lambda s: None)


def test_wait_until_stable_true_for_finished_file(tmp_path, no_sleep):
    f = tmp_path / "a.pm4u"
    f.write_bytes(b"done")
    assert uploader.wait_until_stable(f) is True


def test_wait_until_stable_false_for_missing_file(tmp_path, no_sleep):
    assert uploader.wait_until_stable(tmp_path / "gone.pm4u") is False


def test_wait_until_stable_false_for_empty_file(tmp_path, no_sleep):
    f = tmp_path / "a.pm4u"
    f.touch()
    assert uploader.wait_until_stable(f) is False


def test_wait_until_stable_waits_for_growth_to_stop(tmp_path, monkeypatch):
    f = tmp_path / "a.pm4u"
    f.write_bytes(b"1")
    grow = iter([b"12", b"123", b"123", b"123", b"123", b"123"])

    def sleep(_):
        chunk = next(grow, None)
        if chunk is not None:
            f.write_bytes(chunk)

    monkeypatch.setattr(uploader.time, "sleep", sleep)
    assert uploader.wait_until_stable(f) is True
    assert f.stat().st_size == 3
