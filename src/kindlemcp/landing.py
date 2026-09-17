"""Landing page HTML served at ``/`` by the hosted MCP server.

The hosted endpoint is info-only: it never sends documents or handles
credentials. This page explains what kindlemcp is and how to run it locally.
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
 .note{background:#0f1b2e;border:1px solid #1e3a5f;border-radius:12px;
   padding:14px 18px;margin:16px 0;color:#cbd5e1}
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
 footer{margin-top:3em;padding-top:1.2em;border-top:1px solid #1f2937;
   color:#94a3b8;font-size:.9rem}
</style></head><body><div class="wrap">

<h1>kindlemcp <span class="tag">MCP server + CLI</span></h1>
<p class="lead">Send any document to your Kindle from an AI assistant or the
command line. You give it text, a PDF, or an EPUB &mdash; it emails it to your
Kindle, and a minute later it is in your library.</p>

<div class="note">
 <b>This site is just the project home.</b> The hosted endpoint here does
 <b>not</b> send documents and <b>never handles your credentials</b> &mdash;
 nothing (no password, no document) passes through this server. You run kindlemcp
 <b>on your own machine</b>, where your Gmail details stay local. Setup is below.
</div>

<h2>What you get</h2>
<ul>
 <li><b>From your AI assistant:</b> say <i>&ldquo;summarize this and send it to
   my Kindle&rdquo;</i> and the assistant delivers it to your device.</li>
 <li><b>From the terminal:</b> <code>kindlemcp-send --title "Report" report.pdf</code></li>
 <li>Markdown is auto-converted to a clean EPUB; PDF and EPUB are sent as-is.</li>
</ul>

<h2>Before you start (one time, ~5 min)</h2>
<p>You need three things from your own accounts. They stay on your machine.</p>
<ol class="steps">
 <li><b>A Gmail App Password.</b> Google Account &rarr; Security &rarr; 2-Step
   Verification &rarr; <b>App passwords</b>. A 16-character code used only by
   apps &mdash; not your normal Gmail password.</li>
 <li><b>Your Kindle email address.</b> Amazon &rarr; <i>Manage Your Content and
   Devices</i> &rarr; <i>Preferences</i> &rarr; <b>Personal Document Settings</b>.
   It looks like <code>you_ab12cd@kindle.com</code>.</li>
 <li><b>Approve your sender.</b> On that same Amazon page, add your Gmail address
   to the <b>Approved Personal Document E-mail List</b>. Amazon silently drops
   documents from any address that is not approved &mdash; this is the #1 reason a
   document does not arrive.</li>
</ol>

<h2>Install &amp; connect (local)</h2>
<p>Everything runs on your computer. Nothing goes through this server.</p>
<pre><code># install (one of)
pipx install kindlemcp
uvx --from kindlemcp kindlemcp        # run without installing

# tell it your creds once (env, or a .env file next to you)
export SMTP_URL="smtp://you%40gmail.com:APP_PASSWORD@smtp.gmail.com:587"
export KINDLE_ADDR="you_ab12cd@kindle.com"

# use the CLI directly
kindlemcp-send --title "My Report" report.pdf
echo "# Hello" | kindlemcp-send --title "Quick Note"</code></pre>
<p class="muted">Write <code>@</code> in the Gmail address as <code>%40</code>
inside the SMTP URL (so <code>you@gmail.com</code> &rarr;
<code>you%40gmail.com</code>). Markdown conversion needs
<code>pandoc</code> (<code>brew install pandoc</code>); PDF/EPUB do not.</p>

<h3>Connect it to your AI assistant (local MCP)</h3>
<p>Register the local <code>kindlemcp</code> command as an MCP server &mdash; one
line, and your credentials stay on your machine:</p>
<pre><code># Claude Code
claude mcp add kindlemcp -e SMTP_URL=... -e KINDLE_ADDR=... -- uvx --from kindlemcp kindlemcp

# OpenAI Codex CLI
codex mcp add kindlemcp -- uvx --from kindlemcp kindlemcp

# Gemini CLI
gemini mcp add kindlemcp uvx --from kindlemcp kindlemcp</code></pre>
<p>Or add it by hand to your client config (Claude Desktop
<code>claude_desktop_config.json</code>, or a project <code>.mcp.json</code>):</p>
<pre><code>{
  "mcpServers": {
    "kindlemcp": {
      "command": "uvx",
      "args": ["--from", "kindlemcp", "kindlemcp"],
      "env": {
        "SMTP_URL": "smtp://you%40gmail.com:APP_PASSWORD@smtp.gmail.com:587",
        "KINDLE_ADDR": "you_ab12cd@kindle.com"
      }
    }
  }
}</code></pre>
<p>Then just say <i>&ldquo;send this to my Kindle&rdquo;</i> in your assistant.</p>

<h2>Is it safe?</h2>
<p><b>Yes &mdash; because your credentials never leave your computer.</b> kindlemcp
runs locally: it logs in to Gmail directly from your machine and sends the mail.
The public server at this domain is only a landing page and a health check; it
does not send documents and does not receive or store anyone's password.</p>

<h2>Troubleshooting</h2>
<table>
 <tr><th>Symptom</th><th>Fix</th></tr>
 <tr><td>Document never arrives on the Kindle</td><td>Your Gmail is not in Amazon's
   <b>Approved</b> senders list. Add it (see step 3).</td></tr>
 <tr><td>&ldquo;SMTP_URL / KINDLE_ADDR not set&rdquo;</td><td>The env vars (or
   <code>.env</code>) are missing or misspelled.</td></tr>
 <tr><td>&ldquo;Failed to send email&rdquo;</td><td>Wrong Gmail App Password, or you
   used your normal password. Create a fresh App Password.</td></tr>
 <tr><td>Markdown did not convert</td><td>Install <code>pandoc</code>
   (<code>brew install pandoc</code>). Not needed for PDF/EPUB.</td></tr>
</table>

<footer>
 Open source: <a href="https://github.com/zhamanov-seabus/send-to-kindle">github.com/zhamanov-seabus/send-to-kindle</a>
 &middot; PyPI: <code>pipx install kindlemcp</code>
 &middot; Health: <a href="/health">/health</a>
</footer>

</div></body></html>
"""
