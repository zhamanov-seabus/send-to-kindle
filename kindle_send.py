#!/usr/bin/env python3
"""Send a document to your Kindle via Amazon Send-to-Kindle (email).

Converts Markdown to EPUB with pandoc, then emails it to the Send-to-Kindle
address from an approved Gmail sender. PDFs and EPUBs are attached as-is.

No secrets live in this file. Configuration is resolved in order:
  * SMTP_URL   — env var, else `.env` next to this script, else ~/.kindle.env,
                 else ~/code/aicourse/.env (legacy).
  * KINDLE_ADDR — env var, else `kindle.conf` next to this script, else
                 ~/.kindle.conf.
Copy `.env.example` -> `.env` and `kindle.conf.example` -> `kindle.conf`
(or ~/.kindle.conf) and fill them in. Both are gitignored.

Usage:
  kindle_send.py --title "My Report" report.md
  kindle_send.py --title "My Report" report.pdf      # already an ebook/pdf
  echo "# Hi" | kindle_send.py --title "Note"         # markdown on stdin
"""
import argparse
import os
import ssl
import smtplib
import subprocess
import sys
import tempfile
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse, unquote

HERE = Path(__file__).resolve().parent
# SMTP_URL search path (first hit wins), skipping the env var handled below.
SMTP_SOURCES = [
    HERE / ".env",
    Path.home() / ".kindle.env",
    Path.home() / "code" / "aicourse" / ".env",  # legacy location
]
# KINDLE_ADDR search path.
KINDLE_SOURCES = [
    HERE / "kindle.conf",
    Path.home() / ".kindle.conf",
]


def read_kv(path: Path, key: str) -> str | None:
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        return None
    return None


def resolve(key: str, sources: list[Path]) -> str | None:
    """Env var wins, then the first config file that defines `key`."""
    val = os.environ.get(key)
    if val:
        return val
    for src in sources:
        val = read_kv(src, key)
        if val:
            return val
    return None


def to_epub(src: Path, title: str) -> tuple[Path, str, str]:
    """Return (path, mime_subtype, filename) of the file to attach."""
    ext = src.suffix.lower()
    if ext in (".epub",):
        return src, "epub+zip", src.name
    if ext in (".pdf",):
        return src, "pdf", src.name
    if ext in (".md", ".markdown", ".txt"):
        out = Path(tempfile.mkdtemp()) / (safe(title) + ".epub")
        subprocess.run(
            ["pandoc", str(src), "-o", str(out), "--metadata", f"title={title}"],
            check=True,
        )
        return out, "epub+zip", out.name
    raise SystemExit(f"Unsupported file type: {ext}")


def safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip() or "Document"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="Markdown/EPUB/PDF file (or read Markdown from stdin)")
    ap.add_argument("--title", required=True, help="Document title (used on the Kindle)")
    args = ap.parse_args()

    smtp_url = resolve("SMTP_URL", SMTP_SOURCES)
    if not smtp_url:
        raise SystemExit(
            "SMTP_URL not set (env, ./.env, ~/.kindle.env). See .env.example."
        )
    kindle = resolve("KINDLE_ADDR", KINDLE_SOURCES)
    if not kindle:
        raise SystemExit(
            "KINDLE_ADDR not set (env, ./kindle.conf, ~/.kindle.conf). "
            "See kindle.conf.example."
        )

    if args.file:
        src = Path(args.file)
    else:
        tmp = Path(tempfile.mkdtemp()) / "input.md"
        tmp.write_text(sys.stdin.read())
        src = tmp

    attach, subtype, filename = to_epub(src, args.title)

    u = urlparse(smtp_url)
    user, pw, host, port = unquote(u.username), unquote(u.password), u.hostname, u.port or 587
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = kindle
    msg["Subject"] = args.title  # Kindle uses the subject as the document name
    msg.set_content("Sent by your AI agent.")
    msg.add_attachment(
        attach.read_bytes(), maintype="application", subtype=subtype, filename=filename
    )
    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port) as s:
        s.starttls(context=ctx)
        s.login(user, pw)
        s.send_message(msg)
    print(f"Sent '{args.title}' ({filename}) to {kindle}")


if __name__ == "__main__":
    main()
