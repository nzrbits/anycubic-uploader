from unittest.mock import Mock

import config
import setup_token
import tray_app


def test_prompt_saves_token_without_printing_it(monkeypatch, capsys):
    root = Mock()
    monkeypatch.setattr(setup_token.tk, "Tk", lambda: root)
    monkeypatch.setattr(setup_token.mb, "showinfo", Mock())
    monkeypatch.setattr(
        setup_token.sd, "askstring", lambda *a, **kw: "  secret-token  "
    )
    assert setup_token.prompt_token()
    assert config.load_token() == "secret-token"
    assert "secret-token" not in capsys.readouterr().out
    root.destroy.assert_called_once()


def test_cancel_keeps_existing_token(monkeypatch):
    config.save_token("original")
    root = Mock()
    monkeypatch.setattr(setup_token.tk, "Tk", lambda: root)
    monkeypatch.setattr(setup_token.mb, "showinfo", Mock())
    monkeypatch.setattr(setup_token.sd, "askstring", lambda *a, **kw: None)
    assert not setup_token.prompt_token()
    assert config.load_token() == "original"
    root.destroy.assert_called_once()


def test_packaged_entry_offers_setup_without_token(monkeypatch):
    prompt = Mock(return_value=True)
    monkeypatch.setattr(tray_app, "prompt_token", prompt)
    assert tray_app.ensure_token()
    prompt.assert_called_once()


def test_existing_token_skips_setup(monkeypatch):
    config.save_token("existing")
    prompt = Mock()
    monkeypatch.setattr(tray_app, "prompt_token", prompt)
    assert tray_app.ensure_token()
    prompt.assert_not_called()


def test_corrupt_config_is_reported_and_preserved(monkeypatch):
    config.CONFIG_FILE.write_text("broken", encoding="utf-8")
    root = Mock()
    error = Mock()
    prompt = Mock()
    monkeypatch.setattr(tray_app.tk, "Tk", lambda: root)
    monkeypatch.setattr(tray_app.mb, "showerror", error)
    monkeypatch.setattr(tray_app, "prompt_token", prompt)
    assert not tray_app.ensure_token()
    error.assert_called_once()
    prompt.assert_not_called()
    assert config.CONFIG_FILE.read_text() == "broken"
