"""Tests for core send logic. NEVER sends a real email: smtplib is mocked."""

from __future__ import annotations

import shutil
import subprocess
from email.message import EmailMessage

import pytest

from kindlemcp import core
from kindlemcp.core import (
    SendResult,
    UnsupportedFileTypeError,
    prepare_attachment,
    send_file,
    send_markdown,
)

KINDLE = "me_abc123@kindle.com"
SMTP = "smtp://you%40gmail.com:app_pw@smtp.gmail.com:587"


class _FakeSMTP:
    """Records interactions instead of touching the network."""

    sent: list[EmailMessage] = []
    logins: list[tuple[str, str]] = []
    hosts: list[tuple[str, int]] = []

    def __init__(self, host, port):
        type(self).hosts.append((host, port))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        pass

    def login(self, user, pw):
        type(self).logins.append((user, pw))

    def send_message(self, msg):
        type(self).sent.append(msg)


@pytest.fixture
def fake_smtp(monkeypatch):
    _FakeSMTP.sent = []
    _FakeSMTP.logins = []
    _FakeSMTP.hosts = []
    monkeypatch.setattr(core.smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setenv("SMTP_URL", SMTP)
    monkeypatch.setenv("KINDLE_ADDR", KINDLE)
    return _FakeSMTP


def _only_attachment(msg: EmailMessage):
    parts = list(msg.iter_attachments())
    assert len(parts) == 1
    return parts[0]


def test_safe_title():
    assert core.safe_title("Hello / World!") == "Hello _ World_"
    assert core.safe_title("///") == "___"  # non-empty after sanitizing
    assert core.safe_title("") == "Document"  # empty -> fallback


def test_send_pdf_builds_correct_message(fake_smtp, tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    result = send_file(pdf, "My Report")

    assert isinstance(result, SendResult)
    assert result.kindle_addr == KINDLE
    assert result.filename == "report.pdf"
    assert result.message() == f"Sent 'My Report' (report.pdf) to {KINDLE}"

    assert len(fake_smtp.sent) == 1
    msg = fake_smtp.sent[0]
    assert msg["To"] == KINDLE
    assert msg["Subject"] == "My Report"
    assert msg["From"] == "you@gmail.com"

    att = _only_attachment(msg)
    assert att.get_content_maintype() == "application"
    assert att.get_content_subtype() == "pdf"

    # SMTP host/creds decoded from the URL.
    assert fake_smtp.hosts == [("smtp.gmail.com", 587)]
    assert fake_smtp.logins == [("you@gmail.com", "app_pw")]


def test_send_epub_uses_epub_zip_subtype(fake_smtp, tmp_path):
    epub = tmp_path / "book.epub"
    epub.write_bytes(b"PK fake epub")
    send_file(epub, "A Book")

    att = _only_attachment(fake_smtp.sent[0])
    assert att.get_content_maintype() == "application"
    assert att.get_content_subtype() == "epub+zip"


def test_markdown_invokes_pandoc_mocked(fake_smtp, tmp_path, monkeypatch):
    md = tmp_path / "note.md"
    md.write_text("# Hello\n\nBody.")

    calls: list[list[str]] = []

    def fake_run(cmd, check, capture_output, text):
        calls.append(cmd)
        # Emulate pandoc: write the -o output target.
        out = cmd[cmd.index("-o") + 1]
        with open(out, "wb") as fh:
            fh.write(b"PK fake generated epub")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(core.subprocess, "run", fake_run)

    send_file(md, "My Note")

    assert len(calls) == 1
    assert calls[0][0] == "pandoc"
    assert "--metadata" in calls[0]
    assert "title=My Note" in calls[0]

    att = _only_attachment(fake_smtp.sent[0])
    assert att.get_content_subtype() == "epub+zip"


def test_send_markdown_content_path(fake_smtp, monkeypatch):
    def fake_run(cmd, check, capture_output, text):
        out = cmd[cmd.index("-o") + 1]
        with open(out, "wb") as fh:
            fh.write(b"PK fake epub")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(core.subprocess, "run", fake_run)

    result = send_markdown("# Title\n\nHi", "Inline Note")
    assert result.filename.endswith(".epub")
    att = _only_attachment(fake_smtp.sent[0])
    assert att.get_content_subtype() == "epub+zip"


def test_unsupported_file_type(fake_smtp, tmp_path):
    bad = tmp_path / "data.xyz"
    bad.write_text("nope")
    with pytest.raises(UnsupportedFileTypeError):
        send_file(bad, "Bad")


def test_missing_file_raises(fake_smtp, tmp_path):
    with pytest.raises(UnsupportedFileTypeError):
        send_file(tmp_path / "does_not_exist.pdf", "Ghost")


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_real_pandoc_conversion(fake_smtp, tmp_path):
    """Runs the real pandoc md->epub path (no email; SMTP is mocked)."""
    md = tmp_path / "real.md"
    md.write_text("# Real Heading\n\nSome paragraph text.")
    result = send_file(md, "Real Doc")

    assert result.filename.endswith(".epub")
    att = _only_attachment(fake_smtp.sent[0])
    assert att.get_content_subtype() == "epub+zip"
    # A real EPUB is a non-trivial zip.
    assert len(att.get_payload(decode=True)) > 100


def test_prepare_attachment_passthrough(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")
    path, subtype, name = prepare_attachment(pdf, "T")
    assert (path, subtype, name) == (pdf, "pdf", "x.pdf")


# --- MCP tool argument handling (no email; validation only) ---


def test_mcp_tool_requires_exactly_one_source():
    from kindlemcp.mcp_server import send_to_kindle

    fn = send_to_kindle.fn if hasattr(send_to_kindle, "fn") else send_to_kindle
    assert "exactly one" in fn(title="T").lower()
    assert "exactly one" in fn(title="T", content="a", file_path="b").lower()
    assert "title" in fn(title="").lower()


def test_mcp_tool_sends_file(fake_smtp, tmp_path):
    from kindlemcp.mcp_server import send_to_kindle

    fn = send_to_kindle.fn if hasattr(send_to_kindle, "fn") else send_to_kindle
    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"%PDF")
    out = fn(title="Rep", file_path=str(pdf))
    assert out == f"Sent 'Rep' (r.pdf) to {KINDLE}"
