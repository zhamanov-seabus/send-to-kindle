"""Tests for the info-only hosted HTTP server.

The hosted endpoint never sends documents and never handles credentials, so
these tests assert exactly that: the tool returns the local-only notice, and no
credential plumbing exists.
"""

from __future__ import annotations

import asyncio

from kindlemcp import http_server
from kindlemcp.http_server import (
    LOCAL_ONLY_NOTICE,
    RateLimitMiddleware,
    build_server,
)


def test_notice_points_to_local_install():
    text = LOCAL_ONLY_NOTICE.lower()
    assert "pipx install kindlemcp" in text
    assert "does not send" in text
    assert "never" in text  # never handles credentials


def test_server_builds_and_registers_tool():
    mcp = build_server()
    assert mcp.name == "kindlemcp"
    tools = asyncio.run(mcp.list_tools())
    names = [t.name for t in tools]
    assert names == ["send_to_kindle"]


def test_tool_returns_local_only_notice():
    mcp = build_server()
    # call_tool returns a (content, structured) tuple in the FastMCP SDK; the
    # structured payload carries the tool's return value.
    result = asyncio.run(mcp.call_tool("send_to_kindle", {"title": "x", "content": "y"}))
    text = str(result)
    assert "pipx install kindlemcp" in text
    # No credentials are accepted, so nothing was sent regardless of args.
    assert "does not send" in text.lower()


def test_no_credential_plumbing_remains():
    # The credential-handling surface was removed entirely.
    for gone in (
        "extract_config",
        "_request_config",
        "ConfigMiddleware",
        "SMTP_HEADER",
        "KINDLE_HEADER",
        "_caller_config",
    ):
        assert not hasattr(http_server, gone), f"{gone} should be gone"


def test_rate_limit_middleware_constructs():
    mw = RateLimitMiddleware(app=None, max_requests=5, window_seconds=1.0)
    assert mw.max_requests == 5
