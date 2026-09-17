# kindlemcp — remote HTTP transport deploy notes

Hosts the multi-tenant streamable-HTTP MCP server on the Mac Mini at
**https://kindlemcp.itskills.kz/mcp**, mirroring the itskills launchd +
cloudflared named-tunnel pattern (same as `aicourse`).

## Components

- `com.kindlemcp.web.plist` — launchd job running `kindlemcp-http` (the ASGI MCP
  app) on `127.0.0.1:8861`, `KeepAlive`, logs to `/tmp/kindlemcp-web.{out,err}`.
  Runs from the dedicated `.venv-serve` virtualenv. **No SMTP/Kindle creds** are
  set here — the server is multi-tenant and each caller supplies their own.
- `com.kindlemcp.tunnel.plist` — launchd job running
  `cloudflared --config ~/.cloudflared/kindlemcp.yml tunnel run kindlemcp`.
- `kindlemcp.yml` — cloudflared config, ingress
  `kindlemcp.itskills.kz → http://127.0.0.1:8861`, 404 fallback. Install a copy
  at `~/.cloudflared/kindlemcp.yml`.

Tunnel: `kindlemcp` / UUID `0246f210-49f6-46ac-9bd4-b3edfdf383d1`.

## Serve venv (build once)

```
cd /Users/azamat/code/send-to-kindle
python3 -m venv .venv-serve
.venv-serve/bin/pip install -e .
```

## Tunnel + DNS (done once)

```
cloudflared tunnel create kindlemcp
cloudflared tunnel route dns kindlemcp kindlemcp.itskills.kz
# If the route misbinds to another tunnel (a known cloudflared quirk):
cloudflared tunnel route dns --overwrite-dns kindlemcp kindlemcp.itskills.kz
```

## Install the launchd jobs

```
cp deploy/com.kindlemcp.web.plist    ~/Library/LaunchAgents/
cp deploy/com.kindlemcp.tunnel.plist ~/Library/LaunchAgents/
cp deploy/kindlemcp.yml              ~/.cloudflared/kindlemcp.yml   # if not present
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kindlemcp.web.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kindlemcp.tunnel.plist
```

To reload after an edit: `launchctl bootout gui/$(id -u)/com.kindlemcp.web`
then bootstrap again (same for `.tunnel`).

## Verify

```
curl -s http://127.0.0.1:8861/health           # local: {"status":"ok",...}
curl -s https://kindlemcp.itskills.kz/health   # public via tunnel: same
```

MCP handshake (stateless streamable HTTP):

```
curl -s -X POST https://kindlemcp.itskills.kz/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Per-request config (multi-tenant)

Every caller supplies their own credentials — never stored or logged:

- Header `X-Kindlemcp-Smtp-Url`, e.g.
  `smtp://you%40gmail.com:app_password@smtp.gmail.com:587`
- Header `X-Kindlemcp-Kindle-Addr`, e.g. `you_abc123@kindle.com`
- Or a base64-encoded JSON `?config=` query param with keys `smtpUrl` /
  `kindleAddr` (Smithery style). Headers win over the query param.
