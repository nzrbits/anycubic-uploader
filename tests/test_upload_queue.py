import os
import threading
from unittest.mock import Mock

import pytest

import config
import uploader
from upload_queue import Result, UploadQueue, discover_files
from upload_state import FileVersion, UploadLedger


@pytest.fixture
def ready_files(tmp_path, monkeypatch):
    config.save({"token": "mock", "watch_folders": [str(tmp_path)]})
    monkeypatch.setattr(uploader, "wait_until_stable", lambda path, cancel=None: True)
    return tmp_path


def test_older_failed_file_survives_newer_success(ready_files, monkeypatch):
    a, b = ready_files / "a.pm4u", ready_files / "b.pm4u"
    for path, timestamp in [(a, 1000), (b, 2000)]:
        path.write_bytes(b"x")
        os.utime(path, (timestamp, timestamp))
    attempts = []
    monkeypatch.setattr(
        uploader, "upload", lambda path, token: attempts.append(path.name) or path == b
    )
    first = UploadQueue(lambda *args: None)
    try:
        first.scan()
        first.wait()
    finally:
        first.stop()
    assert attempts == ["a.pm4u", "b.pm4u"]
    attempts.clear()
    second = UploadQueue(lambda *args: None)
    try:
        second.scan()
        second.wait()
    finally:
        second.stop()
    assert attempts == ["a.pm4u"]


def test_duplicates_and_concurrent_process_claims_upload_once(ready_files, monkeypatch):
    path = ready_files / "part.pm4u"
    path.write_bytes(b"x")
    entered, release = threading.Event(), threading.Event()
    attempts = []

    def upload(path, token):
        attempts.append(path)
        entered.set()
        assert release.wait(5)
        return True

    monkeypatch.setattr(uploader, "upload", upload)
    one, two = UploadQueue(lambda *args: None), UploadQueue(lambda *args: None)
    try:
        assert one.submit(path)
        assert entered.wait(5)
        assert not one.submit(path)
        assert two.submit(path)
        two.wait()
        assert attempts == [path]
        release.set()
        one.wait()
        assert not two.submit(path)
    finally:
        release.set()
        one.stop()
        two.stop()


def test_changed_version_is_uploaded_again(ready_files, monkeypatch):
    path = ready_files / "part.pm4u"
    path.write_bytes(b"x")
    attempts = []
    monkeypatch.setattr(
        uploader, "upload", lambda path, token: attempts.append(path.name) or True
    )
    worker = UploadQueue(lambda *args: None)
    try:
        assert worker.submit(path)
        worker.wait()
        path.write_bytes(b"changed")
        assert worker.submit(path)
        worker.wait()
    finally:
        worker.stop()
    assert attempts == ["part.pm4u", "part.pm4u"]


def test_queue_reads_renewed_token(ready_files, monkeypatch):
    path = ready_files / "part.pm4u"
    path.write_bytes(b"x")
    tokens = []
    monkeypatch.setattr(
        uploader, "upload", lambda path, token: tokens.append(token) or False
    )
    worker = UploadQueue(lambda *args: None)
    try:
        worker.submit(path)
        worker.wait()
        config.save_token("renewed")
        worker.submit(path)
        worker.wait()
    finally:
        worker.stop()
    assert tokens == ["mock", "renewed"]


def test_queue_defers_growing_file(ready_files, monkeypatch):
    path = ready_files / "part.pm4u"
    path.write_bytes(b"x")
    attempt = Mock()
    results = []
    monkeypatch.setattr(uploader, "wait_until_stable", lambda path, cancel=None: False)
    monkeypatch.setattr(uploader, "upload", attempt)
    worker = UploadQueue(lambda path, result: results.append(result))
    try:
        worker.submit(path)
        worker.wait()
    finally:
        worker.stop()
    assert results == [Result.DEFERRED]
    attempt.assert_not_called()


def test_missing_token_defers_silently_and_saved_token_resumes(
    ready_files, monkeypatch
):
    path = ready_files / "part.pm4u"
    path.write_bytes(b"x")
    config.save_token("")
    stable = Mock(return_value=True)
    upload = Mock(return_value=True)
    started = Mock()
    results = []
    monkeypatch.setattr(uploader, "wait_until_stable", stable)
    monkeypatch.setattr(uploader, "upload", upload)
    worker = UploadQueue(lambda path, result: results.append(result), started)
    try:
        for _ in range(2):
            assert worker.submit(path)
            worker.wait()
        stable.assert_not_called()
        upload.assert_not_called()
        started.assert_not_called()
        config.save_token("saved")
        assert worker.submit(path)
        worker.wait()
        upload.assert_called_once_with(path, "saved")
        started.assert_called_once_with(path)
        assert results == [Result.DEFERRED, Result.DEFERRED, Result.UPLOADED]
    finally:
        worker.stop()


def test_token_removed_during_file_check_defers_without_upload(
    ready_files, monkeypatch
):
    path = ready_files / "part.pm4u"
    path.write_bytes(b"x")

    def stable(path, cancel=None):
        config.save_token("")
        return True

    upload = Mock()
    results = []
    monkeypatch.setattr(uploader, "wait_until_stable", stable)
    monkeypatch.setattr(uploader, "upload", upload)
    worker = UploadQueue(lambda path, result: results.append(result))
    try:
        worker.submit(path)
        worker.wait()
        upload.assert_not_called()
        assert results == [Result.DEFERRED]
    finally:
        worker.stop()


def test_discovery_deduplicates_and_matches_case_insensitively(tmp_path):
    a = tmp_path / "part.PM4U"
    a.write_bytes(b"x")
    (tmp_path / "folder.pm4u").mkdir()
    config.save(
        {
            "watch_folders": [str(tmp_path), str(tmp_path / ".")],
            "watch_extensions": [".PM4U"],
        }
    )
    assert discover_files() == [a]


def test_stale_lease_can_be_reclaimed(tmp_path, monkeypatch):
    path = tmp_path / "part.pm4u"
    path.write_bytes(b"x")
    version = FileVersion.read(path)
    one, two = UploadLedger(), UploadLedger()
    monkeypatch.setattr("upload_state.time.time", lambda: 1000)
    assert one.claim(version)
    assert not two.claim(version)
    monkeypatch.setattr("upload_state.time.time", lambda: 2300)
    assert two.claim(version)
    one.finish(version, True)
    assert not two.completed(version)
    two.finish(version, True)
    assert one.completed(version)
