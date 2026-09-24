from __future__ import annotations

import sys

import pytest

import setup_token

JWT = "eyJhbGciOiJIUzI1NiJ9." + "a" * 60 + "." + "b" * 40
OTHER = "eyJ" + "z" * 100


def test_token_found_next_to_xx_token_key(tmp_path):
    (tmp_path / "000003.log").write_bytes(
        b"\x00junk" + OTHER.encode() + b"\x00_https://cloud-universe.anycubic.com\x00XX-Token\x01" + JWT.encode() + b"\x00"
    )
    assert setup_token._find_token_in_leveldb(tmp_path) == JWT


def test_falls_back_to_first_jwt_in_anycubic_file(tmp_path):
    (tmp_path / "000005.ldb").write_bytes(b"anycubic\x00" + JWT.encode())
    assert setup_token._find_token_in_leveldb(tmp_path) == JWT


def test_ignores_files_without_anycubic_marker(tmp_path):
    (tmp_path / "000001.log").write_bytes(b"other-site\x00" + JWT.encode())
    assert setup_token._find_token_in_leveldb(tmp_path) is None


def test_ignores_non_leveldb_files(tmp_path):
    (tmp_path / "LOCK").write_bytes(b"XX-Token\x00" + JWT.encode())
    (tmp_path / "MANIFEST-000001").write_bytes(b"XX-Token\x00" + JWT.encode())
    assert setup_token._find_token_in_leveldb(tmp_path) is None


def test_live_chrome_missing_profile_returns_none(tmp_path):
    assert setup_token._extract_from_live_chrome(tmp_path / "nope") is None


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS path layout")
def test_chrome_leveldb_path_on_macos():
    p = setup_token._chrome_leveldb_mac()
    assert p.parts[-6:] == ("Application Support", "Google", "Chrome",
                            "Default", "Local Storage", "leveldb")


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS path layout")
def test_find_chrome_mac_matches_filesystem():
    from pathlib import Path
    found = setup_token._find_chrome_mac()
    if found is None:
        assert not Path("/Applications/Google Chrome.app").exists()
    else:
        assert Path(found).is_file()
