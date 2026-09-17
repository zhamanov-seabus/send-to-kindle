# send-to-kindle

Send any document straight to your Kindle from the command line, via Amazon's
**Send-to-Kindle** email service. Markdown is converted to EPUB with `pandoc`;
PDF and EPUB files are sent as-is.

No secrets live in the code — the Gmail SMTP credential and your Kindle address
are read from local config files that are gitignored.

## Requirements

- Python 3.10+
- [`pandoc`](https://pandoc.org/) (only needed for Markdown input) — `brew install pandoc`
- A Gmail account with a **App Password** (SMTP)
- Your **Send-to-Kindle** email address, and the Gmail sender added to your
  Amazon *approved senders* list
  (Amazon → *Preferences* → *Personal Document Settings*)

## Setup

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

Both files are in `.gitignore` and never committed.

## Usage

```bash
# Markdown -> EPUB -> Kindle
./kindle_send.py --title "My Report" report.md

# PDF or EPUB, sent as-is
./kindle_send.py --title "My Report" report.pdf

# Markdown from stdin
echo "# Hello" | ./kindle_send.py --title "Quick Note"
```

The `--title` becomes the email subject, which Amazon uses as the document name
on the Kindle.

## Config resolution order

| Setting | Looked up in order |
|---|---|
| `SMTP_URL` | env var → `./.env` → `~/.kindle.env` → `~/code/aicourse/.env` (legacy) |
| `KINDLE_ADDR` | env var → `./kindle.conf` → `~/.kindle.conf` |

## License

MIT
