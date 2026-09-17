# kindlemcp

Send any document straight to your Kindle, via Amazon's **Send-to-Kindle**
email service. Ships as both a **command-line tool** and an **MCP server**, so
you can send from a shell or straight from an AI assistant (Claude Desktop,
Claude Code, etc.).

Markdown is converted to EPUB with `pandoc`; PDF and EPUB files are sent as-is.

No secrets live in the code: the Gmail SMTP credential and your Kindle address
are read from the environment or from local config files that are gitignored.

## Why

Long AI answers, articles and PDFs are tiring to read on a glaring screen.
kindlemcp puts them on your Kindle, so you read on calm, eye-friendly e-ink
instead of another bright display.

| The problem | The fix |
|:---:|:---:|
| ![Screen fatigue](docs/problem-screen-fatigue.jpg) | ![Reading on Kindle](docs/solution-eink-reading.jpg) |
| Squinting at long text on a bright screen | The same content, on your Kindle |

## How it works

kindlemcp runs on your own machine. Your AI assistant (or the CLI) calls it, it
converts Markdown to a clean EPUB (PDF and EPUB pass through), and emails the
document to your Kindle through your own Gmail. Your credentials never leave your
computer.

![kindlemcp architecture](docs/architecture.png)

## Requirements

- Python 3.10+
- [`pandoc`](https://pandoc.org/) (only needed for Markdown input) — `brew install pandoc`.
  `pandoc` is an external binary, not a Python dependency.
- A Gmail account with an **App Password** (for SMTP).
- Your **Send-to-Kindle** email address, and the Gmail sender added to your
  Amazon **approved senders** list (Amazon → *Preferences* → *Personal Document
  Settings* → *Approved Personal Document E-mail List*). This is a one-time
  step; documents from any other sender are silently dropped by Amazon.

## Install

```bash
pipx install kindlemcp          # installs `kindlemcp` (MCP) and `kindlemcp-send` (CLI)
# or run without installing:
uvx --from kindlemcp kindlemcp-send --title "Note" report.md
```

For local development from a checkout:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Both values can come from the environment or a config file. Copy the examples:

```bash
cp .env.example .env                 # fill in SMTP_URL
cp kindle.conf.example kindle.conf   # fill in KINDLE_ADDR  (or use ~/.kindle.conf)
```

`.env`:

```
SMTP_URL=smtp://you%40gmail.com:your_app_password@smtp.gmail.com:587
```

`kindle.conf` (or `~/.kindle.conf`):

```
KINDLE_ADDR=you_xxxxxx@kindle.com
```

Both files are gitignored and never committed.

### Config resolution order

| Setting | Looked up in order |
|---|---|
| `SMTP_URL` | env var → `./.env` → `~/.kindle.env` → `~/code/aicourse/.env` (legacy) |
| `KINDLE_ADDR` | env var → `./kindle.conf` → `~/.kindle.conf` |

## CLI usage

```bash
# Markdown -> EPUB -> Kindle
kindlemcp-send --title "My Report" report.md

# PDF or EPUB, sent as-is
kindlemcp-send --title "My Report" report.pdf

# Markdown from stdin
echo "# Hello" | kindlemcp-send --title "Quick Note"
```

`--title` becomes the email subject, which Amazon uses as the document name on
the Kindle.

The old `./kindle_send.py` script still works — it is now a thin shim that calls
the package.

## MCP server

The `kindlemcp` command runs an MCP server over stdio exposing a single tool:

- **`send_to_kindle(title, content?, file_path?)`** — provide exactly one of
  `content` (Markdown text, converted to EPUB) or `file_path` (an existing
  `.md` / `.pdf` / `.epub` file). Returns a human-readable status string.

### Claude Desktop / `.mcp.json`

Add this to your MCP client config (Claude Desktop `claude_desktop_config.json`,
or a project `.mcp.json` for Claude Code):

```json
{
  "mcpServers": {
    "kindlemcp": {
      "command": "uvx",
      "args": ["--from", "kindlemcp", "kindlemcp"],
      "env": {
        "SMTP_URL": "smtp://you%40gmail.com:your_app_password@smtp.gmail.com:587",
        "KINDLE_ADDR": "you_xxxxxx@kindle.com"
      }
    }
  }
}
```

If you installed with `pipx`, use the installed command directly instead:

```json
{
  "mcpServers": {
    "kindlemcp": {
      "command": "kindlemcp",
      "env": {
        "SMTP_URL": "smtp://you%40gmail.com:your_app_password@smtp.gmail.com:587",
        "KINDLE_ADDR": "you_xxxxxx@kindle.com"
      }
    }
  }
}
```

You can omit the `env` block and rely on the config files above instead. Either
way, the Gmail sender in `SMTP_URL` must be on your Amazon approved-senders
list, and `pandoc` must be on `PATH` for Markdown conversion.

## Development

```bash
pip install -e ".[dev]"
python -m pytest      # tests mock SMTP — they never send a real email
ruff check .
```

## License

MIT
