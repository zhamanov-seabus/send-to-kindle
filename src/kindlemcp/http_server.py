"""Public HTTP server for kindlemcp — INFO ONLY, no sending, no credentials.

By design this hosted endpoint does **not** send documents and does **not**
accept anyone's credentials: nothing (no Gmail password, no Kindle address, no
document) passes through this server. Actual sending happens only on the user's
own machine via the local CLI / stdio MCP server (``pipx install kindlemcp``).

The server exposes:
  * ``/``        — a landing / info page
  * ``/health``  — a JSON health check
  * ``/mcp``     — an MCP endpoint whose single tool returns setup instructions
                   pointing the caller at the local install (it never sends).

Run with the ``kindlemcp-http`` console script. Binds to 127.0.0.1:$KINDLEMCP_PORT
(default 8861); a TLS-terminating reverse proxy (cloudflared) fronts it.
"""

from __future__ import annotations

import os
import time
from collections import deque

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from .landing import INDEX_HTML

DEFAULT_PORT = 8861
# Public hostname this server is served at; needed so MCP's DNS-rebinding
# protection accepts the Host header that cloudflared forwards.
PUBLIC_HOST = os.environ.get("KINDLEMCP_PUBLIC_HOST", "kindlemcp.itskills.kz")

# The single message this hosted endpoint returns instead of sending anything.
LOCAL_ONLY_NOTICE = (
    "This hosted endpoint does not send documents and never handles your "
    "credentials — nothing passes through this server. To actually send to "
    "your Kindle, run kindlemcp locally on your own machine: install it with "
    "`pipx install kindlemcp`, set your own SMTP_URL and KINDLE_ADDR, and use "
    "the local `kindlemcp` MCP server or the `kindlemcp-send` CLI. Setup guide: "
    "https://kindlemcp.itskills.kz"
)


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


def build_server() -> FastMCP:
    """Construct the info-only FastMCP HTTP server (no sending, no credentials)."""
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
        max_request_body_size=1024 * 1024,
        transport_security=security,
    )

    @mcp.tool()
    def send_to_kindle(title: str = "", content: str = "") -> str:
        """Explain how to send to a Kindle (this hosted endpoint does not send).

        For your security this shared server never processes credentials or
        documents. Install kindlemcp locally to actually send; this tool just
        returns the setup instructions.
        """
        return LOCAL_ONLY_NOTICE

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "kindlemcp-http"})

    @mcp.custom_route("/", methods=["GET"])
    async def index(_request: Request) -> HTMLResponse:
        return HTMLResponse(INDEX_HTML)

    return mcp


def main() -> None:
    """Run the info-only streamable-HTTP MCP server."""
    mcp = build_server()
    app = mcp.streamable_http_app()
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
