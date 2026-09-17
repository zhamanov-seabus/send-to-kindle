"""Command-line interface for kindlemcp.

Preserves the original ``kindle_send.py`` UX:

    kindlemcp-send --title "My Report" report.md
    kindlemcp-send --title "My Report" report.pdf
    echo "# Hi" | kindlemcp-send --title "Note"      # Markdown on stdin
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import KindleError, send_file, send_markdown


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="kindlemcp-send",
        description="Send a document (Markdown/EPUB/PDF) to your Kindle via email.",
    )
    ap.add_argument(
        "file",
        nargs="?",
        help="Markdown/EPUB/PDF file (or read Markdown from stdin)",
    )
    ap.add_argument(
        "--title",
        required=True,
        help="Document title (used as the name on the Kindle)",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    try:
        if args.file:
            result = send_file(Path(args.file), args.title)
        else:
            content = sys.stdin.read()
            if not content.strip():
                print("No input: pass a file or pipe Markdown on stdin.", file=sys.stderr)
                return 2
            result = send_markdown(content, args.title)
    except KindleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(result.message())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
