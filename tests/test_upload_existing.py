from __future__ import annotations

import pytest

import config
import upload_existing


def test_exits_without_token(capsys):
    with pytest.raises(SystemExit) as e:
        upload_existing.main()
    assert e.value.code == 1
    assert "No token" in capsys.readouterr().out


def test_uploads_only_matching_files(tmp_path, monkeypatch, capsys):
    watch = tmp_path / "watch"
    watch.mkdir()
    (watch / "a.pm4u").write_bytes(b"1")
    (watch / "b.pm4u").write_bytes(b"2")
    (watch / "c.stl").write_bytes(b"3")
    config.save({"token": "tok", "watch_folders": [str(watch), str(tmp_path / "missing")]})

    seen = []

    def fake_upload(path, token):
        seen.append((path.name, token))
        return path.name == "a.pm4u"

    monkeypatch.setattr(upload_existing, "upload", fake_upload)
    upload_existing.main()

    assert seen == [("a.pm4u", "tok"), ("b.pm4u", "tok")]
    assert "1 succeeded, 1 failed" in capsys.readouterr().out


def test_exception_counts_as_failure(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.pm4u").write_bytes(b"1")
    config.save({"token": "tok", "watch_folders": [str(tmp_path)]})

    def boom(path, token):
        raise RuntimeError("network down")

    monkeypatch.setattr(upload_existing, "upload", boom)
    upload_existing.main()
    out = capsys.readouterr().out
    assert "ERROR: a.pm4u: network down" in out
    assert "0 succeeded, 1 failed" in out
