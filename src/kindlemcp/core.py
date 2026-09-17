"""Pure send logic for kindlemcp.

Converts Markdown to EPUB with pandoc (subprocess), passes PDF/EPUB through
as-is, builds an email, and sends it via Gmail SMTP over STARTTLS.

This module raises typed exceptions and returns a :class:`SendResult`. It has
no argparse and no print side effects; the CLI and MCP server map its
exceptions to friendly messages at the edges.
"""

from __future__ import annotations

import smtplib
import ssl
import subprocess
import tempfile
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import unquote, urlparse

from .config import ConfigError, resolve_kindle_addr, resolve_smtp_url

__all__ = [
    "SendResult",
    "KindleError",
    "ConfigError",
    "ConversionError",
    "UnsupportedFileTypeError",
    "SendError",
    "safe_title",
    "prepare_attachment",
    "send_file",
    "send_markdown",
]

# Markdown-like inputs that get converted to EPUB via pandoc.
_MARKDOWN_EXTS = {".md", ".markdown", ".txt"}


class KindleError(RuntimeError):
    """Base class for kindlemcp errors."""


class ConversionError(KindleError):
    """Raised when pandoc conversion fails or pandoc is unavailable."""


class UnsupportedFileTypeError(KindleError):
    """Raised for a file whose extension we cannot send."""


class SendError(KindleError):
    """Raised when the email could not be sent over SMTP."""


@dataclass(frozen=True)
class SendResult:
    """Outcome of a successful send."""

    title: str
    filename: str
    kindle_addr: str

    def message(self) -> str:
        return f"Sent '{self.title}' ({self.filename}) to {self.kindle_addr}"


def safe_title(s: str) -> str:
    """Sanitize a title into a filesystem-safe base name."""
    cleaned = "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip()
    return cleaned or "Document"


def prepare_attachment(src: Path, title: str) -> tuple[Path, str, str]:
    """Return ``(path, mime_subtype, filename)`` of the file to attach.

    EPUB and PDF are passed through as-is; Markdown/text is converted to EPUB
    with pandoc. Raises :class:`UnsupportedFileTypeError` for other types and
    :class:`ConversionError` if pandoc fails or is missing.
    """
    ext = src.suffix.lower()
    if ext == ".epub":
        return src, "epub+zip", src.name
    if ext == ".pdf":
        return src, "pdf", src.name
    if ext in _MARKDOWN_EXTS:
        out = Path(tempfile.mkdtemp()) / (safe_title(title) + ".epub")
        try:
            subprocess.run(
                ["pandoc", str(src), "-o", str(out), "--metadata", f"title={title}"],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise ConversionError(
                "pandoc not found. Install it (e.g. `brew install pandoc`) to "
                "convert Markdown to EPUB."
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or "").strip()
            raise ConversionError(
                f"pandoc failed to convert {src.name}"
                + (f": {detail}" if detail else "")
            ) from exc
        return out, "epub+zip", out.name
    raise UnsupportedFileTypeError(f"Unsupported file type: {ext or '(none)'}")


def _build_message(
    smtp_user: str,
    kindle_addr: str,
    title: str,
    attach_path: Path,
    subtype: str,
    filename: str,
) -> EmailMessage:
    """Build the outgoing email with the document attached."""
    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = kindle_addr
    msg["Subject"] = title  # Kindle uses the subject as the document name.
    msg.set_content("Sent by your AI agent.")
    msg.add_attachment(
        attach_path.read_bytes(),
        maintype="application",
        subtype=subtype,
        filename=filename,
    )
    return msg


def _send_message(smtp_url: str, msg: EmailMessage) -> None:
    """Send an already-built message via SMTP STARTTLS."""
    u = urlparse(smtp_url)
    if not u.hostname or u.username is None or u.password is None:
        raise ConfigError(
            "SMTP_URL is malformed. Expected "
            "smtp://user%40gmail.com:app_password@smtp.gmail.com:587"
        )
    user = unquote(u.username)
    pw = unquote(u.password)
    host = u.hostname
    port = u.port or 587
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP(host, port) as s:
            s.starttls(context=ctx)
            s.login(user, pw)
            s.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise SendError(f"Failed to send email via {host}:{port}: {exc}") from exc


def send_file(src: Path, title: str) -> SendResult:
    """Send an existing file (md/pdf/epub) to the configured Kindle address.

    Resolves config, prepares the attachment, and emails it. Raises the typed
    exceptions in this module (and :class:`ConfigError`) on failure.
    """
    src = Path(src)
    if not src.is_file():
        raise UnsupportedFileTypeError(f"File not found: {src}")

    smtp_url = resolve_smtp_url()
    kindle_addr = resolve_kindle_addr()

    attach_path, subtype, filename = prepare_attachment(src, title)

    u = urlparse(smtp_url)
    smtp_user = unquote(u.username) if u.username else ""
    msg = _build_message(smtp_user, kindle_addr, title, attach_path, subtype, filename)
    _send_message(smtp_url, msg)
    return SendResult(title=title, filename=filename, kindle_addr=kindle_addr)


def send_markdown(content: str, title: str) -> SendResult:
    """Write Markdown ``content`` to a temp .md file, convert, and send."""
    tmp = Path(tempfile.mkdtemp()) / (safe_title(title) + ".md")
    tmp.write_text(content, encoding="utf-8")
    return send_file(tmp, title)
