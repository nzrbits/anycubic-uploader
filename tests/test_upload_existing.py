import config
import upload_existing
import uploader


def test_exits_without_token(capsys):
    assert upload_existing.main() == 1
    assert "No token" in capsys.readouterr().out


def test_bulk_uses_shared_state_and_retries_failed_files(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.pm4u").write_bytes(b"1")
    (tmp_path / "b.PM4U").write_bytes(b"2")
    (tmp_path / "c.stl").write_bytes(b"3")
    config.save({"token": "mock", "watch_folders": [str(tmp_path)]})
    monkeypatch.setattr(uploader, "wait_until_stable", lambda path, cancel=None: True)
    seen = []

    def attempt(path, token):
        seen.append(path.name)
        return path.name != "a.pm4u"

    monkeypatch.setattr(uploader, "upload", attempt)
    assert upload_existing.main() == 1
    assert seen == ["a.pm4u", "b.PM4U"]
    seen.clear()
    assert upload_existing.main() == 1
    assert seen == ["a.pm4u"]
    assert "1 skipped" in capsys.readouterr().out


def test_bulk_defers_unstable_files(tmp_path, monkeypatch):
    (tmp_path / "a.pm4u").write_bytes(b"1")
    config.save({"token": "mock", "watch_folders": [str(tmp_path)]})
    monkeypatch.setattr(uploader, "wait_until_stable", lambda path, cancel=None: False)
    monkeypatch.setattr(
        uploader,
        "upload",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not upload")),
    )
    assert upload_existing.main() == 1
