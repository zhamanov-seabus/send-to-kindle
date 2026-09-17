"""Landing page HTML served at ``/`` by the hosted MCP server.

Kept in its own module so the server code stays small. This is a public,
beginner-friendly explainer + copy-paste setup for the hosted endpoint and the
local package.
"""

from __future__ import annotations

INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>kindlemcp — send documents to your Kindle from AI</title>
<style>
 :root{color-scheme:dark}
 *{box-sizing:border-box}
 body{margin:0;font:16px/1.65 system-ui,-apple-system,Segoe UI,Arial,sans-serif;
   background:#0b1020;color:#e5e7eb}
 .wrap{max-width:820px;margin:0 auto;padding:6vh 22px 12vh}
 h1{font-size:2.1rem;margin:0 0 .15em;letter-spacing:-.5px}
 h2{font-size:1.35rem;margin:2.2em 0 .5em;padding-bottom:.25em;
   border-bottom:1px solid #1f2937}
 h3{font-size:1.05rem;margin:1.4em 0 .3em;color:#bfdbfe}
 p{margin:.5em 0}
 .tag{display:inline-block;background:#1d4ed8;color:#fff;font-size:.8rem;
   font-weight:700;padding:3px 10px;border-radius:999px;vertical-align:middle}
 .lead{font-size:1.12rem;color:#cbd5e1}
 a{color:#7dd3fc}
 code{background:#1e293b;color:#e2e8f0;padding:2px 6px;border-radius:4px;
   font-size:.88em}
 pre{background:#0f172a;border:1px solid #1f2937;border-radius:10px;
   padding:14px 16px;overflow:auto;font-size:.82rem;line-height:1.5}
 pre code{background:none;padding:0}
 .card{background:#111827;border:1px solid #1f2937;border-radius:12px;
   padding:16px 20px;margin:16px 0}
 .steps{counter-reset:s;list-style:none;padding:0;margin:0}
 .steps li{position:relative;padding:0 0 .9em 2.2em;margin:0}
 .steps li::before{counter-increment:s;content:counter(s);position:absolute;
   left:0;top:0;width:1.5em;height:1.5em;background:#1d4ed8;color:#fff;
   border-radius:50%;display:grid;place-items:center;font-size:.8rem;
   font-weight:700}
 table{width:100%;border-collapse:collapse;margin:.5em 0;font-size:.92rem}
 th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #1f2937;
   vertical-align:top}
 th{color:#93c5fd}
 .muted{color:#94a3b8}
 .pill{display:inline-block;background:#0f172a;border:1px solid #1f2937;
   border-radius:8px;padding:2px 8px;font-size:.8rem;margin-right:6px}
 footer{margin-top:3em;padding-top:1.2em;border-top:1px solid #1f2937;
   color:#94a3b8;font-size:.9rem}
</style></head><body><div class="wrap">

<h1>kindlemcp <span class="tag">MCP server + CLI</span></h1>
<p class="lead">Send any document to your Kindle from an AI assistant or the
command line. You give it text, a PDF, or an EPUB &mdash; it emails it to your
Kindle, and a minute later it is in your library.</p>
<p class="muted">This page is the endpoint's home. The service itself is an API
for AI clients (Claude, Codex, Gemini), not a clickable web app &mdash; you use
it from your assistant after a one-time setup below.</p>

<h2>What you get</h2>
<ul>
 <li><b>From your AI assistant:</b> say <i>&ldquo;summarize this and send it to
   my Kindle&rdquo;</i> and the assistant delivers it to your device.</li>
 <li><b>From the terminal:</b> <code>kindlemcp-send --title "Report" report.pdf</code></li>
 <li>Markdown is auto-converted to a clean EPUB; PDF and EPUB are sent as-is.</li>
</ul>

<h2>Before you start (one time, ~5 min)</h2>
<p>You need three things from your own accounts. kindlemcp never stores them.</p>
<ol class="steps">
 <li><b>A Gmail App Password.</b> In your Google Account &rarr; Security &rarr;
   2-Step Verification &rarr; <b>App passwords</b>, create one. It is a 16-character
   code used only by apps &mdash; not your normal Gmail password.</li>
 <li><b>Your Kindle email address.</b> On Amazon &rarr; <i>Manage Your Content and
   Devices</i> &rarr; <i>Preferences</i> &rarr; <b>Personal Document Settings</b>.
   It looks like <code>you_ab12cd@kindle.com</code>.</li>
 <li><b>Approve your sender.</b> On that same Amazon page, add your Gmail address
   to the <b>Approved Personal Document E-mail List</b>. Amazon silently drops
   documents from any address that is not approved &mdash; this is the #1 reason a
   document does not arrive.</li>
</ol>

<h2>Connect it &mdash; Option 1: Hosted (no install)</h2>
<p>Use this public endpoint directly. You pass <b>your own</b> credentials in the
headers; they are used only for that one request and never stored. Add the block
for your client, then restart it.</p>

<h3>Claude Desktop / Claude Code &middot; Gemini CLI <span class="pill">JSON</span></h3>
<p class="muted">Claude Desktop: <code>claude_desktop_config.json</code> &middot;
Claude Code: project <code>.mcp.json</code> &middot;
Gemini CLI: <code>~/.gemini/settings.json</code></p>
<pre><code>{
  "mcpServers": {
    "kindlemcp": {
      "type": "http",
      "url": "https://kindlemcp.itskills.kz/mcp",
      "headers": {
        "X-Kindlemcp-Smtp-Url": "smtp://you%40gmail.com:APP_PASSWORD@smtp.gmail.com:587",
        "X-Kindlemcp-Kindle-Addr": "you_ab12cd@kindle.com"
      }
    }
  }
}</code></pre>

<h3>OpenAI Codex CLI <span class="pill">TOML</span></h3>
<p class="muted">File: <code>~/.codex/config.toml</code></p>
<pre><code>[mcp_servers.kindlemcp]
url = "https://kindlemcp.itskills.kz/mcp"
http_headers = { "X-Kindlemcp-Smtp-Url" = "smtp://you%40gmail.com:APP_PASSWORD@smtp.gmail.com:587", "X-Kindlemcp-Kindle-Addr" = "you_ab12cd@kindle.com" }</code></pre>
<p class="muted">Note: write <code>@</code> in the Gmail address as
<code>%40</code> inside the SMTP URL (so <code>you@gmail.com</code> becomes
<code>you%40gmail.com</code>).</p>

<h2>Connect it &mdash; Option 2: Local (run it yourself)</h2>
<p>Prefer to keep everything on your machine? Install the package; nothing leaves
your computer except the email to Amazon.</p>
<pre><code># install (one of)
pipx install kindlemcp
uvx --from kindlemcp kindlemcp        # run without installing

# tell it your creds once (env, or a .env file)
export SMTP_URL="smtp://you%40gmail.com:APP_PASSWORD@smtp.gmail.com:587"
export KINDLE_ADDR="you_ab12cd@kindle.com"

# use the CLI directly
kindlemcp-send --title "My Report" report.pdf
echo "# Hello" | kindlemcp-send --title "Quick Note"</code></pre>
<p>To connect the local server to an assistant, register the <code>kindlemcp</code>
command as a stdio MCP server, e.g.
<code>claude mcp add kindlemcp -e SMTP_URL=... -e KINDLE_ADDR=... -- uvx --from kindlemcp kindlemcp</code>
(the same works for <code>codex mcp add</code> and <code>gemini mcp add</code>).</p>

<h2>How to use it (once connected)</h2>
<ul>
 <li>In your assistant: <i>&ldquo;Send this article to my Kindle&rdquo;</i> or
   <i>&ldquo;Write a 1-page summary of X and send it to my Kindle.&rdquo;</i></li>
 <li>The assistant calls the <code>send_to_kindle</code> tool with a title and the
   text; you get it on your device under that title.</li>
</ul>

<h2>Is it safe?</h2>
<p>The hosted endpoint is <b>multi-tenant</b>: every request carries its own
Gmail + Kindle details, they are used only for that single send, and they are
<b>never stored or logged</b>. The connection runs over HTTPS. If you would
rather nothing pass through a shared server at all, use Option 2 (local).</p>

<h2>Troubleshooting</h2>
<table>
 <tr><th>Symptom</th><th>Fix</th></tr>
 <tr><td>Document never arrives on the Kindle</td><td>Your Gmail is not in Amazon's
   <b>Approved</b> senders list. Add it (see step 3).</td></tr>
 <tr><td>&ldquo;missing credentials&rdquo; error</td><td>The headers/env with
   <code>SMTP_URL</code> and <code>KINDLE_ADDR</code> are missing or misspelled.</td></tr>
 <tr><td>&ldquo;Failed to send email&rdquo;</td><td>Wrong Gmail App Password, or you
   used your normal password. Create a fresh App Password.</td></tr>
 <tr><td>Markdown did not convert</td><td>Local use only: install
   <code>pandoc</code> (<code>brew install pandoc</code>). Not needed for PDF/EPUB.</td></tr>
</table>

<footer>
 Open source: <a href="https://github.com/zhamanov-seabus/send-to-kindle">github.com/zhamanov-seabus/send-to-kindle</a>
 &middot; PyPI: <code>pipx install kindlemcp</code>
 &middot; Health: <a href="/health">/health</a>
 &middot; MCP endpoint: <code>/mcp</code>
</footer>

</div></body></html>
"""
