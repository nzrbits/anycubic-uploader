import os

from upload_state import FileVersion, UploadLedger


def test_file_version_uses_absolute_canonical_path(tmp_path, monkeypatch):
    path = tmp_path / "part.pm4u"
    path.write_bytes(b"model")
    monkeypatch.chdir(tmp_path)
    version = FileVersion.read(path.relative_to(tmp_path))
    assert version.path == os.path.normcase(str(path))
    assert version.size == 5
    assert version.mtime_ns == path.stat().st_mtime_ns


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
