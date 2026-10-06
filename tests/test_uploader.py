from __future__ import annotations

import hashlib

import pytest

import uploader


def test_headers_carry_token_and_valid_signature():
    h = uploader._make_headers("tok123")
    assert h["XX-Token"] == "tok123"
    raw = f"{uploader._AID}{h['XX-Timestamp']}{uploader._VER}{uploader._SEC}{h['XX-Nonce']}{uploader._AID}"
    assert h["XX-Signature"] == hashlib.md5(raw.encode()).hexdigest()
    assert h["XX-Timestamp"].isdigit() and len(h["XX-Timestamp"]) == 13


def test_headers_use_fresh_nonce():
    assert (
        uploader._make_headers("t")["XX-Nonce"]
        != uploader._make_headers("t")["XX-Nonce"]
    )


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
    fake_api.replies["/v2/profile/newUploadFile"] = {
        "code": 0,
        "msg": "nope",
        "data": None,
    }

    assert uploader.upload(f, "tok") is False
    assert fake_api.calls[-1][2] == {"id": 42, "is_delete_cos": 1}


def test_api_post_raises_on_http_error(monkeypatch):
    from conftest import FakeResponse

    monkeypatch.setattr(
        uploader.requests, "post", lambda *a, **k: FakeResponse(status_code=401)
    )
    with pytest.raises(uploader.requests.HTTPError):
        uploader._api_post("tok", "/x", {})


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
        if chunk is not None and f.read_bytes() != chunk:
            f.write_bytes(chunk)

    monkeypatch.setattr(uploader.time, "sleep", sleep)
    assert uploader.wait_until_stable(f) is True
    assert f.stat().st_size == 3


def test_continuously_growing_file_is_not_stable(tmp_path, monkeypatch):
    path = tmp_path / "growing.pm4u"
    path.write_bytes(b"x")

    def grow(_):
        with path.open("ab") as stream:
            stream.write(b"x")

    monkeypatch.setattr(uploader.time, "sleep", grow)
    assert not uploader.wait_until_stable(path)


@pytest.mark.parametrize("stage", ["put", "claim", "finalize"])
def test_network_errors_release_reservation(tmp_path, fake_api, monkeypatch, stage):
    path = tmp_path / "part.pm4u"
    path.write_bytes(b"x")
    if stage == "put":
        monkeypatch.setattr(
            uploader.requests,
            "put",
            lambda *a, **kw: (_ for _ in ()).throw(uploader.requests.Timeout()),
        )
    else:
        original = uploader._api_post

        def fail(token, endpoint, payload):
            if (stage == "claim" and endpoint.endswith("newUploadFile")) or (
                stage == "finalize"
                and endpoint.endswith("unlockStorageSpace")
                and payload["is_delete_cos"] == 0
            ):
                raise uploader.requests.ConnectionError("offline")
            return original(token, endpoint, payload)

        monkeypatch.setattr(uploader, "_api_post", fail)
    assert not uploader.upload(path, "mock")
    assert fake_api.calls[-1][2] == {"id": 42, "is_delete_cos": 1}


def test_finalization_rejection_is_failure(tmp_path, fake_api):
    path = tmp_path / "part.pm4u"
    path.write_bytes(b"x")
    fake_api.replies["/v2/cloud_storage/unlockStorageSpace"] = {"code": 0}
    assert not uploader.upload(path, "mock")
    assert fake_api.calls[-1][2] == {"id": 42, "is_delete_cos": 1}


def test_missing_upload_url_releases_known_reservation(tmp_path, fake_api):
    path = tmp_path / "part.pm4u"
    path.write_bytes(b"x")
    fake_api.replies["/v2/cloud_storage/lockStorageSpace"] = {
        "code": 1,
        "data": {"id": 42},
    }
    assert not uploader.upload(path, "mock")
    assert fake_api.calls[-1][2] == {"id": 42, "is_delete_cos": 1}


def test_changed_file_is_not_registered(tmp_path, fake_api, monkeypatch):
    from conftest import FakeResponse

    path = tmp_path / "part.pm4u"
    path.write_bytes(b"x")

    def put(*args, **kwargs):
        path.write_bytes(b"different")
        return FakeResponse()

    monkeypatch.setattr(uploader.requests, "put", put)
    assert not uploader.upload(path, "mock")
    assert not any(
        endpoint.endswith("newUploadFile")
        for method, endpoint, payload in fake_api.calls
    )


@pytest.mark.parametrize("response", [{"code": 0}, [], {"data": {}}])
def test_api_rejects_invalid_response(monkeypatch, response):
    from conftest import FakeResponse

    monkeypatch.setattr(
        uploader.requests, "post", lambda *a, **kw: FakeResponse(response)
    )
    with pytest.raises(uploader.ApiError):
        uploader._api_post("mock", "/test", {})


def test_free_storage_formats_gb(fake_api):
    fake_api.replies["/v2/cloud_storage/storageInfo"] = {
        "code": 1,
        "data": {"total_size": 8 * 1_073_741_824, "used_size": 3 * 1_073_741_824},
    }
    assert uploader.free_storage("mock") == "5.0 GB free"
