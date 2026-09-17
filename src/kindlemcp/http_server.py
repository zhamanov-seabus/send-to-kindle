"""Multi-tenant streamable-HTTP MCP server for kindlemcp.

This is the PUBLIC-facing transport. Unlike the stdio server (:mod:`kindlemcp.
mcp_server`), it never uses any server-side SMTP / Kindle credentials. Each
caller supplies *their own* config on every request, so a shared public
endpoint cannot be abused to send mail as the host or spam the host's Kindle.

Per-request config is read from HTTP headers, or a Smithery-style base64 JSON
``config`` query parameter:

    * ``X-Kindlemcp-Smtp-Url``    / config key ``smtpUrl``   (or ``smtp_url``)
    * ``X-Kindlemcp-Kindle-Addr`` / config key ``kindleAddr`` (or ``kindle_addr``)

Headers win over the query param. Credentials are threaded into the send call
for that request only and are never stored or logged.

Run with the ``kindlemcp-http`` console script. Binds to 127.0.0.1:$KINDLEMCP_PORT
(default 8861); a TLS-terminating reverse proxy (cloudflared) fronts it.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import time
from collections import deque
from contextvars import ContextVar

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from .core import KindleError, send_markdown

SMTP_HEADER = "x-kindlemcp-smtp-url"
KINDLE_HEADER = "x-kindlemcp-kindle-addr"

DEFAULT_PORT = 8861
# Public hostname this server is served at; needed so MCP's DNS-rebinding
# protection accepts the Host header that cloudflared forwards.
PUBLIC_HOST = os.environ.get("KINDLEMCP_PUBLIC_HOST", "kindlemcp.itskills.kz")

# Per-request caller config, populated by ConfigMiddleware. Used as a fallback
# when the tool cannot reach the Starlette request off the MCP context.
_request_config: ContextVar[dict[str, str] | None] = ContextVar(
    "_request_config", default=None
)

_INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>kindlemcp</title>
<style>
 :root{color-scheme:light dark}
 body{margin:0;font:16px/1.6 system-ui,-apple-system,Segoe UI,Arial,sans-serif;
   background:#0b1020;color:#e5e7eb;padding:8vh 6vw;max-width:760px;margin:0 auto}
 h1{font-size:2rem;margin:0 0 .2em}
 .tag{color:#93c5fd;font-weight:600}
 code{background:#1e293b;color:#e2e8f0;padding:2px 6px;border-radius:4px;font-size:.9em}
 a{color:#7dd3fc}
 .card{background:#111827;border:1px solid #1f2937;border-radius:10px;
   padding:16px 20px;margin:18px 0}
 .muted{color:#94a3b8;font-size:.92rem}
</style></head><body>
<h1>kindlemcp <span class="tag">MCP server</span></h1>
<p>Send documents to a Kindle via Amazon Send-to-Kindle. This is an API endpoint
for AI assistants (Claude, Codex, Gemini) &mdash; not a website.</p>
<div class="card">
 <b>Endpoints</b><br>
 <code>/mcp</code> &mdash; the MCP endpoint (used by AI clients)<br>
 <code>/health</code> &mdash; <a href="/health">status check</a>
</div>
<div class="card">
 <b>Connect (HTTP MCP)</b>
 <pre><code>{
  "mcpServers": {
    "kindlemcp": {
      "type": "http",
      "url": "https://kindlemcp.itskills.kz/mcp",
      "headers": {
        "X-Kindlemcp-Smtp-Url": "smtp://you%40gmail.com:app_password@smtp.gmail.com:587",
        "X-Kindlemcp-Kindle-Addr": "you_xxx@kindle.com"
      }
    }
  }
}</code></pre>
 <p class="muted">Multi-tenant: you supply your own Gmail SMTP + Kindle address
 per request; they are used only for that call and never stored.</p>
</div>
<p class="muted">Also on PyPI: <code>pipx install kindlemcp</code> &middot;
 <a href="https://github.com/zhamanov-seabus/send-to-kindle">source</a></p>
</body></html>
"""


def _decode_config_query(raw: str) -> dict[str, str]:
    """Decode a Smithery-style base64-encoded JSON ``config`` query value."""
    try:
        padded = raw + "=" * (-len(raw) % 4)
        data = base64.urlsafe_b64decode(padded)
        obj = json.loads(data)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return {}
    if not isinstance(obj, dict):
        return {}
    out: dict[str, str] = {}
    smtp = obj.get("smtpUrl") or obj.get("smtp_url") or obj.get("SMTP_URL")
    kindle = obj.get("kindleAddr") or obj.get("kindle_addr") or obj.get("KINDLE_ADDR")
    if isinstance(smtp, str) and smtp.strip():
        out["smtp_url"] = smtp.strip()
    if isinstance(kindle, str) and kindle.strip():
        out["kindle_addr"] = kindle.strip()
    return out


