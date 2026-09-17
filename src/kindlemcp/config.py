"""Configuration resolution for kindlemcp.

Ports the search-path logic from the original ``kindle_send.py`` script.
No secrets live in code; ``SMTP_URL`` and ``KINDLE_ADDR`` are read from the
environment first, then from a small set of local config files.

Resolution order (first hit wins):
  * ``SMTP_URL``    — env var, else ``./.env``, else ``~/.kindle.env``,
                      else ``~/code/aicourse/.env`` (legacy location).
  * ``KINDLE_ADDR`` — env var, else ``./kindle.conf``, else ``~/.kindle.conf``.
"""

from __future__ import annotations

import os
from pathlib import Path


class ConfigError(RuntimeError):
    """Raised when a required configuration value cannot be resolved."""


def _smtp_sources() -> list[Path]:
    """SMTP_URL config file search path (evaluated lazily so cwd/home are live)."""
    return [
        Path.cwd() / ".env",
        Path.home() / ".kindle.env",
        Path.home() / "code" / "aicourse" / ".env",  # legacy location
    ]


def _kindle_sources() -> list[Path]:
    """KINDLE_ADDR config file search path."""
    return [
        Path.cwd() / "kindle.conf",
        Path.home() / ".kindle.conf",
    ]


def read_kv(path: Path, key: str) -> str | None:
    """Return the value for ``key`` in a ``KEY=value`` file, or None."""
    try:
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    except (FileNotFoundError, NotADirectoryError):
        return None
    return None


def resolve(key: str, sources: list[Path]) -> str | None:
    """Env var wins, then the first config file that defines ``key``."""
    val = os.environ.get(key)
    if val:
        return val
    for src in sources:
        val = read_kv(src, key)
        if val:
            return val
    return None


def resolve_smtp_url() -> str:
    """Resolve ``SMTP_URL`` or raise :class:`ConfigError`."""
    val = resolve("SMTP_URL", _smtp_sources())
    if not val:
        raise ConfigError(
            "SMTP_URL not set. Provide it via the SMTP_URL env var, ./.env, "
            "~/.kindle.env, or ~/code/aicourse/.env. See .env.example."
        )
    return val


def resolve_kindle_addr() -> str:
    """Resolve ``KINDLE_ADDR`` or raise :class:`ConfigError`."""
    val = resolve("KINDLE_ADDR", _kindle_sources())
    if not val:
        raise ConfigError(
            "KINDLE_ADDR not set. Provide it via the KINDLE_ADDR env var, "
            "./kindle.conf, or ~/.kindle.conf. See kindle.conf.example."
        )
    return val
