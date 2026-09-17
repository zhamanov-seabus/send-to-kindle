"""MCP server for kindlemcp.

Exposes a single tool, ``send_to_kindle``, over stdio using the official
Model Context Protocol Python SDK (FastMCP).
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .core import KindleError, send_file, send_markdown

mcp = FastMCP("kindlemcp")


@mcp.tool()
def send_to_kindle(
    title: str,
    content: str | None = None,
    file_path: str | None = None,
) -> str:
    """Send a document to the configured Kindle via Amazon Send-to-Kindle email.

    Provide exactly one of ``content`` or ``file_path``:

    * ``file_path`` — path to an existing .md, .pdf, or .epub file to send.
    * ``content``   — Markdown text; it is written to a temp file, converted to
      EPUB with pandoc, and sent.

    ``title`` becomes the email subject, which Amazon uses as the document name
    on the Kindle. Returns a human-readable success or error message.
    """
    if not title or not title.strip():
        return "error: 'title' is required."

    has_content = content is not None and content.strip() != ""
    has_file = file_path is not None and file_path.strip() != ""

    if has_content and has_file:
        return "error: provide exactly one of 'content' or 'file_path', not both."
    if not has_content and not has_file:
        return "error: provide exactly one of 'content' or 'file_path'."

    try:
        if has_file:
            result = send_file(Path(file_path), title)  # type: ignore[arg-type]
        else:
            result = send_markdown(content, title)  # type: ignore[arg-type]
    except KindleError as exc:
        return f"error: {exc}"
    except Exception as exc:  # noqa: BLE001 - never crash the server on a tool call
        return f"error: unexpected failure: {exc}"

    return result.message()


def main() -> None:
    """Run the MCP server over stdio (default transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