def extract_config(request: Request) -> dict[str, str]:
    """Pull per-request caller config from headers, then the ``config`` query.

    Headers take precedence. Returns a dict that may contain ``smtp_url`` and/or
    ``kindle_addr`` (absent keys mean the caller did not provide that value).
    """
    cfg: dict[str, str] = {}
    raw_query = request.query_params.get("config")
    if raw_query:
        cfg.update(_decode_config_query(raw_query))
    smtp = request.headers.get(SMTP_HEADER)
    kindle = request.headers.get(KINDLE_HEADER)
    if smtp and smtp.strip():
        cfg["smtp_url"] = smtp.strip()
    if kindle and kindle.strip():
        cfg["kindle_addr"] = kindle.strip()
    return cfg


class ConfigMiddleware(BaseHTTPMiddleware):
    """Store each request's caller config in a contextvar for the tool to read."""

    async def dispatch(self, request: Request, call_next):
        token = _request_config.set(extract_config(request))
        try:
            return await call_next(request)
        finally:
            _request_config.reset(token)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Coarse per-client-IP fixed-window rate limit. A safety valve, not a WAF."""

    def __init__(self, app, max_requests: int = 60, window_seconds: float = 60.0):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits.setdefault(client, deque())
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return JSONResponse(
                {"error": "rate limit exceeded, slow down"}, status_code=429
            )
        hits.append(now)
        return await call_next(request)


def _caller_config(ctx: Context) -> dict[str, str]:
    """Best-effort read of the current request's caller config.

    Prefers the Starlette request threaded onto the MCP request context; falls
    back to the contextvar set by :class:`ConfigMiddleware`.
    """
    try:
        request = ctx.request_context.request
    except (AttributeError, LookupError, ValueError):
        request = None
    if isinstance(request, Request):
        return extract_config(request)
    return _request_config.get() or {}


def build_server() -> FastMCP:
    """Construct the multi-tenant FastMCP HTTP server."""
    port = int(os.environ.get("KINDLEMCP_PORT", DEFAULT_PORT))
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            PUBLIC_HOST,
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
        ],
        allowed_origins=[
            f"https://{PUBLIC_HOST}",
            f"http://{PUBLIC_HOST}",
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
        ],
    )
    mcp = FastMCP(
        "kindlemcp",
        host="127.0.0.1",
        port=port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        # Cap request bodies (1 MiB) — this is a metadata/markdown endpoint, not
        # a bulk file uploader.
        max_request_body_size=1024 * 1024,
        transport_security=security,
    )

    @mcp.tool()
    def send_to_kindle(
        ctx: Context,
        title: str,
        content: str,
    ) -> str:
        """Send a document to YOUR Kindle via Amazon Send-to-Kindle email.

        This is a shared, multi-tenant endpoint: you must supply your own
        credentials on each request (they are used only for that call and never
        stored):

        * ``X-Kindlemcp-Smtp-Url`` header, e.g.
          ``smtp://you%40gmail.com:app_password@smtp.gmail.com:587``
        * ``X-Kindlemcp-Kindle-Addr`` header, e.g. ``you_abc123@kindle.com``

        (Or a base64-JSON ``?config=`` query param with ``smtpUrl`` /
        ``kindleAddr``.)

        ``content`` is Markdown text; it is converted to EPUB and delivered.
        ``title`` becomes the document name on the Kindle.

        Note: unlike the local CLI/stdio server, this hosted endpoint does NOT
        accept a server-side file path — a shared public server must never read
        arbitrary files off the host. Send the document text as ``content``.
        """
        if not title or not title.strip():
            return "error: 'title' is required."
        if content is None or content.strip() == "":
            return "error: 'content' is required (Markdown text to send)."

        cfg = _caller_config(ctx)
        smtp_url = cfg.get("smtp_url")
        kindle_addr = cfg.get("kindle_addr")
        if not smtp_url or not kindle_addr:
            return (
                "error: missing credentials. This is a shared public endpoint "
                "with no default account. Send your own config via the "
                "'X-Kindlemcp-Smtp-Url' and 'X-Kindlemcp-Kindle-Addr' headers "
                "(or a base64-JSON '?config=' query param with 'smtpUrl' and "
                "'kindleAddr')."
            )

        try:
            result = send_markdown(
                content,
                title,
                smtp_url=smtp_url,
                kindle_addr=kindle_addr,
            )
        except KindleError as exc:
            return f"error: {exc}"
        except Exception as exc:  # noqa: BLE001 - never crash the server on a call
            return f"error: unexpected failure: {exc}"

        return result.message()

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "kindlemcp-http"})

    @mcp.custom_route("/", methods=["GET"])
    async def index(_request: Request) -> HTMLResponse:
        return HTMLResponse(_INDEX_HTML)

    return mcp


def main() -> None:
    """Run the multi-tenant streamable-HTTP MCP server."""
    mcp = build_server()
    app = mcp.streamable_http_app()
    app.add_middleware(ConfigMiddleware)
    app.add_middleware(RateLimitMiddleware)

    import uvicorn

    uvicorn.run(
        app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
