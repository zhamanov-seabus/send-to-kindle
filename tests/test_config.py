"""Tests for config resolution. No secrets, no network."""

from __future__ import annotations

import pytest

from kindlemcp import config
from kindlemcp.config import ConfigError


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure a clean slate for SMTP_URL / KINDLE_ADDR each test."""
    monkeypatch.delenv("SMTP_URL", raising=False)
    monkeypatch.delenv("KINDLE_ADDR", raising=False)


def test_env_var_wins_for_smtp(monkeypatch, tmp_path):
    # A ./.env exists but the env var should take precedence.
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("SMTP_URL=smtp://file:pw@host:587\n")
    monkeypatch.setenv("SMTP_URL", "smtp://env:pw@host:587")
    assert config.resolve_smtp_url() == "smtp://env:pw@host:587"


def test_smtp_falls_back_to_local_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "# comment\nSMTP_URL=smtp://you%40gmail.com:app_pw@smtp.gmail.com:587\n"
    )
    assert config.resolve_smtp_url() == "smtp://you%40gmail.com:app_pw@smtp.gmail.com:587"


def test_env_var_wins_for_kindle(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "kindle.conf").write_text("KINDLE_ADDR=file_xxx@kindle.com\n")
    monkeypatch.setenv("KINDLE_ADDR", "env_xxx@kindle.com")
    assert config.resolve_kindle_addr() == "env_xxx@kindle.com"


def test_kindle_falls_back_to_local_conf(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "kindle.conf").write_text("KINDLE_ADDR=me_abc123@kindle.com\n")
    assert config.resolve_kindle_addr() == "me_abc123@kindle.com"


def test_missing_smtp_raises(monkeypatch, tmp_path):
    # Empty cwd, no home config, no env var.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_smtp_sources", lambda: [tmp_path / ".env"])
    with pytest.raises(ConfigError):
        config.resolve_smtp_url()


def test_missing_kindle_raises(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_kindle_sources", lambda: [tmp_path / "kindle.conf"])
    with pytest.raises(ConfigError):
        config.resolve_kindle_addr()


def test_read_kv_missing_file_returns_none(tmp_path):
    assert config.read_kv(tmp_path / "nope.env", "SMTP_URL") is None
