#!/usr/bin/env python3
"""Backwards-compatible shim for the old ``kindle_send.py`` entry point.

The real logic now lives in the ``kindlemcp`` package. This shim keeps the
original command working:

    ./kindle_send.py --title "My Report" report.md

Prefer the installed console script ``kindlemcp-send`` (see the README). If the
package is not installed, this shim adds the local ``src/`` layout to the path
so it still runs from a checkout.
"""

import sys
from pathlib import Path

try:
    from kindlemcp.cli import main
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from kindlemcp.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
