"""Tests for the multi-tenant HTTP transport. NEVER sends real email.

Covers per-request config extraction (headers + base64 ``config`` query) and
the HTTP tool's per-request credential threading and refusal when creds are
absent. SMTP is mocked; no network I/O.
"""

from __future__ import annotations

import base64
import json
import shutil
from email.message import EmailMessage

import pytest
from starlette.requests import Request

from kindlemcp import core, http_server
from kindlemcp.http_server import (
    _request_config,
    build_server,
    extract_config,
)

KINDLE = "me_abc123@kindle.com"
SMTP = "smtp://you%40gmail.com:app_pw@smtp.gmail.com:587"


class _FakeSMTP:
    sent: list[EmailMessage] = []
    logins: list[tuple[str, str]] = []
    hosts: list[tuple[str, int]] = []

    def __init__(self, host, port):
        type(self).hosts.append((host, port))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        pass

    def login(self, user, pw):
        type(self).logins.append((user, pw))

    def send_message(self, msg):
        type(self).sent.append(msg)


@pytest.fixture
def fake_smtp(monkeypatch):
    _FakeSMTP.sent = []
    _FakeSMTP.logins = []
    _FakeSMTP.hosts = []
    monkeypatch.setattr(core.smtplib, "SMTP", _FakeSMTP)
    # Deliberately NO env creds: the public server must not fall back to any.
    monkeypatch.delenv("SMTP_URL", raising=False)
    monkeypatch.delenv("KINDLE_ADDR", raising=False)
    return _FakeSMTP


def _make_request(headers: dict[str, str] | None = None, query: str = "") -> Request:
    raw_headers = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp",
        "headers": raw_headers,
        "query_string": query.encode(),
    }
    return Request(scope)


class _FakeCtx:
    """A context whose request cannot be reached, forcing the contextvar path."""

    request_context = None


def _tool_fn():
    mcp = build_server()
    tool = mcp._tool_manager.get_tool("send_to_kindle")
    return tool.fn


def test_extract_config_from_headers():
    req = _make_request(
        {"X-Kindlemcp-Smtp-Url": SMTP, "X-Kindlemcp-Kindle-Addr": KINDLE}
    )
    cfg = extract_config(req)
    assert cfg == {"smtp_url": SMTP, "kindle_addr": KINDLE}


def test_extract_config_from_base64_query():
    payload = base64.urlsafe_b64encode(
        json.dumps({"smtpUrl": SMTP, "kindleAddr": KINDLE}).encode()
    ).decode()
    req = _make_request(query=f"config={payload}")
    cfg = extract_config(req)
    assert cfg == {"smtp_url": SMTP, "kindle_addr": KINDLE}


def test_headers_win_over_query():
    payload = base64.urlsafe_b64encode(
        json.dumps({"smtpUrl": "smtp://q", "kindleAddr": "q@kindle.com"}).encode()
    ).decode()
    req = _make_request(
        {"X-Kindlemcp-Smtp-Url": SMTP, "X-Kindlemcp-Kindle-Addr": KINDLE},
        query=f"config={payload}",
    )
    cfg = extract_config(req)
    assert cfg["smtp_url"] == SMTP
    assert cfg["kindle_addr"] == KINDLE


def test_extract_config_empty_when_absent():
    assert extract_config(_make_request()) == {}


def test_tool_refuses_without_credentials(fake_smtp):
    fn = _tool_fn()
    token = _request_config.set({})
    try:
        out = fn(_FakeCtx(), title="T", content="# Hi")
    finally:
        _request_config.reset(token)
    assert "missing credentials" in out.lower()
    assert not fake_smtp.sent  # nothing sent


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_tool_sends_with_per_request_creds(fake_smtp):
    fn = _tool_fn()
    token = _request_config.set({"smtp_url": SMTP, "kindle_addr": KINDLE})
    try:
        out = fn(_FakeCtx(), title="Rep", content="# Hi\n\nBody.")
    finally:
        _request_config.reset(token)
    # content is Markdown -> EPUB named after the title.
    assert out == f"Sent 'Rep' (Rep.epub) to {KINDLE}"
    assert fake_smtp.logins == [("you@gmail.com", "app_pw")]
    assert fake_smtp.sent[0]["To"] == KINDLE


def test_tool_requires_content(fake_smtp):
    """The hosted tool takes only content; missing content/title is rejected."""
    fn = _tool_fn()
    token = _request_config.set({"smtp_url": SMTP, "kindle_addr": KINDLE})
    try:
        assert "content" in fn(_FakeCtx(), title="T", content="").lower()
        assert "title" in fn(_FakeCtx(), title="", content="# Hi").lower()
    finally:
        _request_config.reset(token)
    assert not fake_smtp.sent


def test_caller_config_reads_request_off_context(fake_smtp):
    """When the Starlette request is on the MCP context, it is used directly."""

    class CtxWithReq:
        class request_context:  # noqa: N801 - mimic attribute chain
            request = _make_request(
                {"X-Kindlemcp-Smtp-Url": SMTP, "X-Kindlemcp-Kindle-Addr": KINDLE}
            )

    cfg = http_server._caller_config(CtxWithReq())
    assert cfg == {"smtp_url": SMTP, "kindle_addr": KINDLE}
